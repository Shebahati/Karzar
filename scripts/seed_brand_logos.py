#!/usr/bin/env python3
"""Download high-quality brand logos and attach them to Brand.logo_url.

Priority (never attach unrelated Wikipedia page thumbnails):
  1. Local assets in scripts/brand_logo_assets/ (verified official SVGs/PNGs)
  2. Curated official / shopmill / Commons logo URLs
  3. Brandfetch / Clearbit / DDG icon for known tooling domains only
  4. Wikimedia Commons search only when the File: title contains brand + "logo"
     and the hit is an image (not PDF/photo dump)

Ambiguous short names (Acrobat≠Adobe, Jaguar≠car, Winstar≠LCD, …) never use
loose CDN/Commons matching — curated/local only, otherwise leave logo_url null.

Run on the API host / inside the API container (needs DB + writable uploads):

  python scripts/seed_brand_logos.py
  python scripts/seed_brand_logos.py --dry-run
  python scripts/seed_brand_logos.py --force
  python scripts/seed_brand_logos.py --ids 2,3,15 --force
  python scripts/seed_brand_logos.py --clear-ids 41,26,12
"""

from __future__ import annotations

import argparse
import asyncio
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import async_session_maker
from app.db.models.product import Brand
from app.utils.file_storage import save_brand_logo_bytes

USER_AGENT = (
    "Mozilla/5.0 (compatible; KarzarBrandLogoBot/1.0; +https://www.karzartools.com)"
)
MIN_BYTES = 800
MAX_BYTES = 5 * 1024 * 1024
ASSETS_DIR = Path(__file__).resolve().parent / "brand_logo_assets"

# Ambiguous short names: never auto-match Wikipedia / random CDNs.
# Only curated URLs / local assets (or explicit leave-null) are allowed.
AMBIGUOUS: frozenset[str] = frozenset(
    {
        "Acrobat",  # Turkish tap machine ≠ Adobe Acrobat
        "Jaguar",  # glass/ceramic drills ≠ Jaguar Cars
        "MAP",
        "Deniz",
        "Emkay",
        "CP-GRAT",
        "Chagan",
        "MPA",
        "Sahand",
        "Promax",
        "Viyer",
        "OMG",
        "Vertex",
        "UTEX",
        "Winstar",  # cutting tools ≠ Winstar Display (LCD)
        "LI-HSUN",
        "3Keego",
        "Chumpower",  # chucks ≠ PET blow-molding chumpower.com
        "TIGER TEC",  # Chinese HRC mills ≠ Walter Tiger·tec / tigertec.de
        "Groz",
        "ZPS",  # ZPS-FN tools ≠ TAJMAC-ZPS machines / zps.cz
        "Vogel",  # many unrelated Vogel entities on Commons/Wikipedia
        "SHAMS",
        "YOWAX",
        "Mighty Seven",
    }
)

# English key → filenames under scripts/brand_logo_assets/ (preferred first).
LOCAL_ASSETS: dict[str, list[str]] = {
    "3Keego": ["3keego.svg"],
    "Chumpower": ["chumpower.svg", "chumpower.png"],
    "Groz": ["groz.svg"],
    "Mighty Seven": [
        "mighty_seven.webp",
        "mighty_seven.png",
        "mighty_seven_text.svg",
    ],
    "MPA": ["mpa.gif"],
    "OMG": ["omg.jpg"],
    "Vertex": ["vertex.gif"],
    "Vogel": ["vogel.jpg"],
    "Winstar": ["winstar.png"],
    "ZPS": ["zps.svg"],
}

