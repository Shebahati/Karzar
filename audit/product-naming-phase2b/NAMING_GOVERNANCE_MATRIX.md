# Naming governance matrix (Phase 2B)

| Input | Exists ≠ governed | HIGH requires |
|-------|-------------------|---------------|
| Product Type | FK may be null | `product_type_governed` |
| manufacturer_code | column may be null | non-null + governed flag |
| Brand display | raw bilingual name | registry status GOVERNED/APPROVED/CANONICAL |
| Naming profile | generic.v1 fallback | mapped PT profile (`PROFILE_GOVERNED`) |
| Variant facts | title heuristics | published KB Facts when used in title |
| Identity qualifiers | free strings | `identity_qualifiers_governed` when used |

`generic.v1` ⇒ `naming_profile_not_governed` ⇒ HIGH forbidden.
