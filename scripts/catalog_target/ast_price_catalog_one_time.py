"""CLI entrypoint for AST one-time price/catalog reconcile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from catalog_target.ast_price_catalog_reconcile import run_reconcile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AST one-time price/catalog reconcile")
    parser.add_argument("--audit-dir", type=Path, default=Path("audit/ast-price-and-catalog-20261024"))
    parser.add_argument(
        "--candidates-csv",
        type=Path,
        default=Path(
            "audit/ast-price-and-catalog-20261024/work/supplier_price_candidates_NOT_FOR_APPLY.csv"
        ),
    )
    parser.add_argument(
        "--catalog-csv",
        type=Path,
        default=Path("audit/ast-price-and-catalog-20261024/CATALOG_SNAPSHOT_20261024.csv"),
    )
    parser.add_argument(
        "--categories-csv",
        type=Path,
        default=Path("audit/ast-price-and-catalog-20261024/CATEGORIES_SNAPSHOT_20261024.csv"),
    )
    parser.add_argument(
        "--source-docs-csv",
        type=Path,
        default=Path("audit/ast-price-and-catalog-20261024/work/source_documents.csv"),
    )
    parser.add_argument(
        "--source-zip",
        type=Path,
        default=Path("audit/ast-price-and-catalog-20261024/source/AST(2).zip"),
    )
    args = parser.parse_args(argv)
    report = run_reconcile(
        audit_dir=args.audit_dir,
        candidates_csv=args.candidates_csv,
        catalog_csv=args.catalog_csv,
        categories_csv=args.categories_csv,
        source_docs_csv=args.source_docs_csv,
        source_zip=args.source_zip,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
