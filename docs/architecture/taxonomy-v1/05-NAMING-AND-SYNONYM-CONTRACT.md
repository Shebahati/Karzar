# Naming and Synonym Contract

**Status:** Proposed design (Phase 1A)

---

## 1. Fields

| Field | Rule |
|-------|------|
| `name_fa` | Single preferred Persian technical term; no synonym stuffing; no `(a-b-c)` packs |
| `name_en` | Singular canonical engineering class name where appropriate; no brand; no marketing fluff |
| `code` | Immutable published identity token (see identity contract) |
| `slug` | URL-safe; mutable with redirect; not identity |
| `synonyms[]` | FA/EN alternate labels for search/import |
| `abbreviations` | Synonym entries, not canonical name |
| `trade_names` | Marked trade/trademark; never default scientific type name |
| `oem_vocabulary` | Series/model aliases under synonym/OEM series |

---

## 2. Persian rules

- Prefer established industrial Persian.
- One concept → one preferred `name_fa`.
- Market variants → synonyms.

**BAD (live):** `راپورتر(گیج بلوک-گیج بلاک)`  
**GOOD:**

```text
name_fa: بلوک گیج
name_en: Gauge Block
synonyms: گیج بلوک, گیج بلاک, راپورتر, Gage Block, Slip Gauge
```

---

## 3. English rules

- Prefer singular class names: `Turning Insert`, `Square End Mill`.
- Avoid: multi-alternative labels, brand names, “types of …”.
- US/UK spelling: pick one preferred (`Gauge`) + synonym (`Gage`).

---

## 4. Trademark / market term policy

| Term | Preferred scientific | Synonyms / trade |
|------|---------------------|------------------|
| HELICOIL | Wire Thread Insert / Thread Repair Insert | هلی‌کویل, Helicoil, HELICOIL® (trade) |
| Digimatic | (readout digital + Mitutoyo association) | Digimatic as trade synonym — not Product Type |
| Coromant Capto | Modular coupling interface | Trade/interface synonym → Property/Compatibility |
| Whistle Notch / Weldon | Shank flat standards | Property / Compatibility |

**Rule:** A trademark MUST NOT become the canonical Product Type merely because the Iranian market uses it generically.

**Helicoil system components** (spring, tap, kit) are related Products/Types + `PART_OF` / `REQUIRES` — not three scientific Domains.

---

## 5. Code naming

- ASCII `UPPER_SNAKE`.
- No Persian, no spaces, no brand tokens.
- Grandfathered PT codes (`GEN_CALIPER`) remain; new codes prefer `KZ.PT.*` namespace consistency in registries even if DB column stores short form.

---

## 6. CI proposals (design only)

- Synonym characters `(`, `/`, `–` densely in preferred name → fail
- Trademark tokens as sole PT `name_en` → fail
- Duplicate preferred names within parent → fail
- Code change on published entity → fail (require deprecate flow)
