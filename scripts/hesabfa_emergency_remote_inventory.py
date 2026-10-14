#!/usr/bin/env python3
"""Emergency read-only full Hesabfa item inventory (remote population only).

Pages every ``item/getItems`` row until ``fetched == TotalCount``. Writes a
timestamped audit under ``audit/hesabfa-emergency-remote-*/`` with SHA256SUMS.
Never calls write endpoints. Never logs credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.services.hesabfa.activation_reconcile import remote_inventory_stats  # noqa: E402
from app.services.hesabfa.client import HesabfaClient, get_hesabfa_client  # noqa: E402
from app.services.hesabfa.exceptions import HesabfaDisabledError, HesabfaError  # noqa: E402
from app.services.hesabfa.item_push import paginate_get_items  # noqa: E402

_ITEM_FIELDS = (
    "Code",
    "ProductCode",
    "Name",
    "ItemType",
    "Active",
    "BuyPrice",
    "SellPrice",
    "Barcode",
    "Unit",
    "Description",
    "NodeFamily",
    "Tax",
)


def _active_flag(raw: Any) -> str:
    if raw is True or raw in {1, "1", "true", "True"}:
        return "true"
    if raw is False or raw in {0, "0", "false", "False"}:
        return "false"
    return "unknown"


def _row_from_item(item: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in _ITEM_FIELDS:
        val = item.get(key)
        if key == "Active":
            out[key] = _active_flag(val)
        elif val is None:
            out[key] = ""
        else:
            out[key] = str(val)
    extras = {k: v for k, v in item.items() if k not in _ITEM_FIELDS}
    if extras:
        out["extra_json"] = json.dumps(extras, ensure_ascii=False, sort_keys=True)
    else:
        out["extra_json"] = ""
    return out


def _counts(rows: list[dict[str, str]]) -> dict[str, int]:
    active = inactive = unknown = 0
    for row in rows:
        flag = row.get("Active", "unknown")
        if flag == "true":
            active += 1
        elif flag == "false":
            inactive += 1
        else:
            unknown += 1
    return {
        "TOTAL_REMOTE": len(rows),
        "ACTIVE_BEFORE": active,
        "INACTIVE_BEFORE": inactive,
        "UNKNOWN_ACTIVE": unknown,
    }


def _sha256sums(directory: Path) -> None:
    lines: list[str] = []
    for path in sorted(directory.iterdir()):
        if path.name == "SHA256SUMS.txt" or path.is_dir():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    (directory / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _run(page_size: int, out_dir: Path, *, fetch_quantity: bool) -> dict[str, Any]:
    if not settings.HESABFA_ENABLED:
        raise SystemExit("HESABFA_ENABLED=false — enable only for read-only snapshot, then disable")
    client = get_hesabfa_client()
    if not client.is_configured():
        raise SystemExit("Hesabfa not configured")

    page = await paginate_get_items(client, page_size=page_size)
    items = page.items
    reported = page.reported_total
    if len(items) != reported:
        raise HesabfaError(
            f"pagination mismatch fetched={len(items)} reported_total={reported}"
        )

    rows = [_row_from_item(item) for item in items]
    counts = _counts(rows)
    if counts["UNKNOWN_ACTIVE"] != 0:
        raise HesabfaError(f"UNKNOWN_ACTIVE={counts['UNKNOWN_ACTIVE']}")

    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    csv_path = out_dir / "REMOTE_ITEMS.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(_ITEM_FIELDS) + ["extra_json"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    inactive_codes = [r["Code"] for r in rows if r.get("Active") == "false"]
    (out_dir / "INACTIVE_CODES.csv").write_text(
        "Code\n" + "\n".join(inactive_codes) + ("\n" if inactive_codes else ""),
        encoding="utf-8",
    )

    quantity_summary: dict[str, Any] = {"fetched": False, "reason": "not_requested"}
    if fetch_quantity and inactive_codes:
        # Sample quantities for inactive subset only (bounded); full qty audit is optional.
        quantity_summary = {"fetched": False, "reason": "emergency_inventory_skips_bulk_quantity"}

    summary = {
        "snapshot_utc": snapshot_utc,
        "reported_total": reported,
        "fetched_count": len(items),
        "pagination_proven": len(items) == reported,
        **counts,
        "remote_inventory_stats": remote_inventory_stats(items),
        "quantity": quantity_summary,
        "ITEM_SAVE_CONTRACT": "UNKNOWN",
        "ACTIVATION_APPLY_STATUS": "BLOCKED_SAFE_HESABFA_ACTIVATION_METHOD_NOT_PROVEN",
        "policy_note": (
            "Repository blocks item/save activation until existing-item semantics are proven. "
            "Use INACTIVE_CODES.csv for Owner UI activation if required."
        ),
    }
    (out_dir / "REMOTE_INVENTORY_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _sha256sums(out_dir)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Audit directory (default: audit/hesabfa-emergency-remote-<utc>)",
    )
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--fetch-quantity", action="store_true")
    args = parser.parse_args(argv)

    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
    out_dir = args.out_dir or (ROOT / "audit" / f"hesabfa-emergency-remote-{stamp}")

    try:
        summary = asyncio.run(
            _run(args.page_size, out_dir, fetch_quantity=args.fetch_quantity)
        )
    except HesabfaDisabledError:
        print("hesabfa_disabled", file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
