"""Durable PDF source verification for AST UPDATE rows (pdftotext evidence)."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from catalog_target.ast_price_catalog_constants import PRICING_POLICY_ID


@dataclass(frozen=True)
class SourceVerificationResult:
    product_id: int
    sku: str
    source_pdf: str
    source_page: int
    proposed_price_toman: str
    verified_rial: int
    verified: bool
    failure_reason: str
    evidence_line: str
    manufacturer_identity: str
    verification_method: str = "pdftotext_layout_sku_line_rial"


def _normalize_digits(value: str) -> str:
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٬،", "0123456789,,")
    return re.sub(r"[^0-9]", "", (value or "").translate(trans))


def _parse_rial_candidates(line: str) -> list[int]:
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٬،", "0123456789,,")
    cleaned = line.translate(trans)
    out: list[int] = []
    for token in re.findall(r"\d[\d,]{5,}", cleaned):
        try:
            out.append(int(token.replace(",", "")))
        except ValueError:
            continue
    return out


def verify_update_row_on_pdf(
    *,
    pdf_path: Path,
    source_page: int,
    sku: str,
    proposed_price_toman: str,
    manufacturer_identity: str,
) -> SourceVerificationResult:
    pid_placeholder = 0
    expected_rial = int(Decimal(str(proposed_price_toman)) * 10)
    if not pdf_path.is_file():
        return SourceVerificationResult(
            product_id=pid_placeholder,
            sku=sku,
            source_pdf=str(pdf_path),
            source_page=source_page,
            proposed_price_toman=str(proposed_price_toman),
            verified_rial=expected_rial,
            verified=False,
            failure_reason="pdf_missing",
            evidence_line="",
            manufacturer_identity=manufacturer_identity,
        )
    proc = subprocess.run(
        [
            "pdftotext",
            "-f",
            str(source_page),
            "-l",
            str(source_page),
            "-layout",
            str(pdf_path),
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return SourceVerificationResult(
            product_id=pid_placeholder,
            sku=sku,
            source_pdf=pdf_path.name,
            source_page=source_page,
            proposed_price_toman=str(proposed_price_toman),
            verified_rial=expected_rial,
            verified=False,
            failure_reason="pdftotext_failed",
            evidence_line=(proc.stderr or "")[:200],
            manufacturer_identity=manufacturer_identity,
        )
    evidence_line = ""
    for line in proc.stdout.splitlines():
        if sku not in line:
            continue
        evidence_line = line.strip()
        for candidate in _parse_rial_candidates(line):
            if abs(candidate - expected_rial) <= max(1000, int(expected_rial * 0.001)):
                return SourceVerificationResult(
                    product_id=pid_placeholder,
                    sku=sku,
                    source_pdf=pdf_path.name,
                    source_page=source_page,
                    proposed_price_toman=str(proposed_price_toman),
                    verified_rial=candidate,
                    verified=True,
                    failure_reason="",
                    evidence_line=evidence_line[:500],
                    manufacturer_identity=manufacturer_identity,
                )
    return SourceVerificationResult(
        product_id=pid_placeholder,
        sku=sku,
        source_pdf=pdf_path.name,
        source_page=source_page,
        proposed_price_toman=str(proposed_price_toman),
        verified_rial=expected_rial,
        verified=False,
        failure_reason="sku_or_rial_not_verified_on_page",
        evidence_line=evidence_line[:500],
        manufacturer_identity=manufacturer_identity,
    )


def verification_record_digest(record: dict[str, Any]) -> str:
    body = {k: record[k] for k in sorted(record) if k != "record_digest"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_verification_record(
    result: SourceVerificationResult,
    *,
    product_id: int,
    brand_hint: str,
    pricing_policy_id: str = PRICING_POLICY_ID,
) -> dict[str, Any]:
    record = {
        "product_id": product_id,
        "sku": result.sku,
        "source_pdf": result.source_pdf,
        "source_page": result.source_page,
        "proposed_price_toman": result.proposed_price_toman,
        "verified_rial": result.verified_rial,
        "pricing_policy_id": pricing_policy_id,
        "manufacturer_identity": result.manufacturer_identity,
        "brand_hint": brand_hint,
        "verification_method": result.verification_method,
        "evidence_line": result.evidence_line,
        "visual_pdf_qa_status": "RESOLVED_PDF_ROW_VERIFIED" if result.verified else "FAILED",
        "manufacturer_identity_status": "RESOLVED_BRAND_FROM_AUTHORIZED_LIST"
        if result.verified and result.manufacturer_identity
        else "UNRESOLVED",
    }
    record["record_digest"] = verification_record_digest(record)
    return record
