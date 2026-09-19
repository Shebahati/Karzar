#!/usr/bin/env python3
"""Local ZCC image downloader/uploader. Preserves manufacturer marks; no image editing."""
import argparse, asyncio, json, os, subprocess, tempfile
from urllib.parse import urlparse
from pathlib import Path
from zcc_ir_import import API, check_environment, http

async def rows():
 from sqlalchemy import text
 from app.db.database import engine
 async with engine.connect() as c:
  async with c.begin():
   await c.execute(text('SET TRANSACTION READ ONLY'))
   r=(await c.execute(text("SELECT p.id,p.sku,p.specifications->>'source_url' source_url,count(i.id) image_count FROM products p LEFT JOIN product_images i ON i.product_id=p.id WHERE p.specifications ? 'source_url' GROUP BY p.id HAVING count(i.id)=0"))).mappings().all()
 await engine.dispose();return [dict(x) for x in r]
def main():
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=Path('data/zcc_ir_20260917_sitemap'));p.add_argument('--audit',type=Path,required=True);p.add_argument('--limit',type=int,default=0);a=p.parse_args();check_environment()
 source={x['source_url']:x for x in json.loads((a.input_dir/'zcc_ir_products.json').read_text())}
 from app.core.config import settings
 token=os.getenv('KARZAR_LOCAL_ADMIN_TOKEN') or http('POST','/auth/login',data={'username':settings.INITIAL_SUPER_ADMIN_PHONE,'password':settings.INITIAL_SUPER_ADMIN_PASSWORD},form=True)['access_token']
 headers={'Authorization':'Bearer '+token,'Host':'api.karzartools.com','X-Forwarded-Proto':'https'}
 a.audit.mkdir(parents=True,exist_ok=False)
 with (a.audit/'audit.jsonl').open('x') as out:
  for product in asyncio.run(rows())[:a.limit or None]:
   row=source.get(product['source_url']);url=row and row.get('main_image_url')
   if not url: out.write(json.dumps({'state':'HOLD_NO_IMAGE','id':product['id']})+'\n');continue
   out.write(json.dumps({'state':'download_intent','id':product['id'],'url':url})+'\n');out.flush()
   suffix=Path(urlparse(url).path).suffix or '.jpg'
   with tempfile.NamedTemporaryFile(suffix=suffix) as image:
    subprocess.run(['curl','--fail','--location','--max-time','30','--output',image.name,url],check=True)
    subprocess.run(['curl','--fail','--max-time','30','-X','POST',API+f"/products/{product['id']}/images",'-H','Authorization: Bearer '+token,'-H','Host: api.karzartools.com','-H','X-Forwarded-Proto: https','-F','file=@'+image.name],check=True)
   out.write(json.dumps({'state':'uploaded','id':product['id'],'url':url})+'\n');out.flush()
if __name__=='__main__':main()
