# TASK-RECORD · IMG-02A-01-R1

| Field | Value |
|-------|-------|
| Task ID | IMG-02A-01-R1 |
| Title | Close pre-authoritative boundary blockers (existing image audit) |
| Parent | IMG-02A-01 |
| Change class | C2 |
| Branch | `feat/existing-image-audit` |
| Status | in_progress |

## Goal

Harden IMG-02A-01 read-only inventory boundaries before an authoritative VPS run: URL marker exactness, storage-index-only file meta, SQL guard tightening, atomic staged publish, coverage/duplicate correctness, and `--no-storage-scan` semantics.

## Corrections delivered (R1)

1. **URL classification** — exact marker `/static/uploads/products/`; HTTP(S) URLs with marker map as `internal_static_absolute`; lookalike paths rejected; userinfo/query/fragment stripped; `url_host` preserved.
2. **file_meta / storage_index** — no filesystem fallback on index miss; rejected-ancestor propagation; `O_RDONLY|O_NOFOLLOW` + per-component `lstat`.
3. **Path disjointness** — reject `output_dir == storage_root` or nesting; summary adds `storage_modified=false`, `storage_mutations=0`.
4. **SQL guard** — allow only exact `SET TRANSACTION READ ONLY` and `SHOW transaction_read_only`; PRAGMA allowlist; CLI operational runs require PostgreSQL with `transaction_read_only=on`.
5. **Status order** — `local_entry_status` evaluated before `missing_local_file`.
6. **`--no-storage-scan`** — no storage-root existence requirement; zero FS reads; `local_unverified` / `storage_scan_skipped`.
7. **Duplicate keys** — external: scheme+host+port+path; internal: mapped relative path.
8. **Coverage** — `products_with_image_rows` scoped to selected inventory; true orphans retained; excluded deleted products not false orphan anomalies.
9. **Atomic publish** — stage outside output; publish after streamed checksums; failure leaves output empty.
10. **Pillow bomb** — `DecompressionBombWarning`/`Error` → isolated `decode_failed`.

## Evidence (authoritative run)

```text
authoritative run status: AUTHORITATIVE RUN BLOCKED
blocker: no VPS SSH / authoritative DATABASE_URL from this environment
network request count = 0 (by design; no run performed)
database writes = 0 (by design; no run performed)
storage mutations = 0 (by design; no run performed)
```

## Local validation

- `tests/test_existing_image_audit.py`: 43 passed (25 original + 18 R1)
- PYTHONHASHSEED 0–9: passed
- `tests/test_image_discovery*.py`: 110 passed
- ruff + aods_validate gates: PASS
