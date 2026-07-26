# PMO / Product Changelog (living)

## 2026-07-26
- [ ] **FE-001** (partial) Floating transparent home header over full-bleed hero — white logo + subtle top shade until first scroll, then glass; capsule nav bg kept
- [x] **SEO-002** Category hub intros + internal links (15 metrology/cutting hubs) — #91 → `main` @d92722a; Deploy Staging green; verified `/categories/انواع-کولیس`
- [x] **SEO-001** Storefront JSON-LD: Product + gated Offer + Breadcrumb (PDP); CollectionPage/ItemList (category hubs); Organization + WebSite + SearchAction (layout) — #88 → `main` @89a4cf5; Deploy Staging green; verified `/product/7115`
- [ ] Taxonomy: remove padding «عمومی» L3 leaves → products to L2 parent — #87 (`scripts/remove_omumi_padding_leaves.py` + sole-parent DELETE; dry-run 23/1954; staging apply pending workflow)
- [x] Merged to `main`: Measurement promote CI (#81); SAN OU (#73), Mitutoyo leaflets (#72), Dasqua 2025 (#71), Chumpower (#70) enrichment; Hesabfa stock clear asyncpg (#56); CI lint/test unlock for frontend-only PRs (#26); Living PMO (#86)
- [x] Staging deployed for the enrichment PRs above (#70–#73)
- [x] Skipped (not merged): phase-A images continue (#67, open), Dohre enrichment (#69, open), Insize 108A (#74, closed)
- [x] Created living PMO under `project-management/`
- [x] Seeded tasks.json + import CSVs
- [x] Documented 31 Shahrivar realism assessment

## Prior (repo history — selected)
- [x] Homepage megamenu hero / categories / why-karzar waves
- [x] Metrology taxonomy promote + admin megamenu display flags
- [x] SEO short_description plumbing (#66/#68)
