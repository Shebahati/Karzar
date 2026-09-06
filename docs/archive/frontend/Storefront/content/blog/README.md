# Buyer-intent blog articles (SEO-003)

Persian mid-tail buyer-intent articles for the Karzar magazine (`/blog/[slug]`).

- **SoT file:** `articles.json`
- **Repo path:** also available as `content/blog/` (symlink → this directory)
- **Consumed by:** Storefront `src/lib/blog-articles.ts` (tests + mock) and `scripts/publish_seo003_articles.py` (CMS upsert)

## Rules

- 24 calendar articles (A01–D06) with unique title/intent
- Each article: ≥2 `related_product_ids`, ≥1 hub `/categories/…` link, FAQ when fit
- No price, stock, or availability claims
- No invented product specs — describe selection criteria only
- Publish to CMS after deploy so staging/live API serves them

## Regenerate

```bash
python3 scripts/generate_seo003_articles.py
```