# English key → candidate direct URLs (prefer official SVG/PNG, then shopmill).
CURATED: dict[str, list[str]] = {
    "Mitutoyo": [
        "https://shopmilltools.com/wp-content/uploads/2025/11/mitutoyo.webp",
        "https://shopmilltools.com/wp-content/uploads/2025/09/mitutoyo.webp",
        "https://upload.wikimedia.org/wikipedia/commons/c/c2/Mitutoyo_company_logo.svg",
    ],
    "INSIZE": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/insize-1.webp",
    ],
    "ASIMETO": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/asimeto.webp",
    ],
    "Dasqua": [
        "https://shopmilltools.com/wp-content/uploads/2025/11/dasqua.webp",
        "https://shopmilltools.com/wp-content/uploads/2025/09/dasqua.webp",
    ],
    "KORLOY": [
        "https://shopmilltools.com/wp-content/uploads/2025/08/korloy.webp",
        "https://shopmilltools.com/wp-content/uploads/2025/09/korloy.webp",
    ],
    "ZCC.CT": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/zcc-ct.webp",
    ],
    "GUANGLU": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/guanglu.webp",
    ],
    "TERMA": [
        "https://shopmilltools.com/wp-content/uploads/2025/11/terma.webp",
        "https://shopmilltools.com/wp-content/uploads/2025/09/terma.webp",
    ],
    "DOHRE": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/dohre.webp",
    ],
    "MAP": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/map.webp",
        "https://shopmilltools.com/wp-content/uploads/2025/11/MAP.webp",
    ],
    "ASTPOWER": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/astpower.webp",
    ],
    "SAN OU": [
        "https://shopmilltools.com/wp-content/uploads/2025/09/san-ou.webp",
    ],
    "Narex": [
        "https://upload.wikimedia.org/wikipedia/commons/d/da/Narex-logo.png",
    ],
    "RÖHM": [
        "https://upload.wikimedia.org/wikipedia/commons/6/62/R%C3%B6hm_GmbH_logo.svg",
    ],
    # Newly curated official tooling logos (no Commons auto-guess).
    "Groz": [
        "https://groz-tools.com/static/frontend/Groz/Desktop/en_US/images/logo.svg",
        "https://groz-tools.com/media/logo/stores/1/logo.png",
    ],
    "Vogel": [
        "https://shop.vogel-germany.de/images/logos/logo-vogel-germany_pdf.jpg",
    ],
    "Winstar": [
        "https://www.winstarcutting.com/wp-content/uploads/Logo.png",
        "https://www.winstarcutting.com.tw/wp-content/uploads/Logo.png",
    ],
    "Mighty Seven": [
        "https://tools.mighty-seven.com/wp-content/uploads/2023/08/m7-logo.webp",
        "https://www.mighty-seven.com/images/header/logo.png",
        "https://www.mighty-seven.com/images/header/logo_text.svg",
    ],
    "Chumpower": [
        "https://www.chumpowerchuck.com/images/main_logo.png",
    ],
    "3Keego": [
        "https://asset-3keego.sharkcdn.io/build/3keego/images/3keego-logo.svg",
    ],
    "OMG": [
        "https://www.omgnet.it/upld/risorse/OMG-logo-def_350x3502.jpg",
    ],
    "MPA": [
        "https://www.m-p-a.it/images/logo.gif",
    ],
    "Vertex": [
        "https://www.vertex.co.com/admin/images/vertex-logo.gif",
    ],
    "ZPS": [
        "https://www.zps-fn.cz/public/images/img-sprite.svg",
    ],
}

# Domains for Brandfetch/Clearbit/DDG — only unambiguous tooling brands.
# Do NOT map short/ambiguous names to unrelated consumer domains.
DOMAINS: dict[str, str] = {
    "Mitutoyo": "mitutoyo.com",
    "INSIZE": "insize.com",
    "ASIMETO": "asimeto.com",
    "Dasqua": "dasqua.com",
    "KORLOY": "korloy.com",
    "ZCC.CT": "zccct.com",
    "Narex": "narex.cz",
    "RÖHM": "roehm.biz",
    "GUANGLU": "guanglumeasuring.com",
    "TERMA": "terma.com.pl",
    "DOHRE": "dohre.com",
    "SAN OU": "sanou.com.cn",
    "ASTPOWER": "astpower.com",
}

# Commons File: title must include one of these tokens (normalized) plus "logo".
COMMONS_ALLOWED: frozenset[str] = frozenset(CURATED) | frozenset(
    {
        "Mitutoyo",
        "Narex",
        "RÖHM",
        "Roehm",
        "Rohm",
    }
)

COMMONS_REJECT_TITLE = re.compile(
    r"(pdf|portrait|photo|building|headquarters|newspaper|journal|newsletter|"
    r"agreement|decision|horse|earth|astronaut|crater|mountain|ubuntu|"
    r"university|music|saarland|verlag|publisher|plexiglas|kochi|"
    r"adobe|acrobat|jaguar.?cars|land.?rover|groz.?beckert|winstar.?display)",
    re.I,
)


def english_name(full: str) -> str:
    left = full.split("|", 1)[0].strip()
    return left or full.strip()


