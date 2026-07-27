#!/usr/bin/env python3
"""Publish / update SEO-003 buyer-intent articles via CMS API.

Source of truth:
  frontend/Storefront/content/blog/articles.json
  (on VPS after deploy: $FRONTEND_ROOT/Storefront/content/blog/articles.json)

Examples:
  python scripts/publish_seo003_articles.py --dry-run
  KARZAR_API_BASE=https://api.karzartools.com/api/v1 \\
    python scripts/publish_seo003_articles.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
ROOT = Path(__file__).resolve().parents[1]


def articles_path() -> Path:
    env = os.getenv("SEO003_ARTICLES_PATH")
    if env:
        return Path(env)
    frontend_root = os.getenv("FRONTEND_ROOT")
    if frontend_root:
        candidate = Path(frontend_root) / "Storefront" / "content" / "blog" / "articles.json"
        if candidate.exists():
            return candidate
    return ROOT / "frontend" / "Storefront" / "content" / "blog" / "articles.json"


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip().strip("'").strip('"')
    return out


def _load_admin_creds() -> tuple[str, str]:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    for secrets in (
        Path("/opt/karzar/.deploy-secrets"),
        Path("/opt/karzar/Karzar/.deploy-secrets"),
        Path("/opt/karzar/Karzar/.env"),
        ROOT / ".deploy-secrets",
        ROOT / ".env",
    ):
        parsed = _parse_env_file(secrets)
        phone = phone or parsed.get("INITIAL_SUPER_ADMIN_PHONE")
        password = password or parsed.get("INITIAL_SUPER_ADMIN_PASSWORD")
    if not phone or not password:
        raise RuntimeError(
            "missing admin creds (INITIAL_SUPER_ADMIN_PHONE/PASSWORD in env, "
            ".deploy-secrets, or .env)"
        )
    return phone, password


def http_json(method: str, url: str, *, data=None, headers=None, timeout=120):
    body = None
    hdrs = {"Accept": "application/json", "User-Agent": "KarzarSeo003Publish/1.0"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode()) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:800]}
        return e.code, payload


def login() -> str:
    phone, password = _load_admin_creds()
    body = urllib.parse.urlencode({"username": phone, "password": password}).encode()
    req = urllib.request.Request(
        f"{API}/auth/login",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["access_token"]


def find_related_ids(auth: dict, queries: list[str], limit: int = 4) -> list[int]:
    ids: list[int] = []
    seen: set[int] = set()
    for q in queries:
        if not q or len(ids) >= limit:
            break
        st, resp = http_json(
            "GET",
            f"{API}/products/?limit=20&search={urllib.parse.quote(q)}",
            headers=auth,
        )
        if st != 200:
            continue
        for p in resp.get("data") or []:
            pid = p.get("id")
            if isinstance(pid, int) and pid not in seen:
                seen.add(pid)
                ids.append(pid)
                if len(ids) >= limit:
                    break
    return ids


def cms_payload(article: dict, related: list[int]) -> dict:
    return {
        "slug": article["slug"],
        "title": article["title"],
        "excerpt": article["excerpt"],
        "cover_image": article.get("cover_image"),
        "published_at": article["published_at"],
        "reading_minutes": article.get("reading_minutes", 8),
        "author": article.get("author") or "تیم فنی کارزار",
        "tags": article.get("tags") or [],
        "related_product_ids": related,
        "blocks": article.get("blocks") or [],
        "is_published": bool(article.get("is_published", True)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Publish only first N articles (0=all)")
    args = ap.parse_args()

    path = articles_path()
    if not path.exists():
        print(f"[seo003] missing articles file: {path}", file=sys.stderr)
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    articles = data.get("articles") or []
    if args.limit > 0:
        articles = articles[: args.limit]
    if len(articles) != 24 and args.limit == 0:
        print(f"[seo003] expected 24 articles, got {len(articles)}", file=sys.stderr)
        return 1

    token = login()
    auth = {"Authorization": f"Bearer {token}"}

    by_slug: dict = {}
    skip = 0
    page_size = 200
    while True:
        st, listing = http_json(
            "GET",
            f"{API}/cms/articles?limit={page_size}&skip={skip}",
            headers=auth,
        )
        if st != 200:
            print(f"[seo003] list fail {st} {listing}", file=sys.stderr)
            return 1
        batch = listing.get("data") or []
        for a in batch:
            if a.get("slug"):
                by_slug[a["slug"]] = a
        if len(batch) < page_size:
            break
        skip += len(batch)
        if skip > 5000:
            break

    ok = 0
    fail = 0
    for article in articles:
        related = list(article.get("related_product_ids") or [])
        queries = article.get("related_product_queries") or []
        if len(related) < 2 and queries:
            related = find_related_ids(auth, queries, limit=4)
        if len(related) < 2:
            print(f"[seo003] WARN {article['slug']}: fewer than 2 related products ({related})")

        payload = cms_payload(article, related)
        existing = by_slug.get(article["slug"])

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "action": "update" if existing else "create",
                        "calendar_id": article.get("calendar_id"),
                        "slug": article["slug"],
                        "blocks": len(payload["blocks"]),
                        "related": related,
                    },
                    ensure_ascii=False,
                )
            )
            ok += 1
            continue

        if existing:
            st, resp = http_json(
                "PUT",
                f"{API}/cms/articles/{existing['id']}",
                data=payload,
                headers=auth,
            )
            action = "updated"
        else:
            st, resp = http_json("POST", f"{API}/cms/articles", data=payload, headers=auth)
            action = "created"

        if st not in (200, 201):
            print(f"[seo003] FAIL {action} {article['slug']} {st} {resp}", file=sys.stderr)
            fail += 1
            continue

        st2, _pub = http_json("GET", f"{API}/blog/{article['slug']}")
        if st2 != 200:
            print(f"[seo003] FAIL public GET {article['slug']} → {st2}", file=sys.stderr)
            fail += 1
            continue

        print(f"[seo003] {action} {article.get('calendar_id')} {article['slug']} id={resp.get('id')}")
        ok += 1

    print(f"[seo003] done ok={ok} fail={fail} dry_run={args.dry_run}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
