#!/usr/bin/env python3
"""Build a read-only, checksummed ZCC image-import plan; no remote or DB writes."""
from __future__ import annotations
import asyncio, hashlib, json
from pathlib import Path
from collections import Counter

async def local_products():
    from sqlalchemy import text
    from app.db.database import engine
    async with engine.connect() as conn:
        async with conn.begin():
            await conn.execute(text('SET TRANSACTION READ ONLY'))
            rows=(await conn.execute(text("""SELECT p.id,p.sku,p.specifications->>'source_url' source_url,count(i.id) image_count FROM products p LEFT JOIN product_images i ON i.product_id=p.id WHERE p.specifications ? 'source_url' GROUP BY p.id"""))).mappings().all()
    await engine.dispose(); return [dict(r) for r in rows]

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=Path('data/zcc_ir_20260917_sitemap'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=json.loads((a.input_dir/'zcc_ir_products.json').read_text())
    by_url={r['source_url']:r for r in source}; entries=[]
    for product in asyncio.run(local_products()):
        row=by_url.get(product['source_url'])
        if not row: continue
        images=[]
        for url in [row.get('main_image_url'),*(row.get('gallery_image_urls') or [])]:
            if url and url not in images: images.append(url)
        state='READY_DOWNLOAD' if images and product['image_count']==0 else ('EXISTING_IMAGES' if product['image_count'] else 'HOLD_NO_SOURCE_IMAGE')
        entries.append({'product_id':product['id'],'sku':product['sku'],'state':state,'source_url':product['source_url'],'image_urls':images[:10]})
    plan={'source_sha256':hashlib.sha256((a.input_dir/'zcc_ir_products.json').read_bytes()).hexdigest(),'entries':entries,'policy':'preserve manufacturer marks; review only independent ZCC store watermark'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    print(json.dumps({'counts':dict(Counter(x['state'] for x in entries)),'sha256':hashlib.sha256(json.dumps(plan,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}))
if __name__=='__main__':main()