def _norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _sniff_ext(content: bytes, url: str, content_type: str | None) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    head = content.lstrip()[:200].lower()
    if head.startswith(b"<svg") or b"<svg" in head[:50]:
        return ".svg"
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    if content_type:
        guess = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guess == ".jpe":
            return ".jpg"
        if guess in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
            return ".jpg" if guess == ".jpeg" else guess
    return None


def _load_local(name: str) -> tuple[bytes, str, str] | None:
    for filename in LOCAL_ASSETS.get(name, []):
        path = ASSETS_DIR / filename
        if not path.is_file():
            continue
        content = path.read_bytes()
        if len(content) < MIN_BYTES or len(content) > MAX_BYTES:
            continue
        ext = _sniff_ext(content, str(path), None) or path.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}:
            continue
        if ext == ".jpeg":
            ext = ".jpg"
        return content, ext, f"local:{filename}"
    return None


def _extract_zps_logo_from_sprite(content: bytes) -> tuple[bytes, str] | None:
    """ZPS-FN ships the mark inside an SVG sprite (#logo)."""
    text = content.decode("utf-8", "ignore")
    m = re.search(
        r'<symbol[^>]+id=["\']logo["\'][^>]*>(.*?)</symbol>',
        text,
        re.I | re.S,
    )
    if not m:
        return None
    vb = re.search(r'viewBox=["\']([^"\']+)["\']', m.group(0))
    view = vb.group(1) if vb else "0 0 137.6 29.4"
    inner = re.sub(r"^<symbol[^>]*>|</symbol>$", "", m.group(0), flags=re.I | re.S)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}">'
        f"{inner}</svg>"
    ).encode()
    if len(svg) < MIN_BYTES:
        return None
    return svg, ".svg"


async def _fetch(client: httpx.AsyncClient, url: str) -> tuple[bytes, str] | None:
    try:
        resp = await client.get(url, follow_redirects=True, timeout=25.0)
    except Exception:
        return None
    if resp.status_code != 200 or not resp.content:
        return None
    content = resp.content
    if len(content) < MIN_BYTES or len(content) > MAX_BYTES:
        return None
    ct = resp.headers.get("content-type", "")
    if "html" in ct.lower() and b"<svg" not in content[:500].lower():
        return None
    # ZPS-FN sprite: extract #logo symbol instead of storing the whole sprite.
    if "img-sprite.svg" in url and (
        b'id="logo"' in content or b"id='logo'" in content
    ):
        extracted = _extract_zps_logo_from_sprite(content)
        if extracted:
            return extracted
    ext = _sniff_ext(content, url, ct)
    if not ext:
        return None
    return content, ext


def _title_matches_brand(title: str, name: str) -> bool:
    """Require File: title to contain brand token AND logo."""
    t = title.lower()
    if "logo" not in t:
        return False
    if COMMONS_REJECT_TITLE.search(title):
        return False
    brand_norm = _norm_token(name)
    title_norm = _norm_token(title)
    if brand_norm and brand_norm in title_norm:
        return True
    # Allow diacritic-stripped Röhm / Roehm
    if name in {"RÖHM", "Roehm"} and ("rohm" in title_norm or "roehm" in title_norm):
        return True
    return False


async def commons_logo_search(
    client: httpx.AsyncClient,
    name: str,
) -> tuple[bytes, str] | None:
    """Commons File: search — only titles containing brand + logo."""
    if name not in COMMONS_ALLOWED and _norm_token(name) not in {
        _norm_token(x) for x in COMMONS_ALLOWED
    }:
        return None

    queries = [f"{name} logo", f'"{name}" logo']
    if name == "RÖHM":
        queries = ["Röhm GmbH logo", "Roehm GmbH logo", "Röhm logo chuck"]

    for q in queries:
        try:
            r = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": q,
                    "srnamespace": 6,
                    "srlimit": 8,
                    "format": "json",
                },
                timeout=20.0,
            )
        except Exception:
            continue
        if r.status_code != 200:
            continue
        for hit in r.json().get("query", {}).get("search", []):
            title = hit.get("title") or ""
            if not title.lower().startswith("file:"):
                continue
            if not _title_matches_brand(title, name):
                continue
            try:
                info = await client.get(
                    "https://commons.wikimedia.org/w/api.php",
                    params={
                        "action": "query",
                        "titles": title,
                        "prop": "imageinfo",
                        "iiprop": "url|mime|size",
                        "iiurlwidth": 800,
                        "format": "json",
                    },
                    timeout=20.0,
                )
            except Exception:
                continue
            if info.status_code != 200:
                continue
            pages = info.json().get("query", {}).get("pages", {})
            for page in pages.values():
                infos = page.get("imageinfo") or []
                if not infos:
                    continue
                mime = (infos[0].get("mime") or "").lower()
                if not mime.startswith("image/"):
                    continue
                if mime in {"application/pdf", "image/tiff"}:
                    continue
                url = infos[0].get("thumburl") or infos[0].get("url")
                if not url:
                    continue
                got = await _fetch(client, url)
                if got:
                    return got
                # SVG originals often work when thumb sizing fails
                raw = infos[0].get("url")
                if raw and raw != url:
                    got = await _fetch(client, raw)
                    if got:
                        return got
    return None


