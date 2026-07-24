#!/usr/bin/env python3
"""Publish / update the vernier caliper SEO article via CMS API.

  python scripts/publish_vernier_article.py
  python scripts/publish_vernier_article.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
ARTICLE_PATH = Path(__file__).resolve().parents[1] / "data" / "article_how_to_read_vernier_caliper.json"


def _load_admin_creds() -> tuple[str, str]:
    phone = os.getenv("INITIAL_SUPER_ADMIN_PHONE")
    password = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD")
    secrets = Path(__file__).resolve().parents[1] / ".deploy-secrets"
    if secrets.exists():
        for line in secrets.read_text(encoding="utf-8").splitlines():
            if line.startswith("INITIAL_SUPER_ADMIN_PHONE=") and not phone:
                phone = line.split("=", 1)[1].strip()
            if line.startswith("INITIAL_SUPER_ADMIN_PASSWORD=") and not password:
                password = line.split("=", 1)[1].strip()
    if not phone or not password:
        raise RuntimeError("missing admin creds")
    return phone, password


def http_json(method: str, url: str, *, data=None, headers=None, timeout=120):
    body = None
    hdrs = {"Accept": "application/json", "User-Agent": "KarzarArticlePublish/1.0"}
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
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())["access_token"]


def find_related_caliper_ids(auth: dict, limit: int = 6) -> list[int]:
    """Best-effort: products whose name contains کولیس."""
    ids: list[int] = []
    skip = 0
    while len(ids) < limit and skip < 500:
        st, resp = http_json(
            "GET",
            f"{API}/products/?limit=100&skip={skip}&search={urllib.parse.quote('کولیس')}",
            headers=auth,
        )
        if st != 200:
            break
        batch = resp.get("data") or []
        if not batch:
            break
        for p in batch:
            name = (p.get("name") or "").lower()
            if "کولیس" in (p.get("name") or "") or "caliper" in name:
                ids.append(p["id"])
                if len(ids) >= limit:
                    break
        skip += len(batch)
        if len(batch) < 100:
            break
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = json.loads(ARTICLE_PATH.read_text(encoding="utf-8"))
    token = login()
    auth = {"Authorization": f"Bearer {token}"}

    related = find_related_caliper_ids(auth)
    if related:
        payload["related_product_ids"] = related
        print(f"[article] related products={related}")

    # find existing by slug in admin list
    st, listing = http_json("GET", f"{API}/cms/articles?limit=200", headers=auth)
    if st != 200:
        print(f"[article] list fail {st} {listing}")
        return 1
    existing = next((a for a in (listing.get("data") or []) if a.get("slug") == payload["slug"]), None)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "action": "update" if existing else "create",
                    "id": existing.get("id") if existing else None,
                    "slug": payload["slug"],
                    "blocks": len(payload["blocks"]),
                    "related": payload.get("related_product_ids"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

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
        print(f"[article] FAIL {action} {st} {resp}")
        return 1

    print(f"[article] {action} id={resp.get('id')} slug={resp.get('slug')}")

    # public verify
    st2, pub = http_json("GET", f"{API}/blog/{payload['slug']}")
    print(f"[article] public GET /blog/{payload['slug']} → {st2} title={pub.get('title','')[:60]}")
    return 0 if st2 == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
