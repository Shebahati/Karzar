#!/usr/bin/env python3
"""Download high-quality brand logos and attach them to Brand.logo_url.

Run on the API host / inside the API container (needs DB + writable uploads):

  python scripts/seed_brand_logos.py
  python scripts/seed_brand_logos.py --dry-run
  python scripts/seed_brand_logos.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

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

# English key → candidate direct URLs (prefer PNG/SVG from Wikimedia / official CDNs).
CURATED: dict[str, list[str]] = {
    "Mitutoyo": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Mitutoyo_logo.svg/512px-Mitutoyo_logo.svg.png",
        "https://upload.wikimedia.org/wikipedia/commons/8/8a/Mitutoyo_logo.svg",
    ],
    "INSIZE": [
        "https://www.insize.com/upload/image/20201210/insize-logo.png",
    ],
    "ASIMETO": [
        "https://www.asimeto.com/wp-content/uploads/2019/05/asimeto-logo.png",
    ],
    "Dasqua": [
        "https://www.dasqua.com/wp-content/uploads/2020/06/dasqua-logo.png",
    ],
    "KORLOY": [
        "https://www.korloy.com/eng/images/common/logo.png",
    ],
    "ZCC.CT": [
        "https://www.zccct.com/static/images/logo.png",
    ],
    "Vogel": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Vogel_Germany_logo.svg/512px-Vogel_Germany_logo.svg.png",
    ],
    "Narex": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Narex_logo.svg/512px-Narex_logo.svg.png",
    ],
    "RÖHM": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/R%C3%B6hm_GmbH_logo.svg/512px-R%C3%B6hm_GmbH_logo.svg.png",
        "https://www.roehm.biz/fileadmin/user_upload/roehm-logo.svg",
    ],
    "Groz": [
        "https://www.groz-tools.com/images/logo.png",
    ],
    "Vertex": [
        "https://www.vertex-tools.com/images/logo.png",
    ],
    "GUANGLU": [
        "https://www.guanglumeasuring.com/static/images/logo.png",
    ],
    "Winstar": [
        "https://www.winstar.com.tw/images/logo.png",
    ],
    "ZPS": [
        "https://www.zps.cz/files/logo.png",
    ],
}

DOMAINS: dict[str, str] = {
    "Mitutoyo": "mitutoyo.com",
    "INSIZE": "insize.com",
    "ASIMETO": "asimeto.com",
    "Dasqua": "dasqua.com",
    "KORLOY": "korloy.com",
    "ZCC.CT": "zccct.com",
    "Vogel": "vogel-germany.de",
    "Narex": "narex.cz",
    "RÖHM": "roehm.biz",
    "Groz": "groz-tools.com",
    "Vertex": "vertex-tools.com",
    "GUANGLU": "guanglumeasuring.com",
    "Winstar": "winstar.com.tw",
    "Chumpower": "chumpower.com",
    "TERMA": "terma.com.pl",
    "DOHRE": "dohre.com",
    "MAP": "mapal.com",
    "SAN OU": "sanou.com.cn",
    "TIGER TEC": "tigertec.de",
    "Emkay": "emkay.com",
    "Jaguar": "jaguar.com",
    "UTEX": "utex.com",
    "LI-HSUN": "lihsun.com.tw",
    "Viyer": "viyer.com",
    "Transmex": "transmex.com",
    "Deniz": "deniz.com",
    "3Keego": "3keego.com",
    "Chagan": "chagan.com",
    "MPA": "mpa.com",
    "Sahand": "sahand.com",
    "Promax": "promax.com",
    "CP-GRAT": "cpgrat.com",
    "Acrobat": "acrobat.com",
    "OMG": "omg.it",
    "ZPS": "zps.cz",
    "ASTPOWER": "astpower.com",
}


def english_name(full: str) -> str:
    left = full.split("|", 1)[0].strip()
    return left or full.strip()


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
    ext = _sniff_ext(content, url, ct)
    if not ext:
        return None
    return content, ext


async def wikimedia_logo(client: httpx.AsyncClient, name: str) -> tuple[bytes, str] | None:
    api = "https://en.wikipedia.org/w/api.php"
    try:
        r = await client.get(
            api,
            params={
                "action": "query",
                "titles": name,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 800,
                "redirects": 1,
            },
            timeout=20.0,
        )
        if r.status_code == 200:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = (page.get("thumbnail") or {}).get("source")
                if thumb:
                    got = await _fetch(client, thumb)
                    if got:
                        return got
    except Exception:
        pass

    try:
        r = await client.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": f"{name} logo",
                "srnamespace": 6,
                "srlimit": 5,
                "format": "json",
            },
            timeout=20.0,
        )
        if r.status_code != 200:
            return None
        for hit in r.json().get("query", {}).get("search", []):
            title = hit.get("title") or ""
            if not title.lower().startswith("file:"):
                continue
            info = await client.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "iiurlwidth": 800,
                    "format": "json",
                },
                timeout=20.0,
            )
            if info.status_code != 200:
                continue
            pages = info.json().get("query", {}).get("pages", {})
            for page in pages.values():
                infos = page.get("imageinfo") or []
                if not infos:
                    continue
                url = infos[0].get("thumburl") or infos[0].get("url")
                if url:
                    got = await _fetch(client, url)
                    if got:
                        return got
    except Exception:
        return None
    return None


async def brandfetch_logo(client: httpx.AsyncClient, domain: str) -> tuple[bytes, str] | None:
    candidates = [
        f"https://cdn.brandfetch.io/{domain}/w/512/h/512/fallback/lettertype/theme/dark/icon.jpeg",
        f"https://cdn.brandfetch.io/{domain}/w/512/h/512",
        f"https://logo.clearbit.com/{domain}",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
        f"https://www.google.com/s2/favicons?domain={quote(domain)}&sz=128",
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
    for url in CURATED.get(name, []):
        got = await _fetch(client, url)
        if got:
            return got[0], got[1], f"curated:{url}"

    wiki = await wikimedia_logo(client, name)
    if wiki:
        return wiki[0], wiki[1], "wikimedia"

    domain = DOMAINS.get(name)
    if domain:
        bf = await brandfetch_logo(client, domain)
        if bf:
            return bf[0], bf[1], f"cdn:{domain}"

    alt = re.sub(r"[^A-Za-z0-9 .+-]", "", name).strip()
    if alt and alt != name:
        wiki2 = await wikimedia_logo(client, alt)
        if wiki2:
            return wiki2[0], wiki2[1], "wikimedia-alt"
    return None


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Replace existing logos")
    args = parser.parse_args()

    headers = {"User-Agent": USER_AGENT, "Accept": "image/*,*/*"}
    async with httpx.AsyncClient(headers=headers) as client:
        async with async_session_maker() as db:
            brands = list((await db.execute(select(Brand).order_by(Brand.name))).scalars())
            ok = skip = fail = 0
            for brand in brands:
                name = english_name(brand.name)
                if brand.logo_url and not args.force:
                    print(f"SKIP  {brand.id} {name} (has logo)")
                    skip += 1
                    continue
                print(f"FETCH {brand.id} {name} …", flush=True)
                resolved = await resolve_logo(client, name)
                if not resolved:
                    print(f"FAIL  {brand.id} {name} (no source)")
                    fail += 1
                    continue
                content, ext, source = resolved
                if args.dry_run:
                    print(f"OK    {brand.id} {name} would save {len(content)}B {ext} from {source}")
                    ok += 1
                    continue
                path = save_brand_logo_bytes(brand.id, content, ext)
                brand.logo_url = path
                await db.flush()
                print(f"OK    {brand.id} {name} -> {path} ({len(content)}B, {source})")
                ok += 1
            if not args.dry_run:
                await db.commit()
            print(f"\nDone: ok={ok} skip={skip} fail={fail}")
            return 0 if fail == 0 or ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