async def brandfetch_logo(client: httpx.AsyncClient, domain: str) -> tuple[bytes, str] | None:
    candidates = [
        f"https://cdn.brandfetch.io/{domain}/w/512/h/512/fallback/lettertype/theme/dark/icon.jpeg",
        f"https://cdn.brandfetch.io/{domain}/w/512/h/512",
        f"https://logo.clearbit.com/{domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
    ]
    for url in candidates:
        got = await _fetch(client, url)
        if got:
            return got
    return None


async def resolve_logo(
    client: httpx.AsyncClient,
    name: str,
) -> tuple[bytes, str, str] | None:
    local = _load_local(name)
    if local:
        return local

    for url in CURATED.get(name, []):
        got = await _fetch(client, url)
        if got:
            return got[0], got[1], f"curated:{url}"

    # Ambiguous brands: curated/local only — never Wikipedia pageimages / loose search.
    if name in AMBIGUOUS:
        return None

    domain = DOMAINS.get(name)
    if domain:
        bf = await brandfetch_logo(client, domain)
        if bf:
            return bf[0], bf[1], f"cdn:{domain}"

    # Strict Commons logo-file search (never enwiki pageimages).
    commons = await commons_logo_search(client, name)
    if commons:
        return commons[0], commons[1], "commons-logo"

    return None


def _parse_id_list(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return out


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace existing logos")
    parser.add_argument(
        "--ids",
        help="Comma-separated brand IDs to process (default: all)",
    )
    parser.add_argument(
        "--clear-ids",
        help="Comma-separated brand IDs whose logo_url should be cleared (null)",
    )
    parser.add_argument(
        "--clear-all-bad",
        action="store_true",
        help="Clear logo_url for every brand not in CURATED keep-set before fetch "
        "(use with care; prefer --clear-ids)",
    )
    args = parser.parse_args()

    only_ids = _parse_id_list(args.ids)
    clear_ids = _parse_id_list(args.clear_ids) or set()

    headers = {"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    async with httpx.AsyncClient(headers=headers) as client:
        async with async_session_maker() as db:
            brands = list((await db.execute(select(Brand).order_by(Brand.name))).scalars())
            ok = skip = fail = cleared = 0

            for brand in brands:
                name = english_name(brand.name)
                in_scope = only_ids is None or brand.id in only_ids

                should_clear = brand.id in clear_ids or (
                    args.clear_all_bad and name not in CURATED and bool(brand.logo_url)
                )
                if should_clear and (only_ids is None or brand.id in clear_ids or in_scope):
                    if args.dry_run:
                        print(f"CLEAR {brand.id} {name} (dry-run)")
                    else:
                        brand.logo_url = None
                        await db.flush()
                        print(f"CLEAR {brand.id} {name}")
                    cleared += 1

                if not in_scope:
                    continue

                if brand.logo_url and not args.force:
                    print(f"SKIP  {brand.id} {name} (has logo)")
                    skip += 1
                    continue

                print(f"FETCH {brand.id} {name} …", flush=True)
                resolved = await resolve_logo(client, name)
                if not resolved:
                    print(f"FAIL  {brand.id} {name} (no safe source)")
                    fail += 1
                    continue
                content, ext, source = resolved
                if args.dry_run:
                    print(
                        f"OK    {brand.id} {name} would save {len(content)}B {ext} from {source}"
                    )
                    ok += 1
                    continue
                path = save_brand_logo_bytes(brand.id, content, ext)
                brand.logo_url = path
                await db.flush()
                print(f"OK    {brand.id} {name} -> {path} ({len(content)}B, {source})")
                ok += 1

            if not args.dry_run:
                await db.commit()
            print(f"\nDone: ok={ok} skip={skip} fail={fail} cleared={cleared}")
            return 0 if fail == 0 or ok > 0 or cleared > 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
