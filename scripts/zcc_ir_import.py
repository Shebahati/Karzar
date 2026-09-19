#!/usr/bin/env python3
"""ZCC Category A: reconcile every source row; create local inactive drafts only.

Source: checksummed crawl + category mapping. Owner: Mohammad Shebahati.
Destination: development container's loopback API; production unsupported.
Validation: source collisions, full local DB census, live taxonomy, ProductCreate.
Audit: exclusive run directory, frozen plan, fsynced intent/result journal.
Recovery: before-run local DB backup plus created IDs; no automatic deletion.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib import request, parse, error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zcc_ir_catalog.normalize import canonicalize_brand, manufacturer_identity_key, extract_model_from_name, fold_text

API = 'http://127.0.0.1:8000/api/v1'
PREFIX = {'ZCC.CT': 'ZCC', 'SAN OU': 'SANOU', 'STC': 'STC'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def proposed_sku(row):
    brand = row.get('brand_normalized')
    code = row.get('part_number') or row.get('manufacturer_code')
    if brand not in PREFIX or not code:
        return None
    # Never truncate, invent suffixes, or use a source page ID as manufacturer code.
    sku = PREFIX[brand] + '-' + re.sub(r'\s+', '-', str(code).strip().upper())
    return sku if len(sku) <= 50 and re.fullmatch(r'[A-Z0-9./+_-]+', sku) else None


def build_plan(rows, mappings, categories, brands, current):
    cats = {str(c['id']): c for c in categories}
    brand_ids = {}
    for b in brands:
        brand_ids.setdefault(canonicalize_brand(b['name']), []).append(b['id'])
    counts = Counter(proposed_sku(r) for r in rows)
    identities = Counter((r.get('brand_normalized'), manufacturer_identity_key(r.get('part_number') or r.get('manufacturer_code'))) for r in rows)
    urls = Counter(r.get('source_url') for r in rows)
    existing_index = []
    for p in current:
        pb = canonicalize_brand(p.get('brand') or '')
        ps = p.get('sku') or ''
        prefix = PREFIX.get(pb, '') + '-'
        existing_index.append((p['id'], pb, ps,
            manufacturer_identity_key(extract_model_from_name(p.get('name'))),
            manufacturer_identity_key(ps[len(prefix):] if ps.startswith(prefix) else ps)))
    entries = []
    for r in rows:
        sku = proposed_sku(r)
        brand = r.get('brand_normalized')
        identity = manufacturer_identity_key(r.get('part_number') or r.get('manufacturer_code'))
        m = mappings.get(' > '.join(r.get('category_path') or []), {})
        target_path = [fold_text(s).strip() for s in (m.get('karzar_category_path') or '').split('›')]
        matching_cats = [c for c in categories if [fold_text(s).strip() for s in c.get('breadcrumb', [])] == target_path and c.get('is_selectable')]
        cat = matching_cats[0] if len(matching_cats) == 1 else None
        flags = []
        if m.get('mapping_status') != 'SAFE_RULE': flags.append('OUTSIDE_SAFE_CATEGORY_SCOPE')
        if not cat or not cat.get('is_selectable'): flags.append('CATEGORY_NOT_SELECTABLE')
        if brand not in PREFIX: flags.append('BRAND_CONFLICT')
        if len(brand_ids.get(brand, [])) > 1: flags.append('AMBIGUOUS_TARGET_BRAND')
        if not brand_ids.get(brand) and brand != 'STC': flags.append('MISSING_TARGET_BRAND')
        if not sku: flags.append('INVALID_MANUFACTURER_SKU')
        if sku and (counts[sku] > 1 or identities[(brand, identity)] > 1): flags.append('SOURCE_IDENTITY_COLLISION')
        if urls[r.get('source_url')] > 1: flags.append('SOURCE_URL_COLLISION')
        if not str(r.get('source_url') or '').startswith('https://zcc.ir/product/'): flags.append('INVALID_SOURCE_URL')
        matched = []
        for pid, pb, psku, model, pmodel in existing_index:
            same_brand = pb == brand
            alias = brand == 'SAN OU' and r.get('source_internal_sku') and psku == 'SO-' + str(r['source_internal_sku'])
            if psku == sku or (same_brand and (alias or (identity and identity in {model, pmodel}))):
                matched.append(pid)
        if len(matched) > 1: flags.append('AMBIGUOUS_EXISTING_MATCH')
        state = 'HOLD' if flags else ('EXISTING' if matched else 'CREATE')
        payload = None
        if state == 'CREATE':
            payload = {'sku': sku, 'name': r.get('name_fa'), 'category_id': cat['id'],
                       'brand_id': (brand_ids.get(brand) or [None])[0],
                       'is_active': False, 'is_available': False, 'base_price': None,
                       'specifications': {'source_attributes': r.get('attributes') or {},
                                          'source_url': r['source_url'],
                                          'source_timestamp': r.get('crawl_timestamp')}}
        entries.append({'source_url': r.get('source_url'), 'sku': sku, 'brand': brand,
                        'state': state, 'reasons': flags, 'existing_ids': matched,
                        'payload': payload, 'image_source_urls': r.get('gallery_image_urls') or []})
    return entries


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('Redirect refused; local destination must remain fixed')


def http(method, path, token=None, data=None, form=False):
    headers = {'Host': 'api.karzartools.com', 'X-Forwarded-Proto': 'https'}
    if token: headers['Authorization'] = 'Bearer ' + token
    body = None
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
        body = (parse.urlencode(data) if form else json.dumps(data)).encode()
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request.Request(API + path, data=body, headers=headers, method=method), timeout=30) as response:
            return json.load(response)
    except error.HTTPError as exc:
        raise RuntimeError(f'Local API {method} {path}: HTTP {exc.code}; stop and reconcile before retry') from None


def check_environment():
    from app.core.config import settings
    from sqlalchemy.engine import make_url
    if settings.APP_ENV != 'development' or settings.HESABFA_ENABLED:
        raise RuntimeError('Requires development environment with Hesabfa disabled')
    if make_url(str(settings.ASYNC_DATABASE_URI)).host not in {'db', 'localhost', '127.0.0.1'}:
        raise RuntimeError('Non-local database refused')
    if os.getenv('KARZAR_API_BASE', API).rstrip('/') != API:
        raise RuntimeError('Only the fixed Category A loopback API is supported')
    return settings


async def census():
    from sqlalchemy import text
    from app.db.database import engine
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.execute(text('SET TRANSACTION READ ONLY'))
            rows = (await conn.execute(text('SELECT p.id, p.sku, p.name, p.brand_id, p.category_id, p.is_active, p.is_available, p.deleted_at, b.name AS brand FROM products p LEFT JOIN brands b ON b.id=p.brand_id ORDER BY p.id'))).mappings().all()
    await engine.dispose()
    return [dict(r) for r in rows]


def write_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)


def apply_plan(plan, settings, audit_path, backup, expected_hash, limit):
    if expected_hash != digest(plan): raise RuntimeError('Plan approval hash mismatch')
    if not backup.is_file() or backup.stat().st_size == 0: raise RuntimeError('Local backup required')
    token = os.getenv('KARZAR_LOCAL_ADMIN_TOKEN')
    if not token:
        if not settings.INITIAL_SUPER_ADMIN_PHONE or not settings.INITIAL_SUPER_ADMIN_PASSWORD:
            raise RuntimeError('Local admin authentication unavailable')
        token = http('POST', '/auth/login', data={'username': settings.INITIAL_SUPER_ADMIN_PHONE, 'password': settings.INITIAL_SUPER_ADMIN_PASSWORD}, form=True)['access_token']
    candidates = [e for e in plan['entries'] if e['state'] == 'CREATE']
    if limit: candidates = candidates[:limit]
    brand_id = None
    with audit_path.open('x', encoding='utf-8') as audit:
        def record(event):
            audit.write(json.dumps(event, ensure_ascii=False) + '\n'); audit.flush(); os.fsync(audit.fileno())
        record({'event': 'begin', 'plan_sha256': expected_hash, 'backup': str(backup), 'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest()})
        for entry in candidates:
            payload = dict(entry['payload'])
            if payload['brand_id'] is None:
                if entry['brand'] != 'STC': raise RuntimeError('Unapproved brand creation')
                if brand_id is None:
                    record({'event': 'brand_intent', 'name': 'STC'})
                    brand_id = http('POST', '/brands/', token, {'name': 'STC'})['id']
                    record({'event': 'brand_created', 'id': brand_id})
                payload['brand_id'] = brand_id
            record({'event': 'create_intent', 'source_url': entry['source_url'], 'payload': payload})
            result = http('POST', '/products/', token, payload)
            record({'event': 'created', 'id': result['id'], 'sku': payload['sku'], 'source_url': entry['source_url']})
        record({'event': 'complete', 'created': len(candidates)})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', type=Path, default=Path('data/zcc_ir_20260917_sitemap'))
    p.add_argument('--category-overrides', type=Path, default=Path('scripts/zcc_ir_category_overrides.json'))
    p.add_argument('--output-dir', type=Path, required=True, help='New exclusive run directory')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--confirm-plan-sha256')
    p.add_argument('--backup', type=Path)
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()
    if args.limit < 0: p.error('limit must be non-negative')
    if args.apply and (not args.backup or not args.confirm_plan_sha256): p.error('apply requires backup and confirmed plan hash')
    settings = check_environment()
    source = args.input_dir / 'zcc_ir_products.json'
    map_path = args.input_dir / 'zcc_ir_category_mapping.csv'
    rows = json.loads(source.read_text())
    with map_path.open(encoding='utf-8') as f: mappings = {r['source_category_path']: r for r in csv.DictReader(f)}
    overrides = json.loads(args.category_overrides.read_text(encoding='utf-8'))
    for source_path, mapping in mappings.items():
        if mapping['mapping_status'] == 'SAFE_RULE':
            continue
        matched = [rule for rule in overrides['rules'] if rule['contains'] in source_path]
        if len(matched) > 1:
            raise RuntimeError(f'Ambiguous category override for {source_path!r}')
        if matched:
            mapping['mapping_status'] = 'SAFE_RULE'
            mapping['karzar_category_path'] = matched[0]['target']
    categories = http('GET', '/categories/')['data']
    brands = http('GET', '/brands/')['data']
    current = asyncio.run(census())
    entries = build_plan(rows, mappings, categories, brands, current)
    from app.schemas.product import ProductCreate
    for e in entries:
        if e['payload']:
            try: ProductCreate.model_validate(e['payload'])
            except ValueError:
                e.update(state='HOLD', reasons=e['reasons'] + ['API_SCHEMA_INVALID'], payload=None)
    plan = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'mapping_sha256': hashlib.sha256(map_path.read_bytes()).hexdigest(),
            'entries': entries, 'scope': 'SAFE_RULE_ONLY', 'destination': API}
    args.output_dir.mkdir(parents=True, exist_ok=False)
    write_json(args.output_dir / 'plan.json', plan)
    write_json(args.output_dir / 'before.json', {'products': current, 'brands': brands, 'categories': categories})
    summary = {'source_rows': len(rows), 'safe_scope_rows': sum('OUTSIDE_SAFE_CATEGORY_SCOPE' not in e['reasons'] for e in entries),
               'counts': dict(Counter(e['state'] for e in entries)), 'plan_sha256': digest(plan),
               'applied': False, 'images': 'source references only; image upload deferred'}
    write_json(args.output_dir / 'summary.json', summary)
    print(json.dumps(summary))
    if args.apply:
        apply_plan(plan, settings, args.output_dir / 'audit.jsonl', args.backup, args.confirm_plan_sha256, args.limit)
        print('LOCAL_APPLY_COMPLETE')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
