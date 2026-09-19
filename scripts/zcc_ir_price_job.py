#!/usr/bin/env python3
"""ZCC Category A price job: local, auditable, price-only updates in toman."""
from __future__ import annotations
import argparse, asyncio, hashlib, json, os
from decimal import Decimal
from pathlib import Path
from collections import Counter
from zcc_ir_import import API, check_environment, digest, http, write_json

async def census():
    from sqlalchemy import text
    from app.db.database import engine
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.execute(text('SET TRANSACTION READ ONLY'))
            rows=(await conn.execute(text("SELECT id,sku,base_price,specifications->>'source_url' source_url FROM products WHERE specifications ? 'source_url'"))).mappings().all()
    await engine.dispose()
    return [dict(x) for x in rows]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input-dir',type=Path,default=Path('data/zcc_ir_20260917_sitemap'))
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--confirm-plan-sha256')
    p.add_argument('--backup',type=Path)
    p.add_argument('--limit',type=int,default=0)
    a=p.parse_args()
    if a.apply and (not a.backup or not a.confirm_plan_sha256): p.error('apply requires backup and confirmed plan hash')
    check_environment()
    source_path=a.input_dir/'zcc_ir_products.json'
    source=json.loads(source_path.read_text())
    current=asyncio.run(census())
    by_url={r['source_url']:r for r in source}
    entries=[]
    for product in current:
        row=by_url.get(product['source_url'])
        if not row: continue
        price=row.get('price_normalized')
        if row.get('price_status')!='ok' or not price or int(price)<=0:
            entries.append({'id':product['id'],'sku':product['sku'],'state':'HOLD','reason':'SOURCE_PRICE_NOT_VALID','source_url':product['source_url']}); continue
        if product['base_price'] is not None and Decimal(str(product['base_price'])) == Decimal(str(price)):
            state='EXACT'
        else: state='UPDATE'
        entries.append({'id':product['id'],'sku':product['sku'],'state':state,'price_toman':str(price),'source_url':product['source_url']})
    plan={'destination':API,'currency':'toman','source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'entries':entries}
    a.output_dir.mkdir(parents=True,exist_ok=False); write_json(a.output_dir/'plan.json',plan)
    summary={'counts':dict(Counter(e['state'] for e in entries)),'plan_sha256':digest(plan),'applied':False,'scope':'base_price only; no availability or stock'}
    write_json(a.output_dir/'summary.json',summary); print(json.dumps(summary))
    if not a.apply:return
    if a.confirm_plan_sha256!=digest(plan):raise RuntimeError('Plan approval hash mismatch')
    if not a.backup.is_file() or not a.backup.stat().st_size:raise RuntimeError('Local backup required')
    from app.core.config import settings
    token=os.getenv('KARZAR_LOCAL_ADMIN_TOKEN') or http('POST','/auth/login',data={'username':settings.INITIAL_SUPER_ADMIN_PHONE,'password':settings.INITIAL_SUPER_ADMIN_PASSWORD},form=True)['access_token']
    work=[e for e in entries if e['state']=='UPDATE'][:a.limit or None]
    with (a.output_dir/'audit.jsonl').open('x') as f:
        def log(x): f.write(json.dumps(x)+'\n');f.flush();os.fsync(f.fileno())
        log({'event':'begin','plan_sha256':digest(plan),'backup':str(a.backup)})
        for e in work:
            log({'event':'price_intent','id':e['id'],'sku':e['sku'],'price_toman':e['price_toman']})
            http('PUT',f"/products/{e['id']}",token,{'base_price':e['price_toman']})
            log({'event':'price_updated','id':e['id']})
        log({'event':'complete','updated':len(work)})
    print('LOCAL_PRICE_APPLY_COMPLETE')
if __name__=='__main__': main()
