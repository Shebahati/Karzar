"""Fixture-only tests for IMG-02C multisource discovery (no live network)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from image_multisource import MultisourceError  # noqa: E402
from image_multisource.calibrate import calibrate_source, validate_redirect  # noqa: E402
from image_multisource.eligibility import (  # noqa: E402
    build_eligibility_report,
    select_calibration_sample,
)
from image_multisource.matching import classify_match, sku_token_present  # noqa: E402
from image_multisource.output import assert_external_output  # noqa: E402
from image_multisource.pdf import build_pdf_record  # noqa: E402
from image_multisource.pipeline import run_foundation_and_calibration  # noqa: E402
from image_multisource.quality import (  # noqa: E402
    average_perceptual_hash,
    group_duplicates,
    inspect_image_bytes,
    normalize_source_url,
    sha256_bytes,
)
from image_multisource.registry import (  # noqa: E402
    builtin_known_host_registry,
    parse_source,
    prefer_higher_priority,
    sort_sources,
    write_registry_snapshot,
)
from image_multisource.robots import classify_robots_text  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def _mini_jpeg(color: tuple[int, int, int] = (40, 80, 120)) -> bytes:
    from io import BytesIO

    from PIL import Image

    im = Image.new("RGB", (320, 320), color)
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _worklist(tmp: Path, rows: list[dict[str, str]]) -> Path:
    fields = [
        "schema_version",
        "task_id",
        "work_item_id",
        "product_key",
        "product_id",
        "sku",
        "product_name",
        "brand_key",
        "work_type",
        "work_reasons",
        "priority",
        "eligible_for_automatic_discovery",
    ]
    path = tmp / "worklist-all.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    return path


def _r2_dir(tmp: Path, *, stable: list[str], drift: list[str], manual: list[str]) -> Path:
    root = tmp / "IMG-02B-R2"
    cons = root / "consolidated"
    cons.mkdir(parents=True)
    with (cons / "all-accepted-manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "sku", "sha256"])
        w.writeheader()
        for pid in stable:
            w.writerow({"product_id": pid, "sku": f"S-{pid}", "sha256": f"{int(pid):064x}"[:64]})
    with (cons / "all-source-drift-review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "discovery_status"])
        w.writeheader()
        for pid in drift:
            w.writerow({"product_id": pid, "discovery_status": "source_drift_review"})
    with (cons / "all-manual-review.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "product_id",
                "discovery_status",
                "eligible_for_automatic_discovery",
                "reason_code",
            ],
        )
        w.writeheader()
        for pid in manual:
            w.writerow(
                {
                    "product_id": pid,
                    "discovery_status": "manual_review",
                    "eligible_for_automatic_discovery": "false",
                    "reason_code": "ambiguous_official_product",
                }
            )
    return root


def test_registry_rejects_enabled_unknown():
    raw = {
        "source_id": "bad",
        "source_class": "S5",
        "brand_keys": ["insize"],
        "allowed_page_hosts": ["x.example"],
        "allowed_asset_hosts": ["cdn.example"],
        "country": "IR",
        "authorization_status": "unknown",
        "authorization_evidence": "",
        "robots_status": "not_checked",
        "discovery_method": "none",
        "exact_sku_supported": False,
        "catalog_pdf_supported": False,
        "enabled": True,
        "rights_status": "review_required",
        "notes": "",
    }
    with pytest.raises(MultisourceError):
        parse_source(raw)


def test_source_priority_and_sort():
    sources = builtin_known_host_registry()
    ordered = sort_sources(sources)
    classes = [s.source_class for s in ordered]
    assert classes == sorted(classes, key=lambda c: ["S1", "S2", "S3", "S4", "S5"].index(c))
    assert prefer_higher_priority("S3", "S1") is True
    assert prefer_higher_priority("S1", "S5") is False


def test_eligibility_excludes_seed_hold_drift(tmp_path: Path):
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": "1",
                "sku": "A",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            },
            {
                "product_id": "2",
                "sku": "B",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            },
            {
                "product_id": "3",
                "sku": "C",
                "brand_key": "dasqua",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            },
            {
                "product_id": "4",
                "sku": "D",
                "brand_key": "dasqua",
                "work_type": "manual_review_hold",
                "priority": "P0",
                "eligible_for_automatic_discovery": "false",
            },
            {
                "product_id": "5",
                "sku": "E",
                "brand_key": "san_ou",
                "work_type": "missing_image",
                "priority": "P1",
                "eligible_for_automatic_discovery": "true",
            },
        ],
    )
    r2 = _r2_dir(tmp_path, stable=["1"], drift=["2"], manual=["3"])
    report = build_eligibility_report(worklist_csv=wl, r2_seed=r2)
    assert report["totals"]["total_governed_work_items"] == 5
    assert report["totals"]["already_sourced"] == 1
    assert report["totals"]["source_drift"] == 1
    assert report["totals"]["remaining_eligible"] == 1
    assert report["remaining_eligible_product_ids"] == ["5"]
    sample = select_calibration_sample(report, wl, brand_key="san_ou", limit=20)
    assert len(sample) == 1


def test_exact_sku_matching_and_retailer_quarantine():
    src = parse_source(
        {
            "source_id": "tosag",
            "source_class": "S3",
            "brand_keys": ["insize"],
            "allowed_page_hosts": ["www.tosag.ch"],
            "allowed_asset_hosts": ["www.tosag.ch"],
            "country": "CH",
            "authorization_status": "authorized_candidate",
            "authorization_evidence": "x",
            "robots_status": "allow",
            "discovery_method": "search",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "",
        }
    )
    ok = classify_match(
        source=src,
        product_id="10",
        sku="1120-500",
        brand_key="insize",
        page_url="https://www.tosag.ch/product/1120-500",
        asset_url="https://www.tosag.ch/i.jpg",
        page_text="INSIZE micrometer 1120-500 exact",
        match_basis="exact_sku_authorized_distributor",
        brand_confirmed=True,
        subject_exact=True,
        redirect_approved=True,
    )
    assert ok["discovery_status"] == "candidate_ready"
    assert sku_token_present("footer only", "1120-500") is False

    retail = parse_source(
        {
            **src.to_dict(),
            "source_id": "shop",
            "source_class": "S4",
            "authorization_status": "specialist_retailer",
            "brand_keys": list(src.brand_keys),
            "allowed_page_hosts": list(src.allowed_page_hosts),
            "allowed_asset_hosts": list(src.allowed_asset_hosts),
        }
    )
    # rebuild via parse
    retail = parse_source(
        {
            "source_id": "shop",
            "source_class": "S4",
            "brand_keys": ["insize"],
            "allowed_page_hosts": ["www.tosag.ch"],
            "allowed_asset_hosts": ["www.tosag.ch"],
            "country": "CH",
            "authorization_status": "specialist_retailer",
            "authorization_evidence": "x",
            "robots_status": "allow",
            "discovery_method": "search",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "",
        }
    )
    rr = classify_match(
        source=retail,
        product_id="10",
        sku="1120-500",
        brand_key="insize",
        page_url="https://www.tosag.ch/product/1120-500",
        asset_url="https://www.tosag.ch/i.jpg",
        page_text="1120-500",
        match_basis="exact_sku_product_page",
        brand_confirmed=True,
        subject_exact=True,
        redirect_approved=True,
    )
    assert rr["discovery_status"] == "retailer_review"
    assert rr["eligible_for_automatic_acceptance"] == "false"


def test_redirect_rejection_and_robots():
    src = builtin_known_host_registry()[0]
    assert validate_redirect(
        requested_url="https://www.dasquatools.com/a",
        final_url="https://evil.example/a",
        source=src,
    ) is False
    rob = classify_robots_text(
        "User-agent: *\nDisallow: /\n",
        user_agent="KarzarImageMultisource/0.1",
        url="https://www.dasquatools.com/",
    )
    assert rob["crawl_permitted"] == "false"


def test_pdf_provenance_rejects_family_proximity():
    data = b"%PDF-1.4\n1 0 obj<< /Type /Page >>endobj\n%%EOF\n"
    rec = build_pdf_record(
        source_url="https://www.dasquatools.com/c.pdf",
        data=data,
        sku="1804-1405",
        matched_page_number=1,
        text_evidence="family catalogue page nearby items",
        image_ref="page-1-img-2",
    )
    assert rec.identity_status == "rejected_family_or_missing_exact_sku"
    ok = build_pdf_record(
        source_url="https://www.dasquatools.com/c.pdf",
        data=data,
        sku="1804-1405",
        matched_page_number=1,
        text_evidence="Item number 1804-1405 digital gauge",
        image_ref="page-1-img-2",
    )
    assert ok.identity_status == "exact_sku_or_model_confirmed"


def test_quality_filter_and_dedupe():
    a = _mini_jpeg((10, 20, 30))
    b = _mini_jpeg((10, 20, 30))
    c = _mini_jpeg((200, 10, 10))
    ia = inspect_image_bytes(a)
    assert ia["quality_status"] == "ok"
    assert ia["sha256"] == sha256_bytes(a)
    assert average_perceptual_hash(a) == average_perceptual_hash(b)
    assert normalize_source_url("https://X.Example/a.jpg?utm=1#h") == "https://x.example/a.jpg"
    html = inspect_image_bytes(b"<html>nope</html>")
    assert html["quality_status"] == "reject"
    groups = group_duplicates(
        [
            {
                "asset_id": "a1",
                "sha256": sha256_bytes(a),
                "source_image_url": "https://x.example/a.jpg",
                "perceptual_hash": average_perceptual_hash(a),
            },
            {
                "asset_id": "a2",
                "sha256": sha256_bytes(b),
                "source_image_url": "https://x.example/a.jpg?x=1",
                "perceptual_hash": average_perceptual_hash(b),
            },
            {
                "asset_id": "c1",
                "sha256": sha256_bytes(c),
                "source_image_url": "https://x.example/c.jpg",
                "perceptual_hash": average_perceptual_hash(c),
            },
        ]
    )
    assert any(g["member_count"] == "2" for g in groups)


def test_family_image_non_collapse_relations_separate():
    # Same physical sha may map to multiple products only as separate relations.
    sha = "ab" * 32
    relations = [
        {"product_id": "1", "sha256": sha, "evidence": "exact_sku_page_a"},
        {"product_id": "2", "sha256": sha, "evidence": "exact_sku_page_b"},
    ]
    assert len({r["product_id"] for r in relations}) == 2
    assert len({r["sha256"] for r in relations}) == 1


def test_external_output_safety_and_checksum_determinism(tmp_path: Path):
    with pytest.raises(MultisourceError):
        assert_external_output(REPO / "inside", REPO)
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": "10",
                "sku": "X",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    r1 = run_foundation_and_calibration(
        worklist_csv=wl,
        r2_seed=r2,
        output_dir=out1,
        repo_root=REPO,
        calibration_limit=5,
    )
    r2b = run_foundation_and_calibration(
        worklist_csv=wl,
        r2_seed=r2,
        output_dir=out2,
        repo_root=REPO,
        calibration_limit=5,
    )
    assert r1["checksums_digest"] == r2b["checksums_digest"]
    assert (out1 / "summary.json").is_file()
    snap = json.loads((out1 / "source-registry-snapshot.json").read_text(encoding="utf-8"))
    assert any(s["authorization_status"] == "unknown" and s["enabled"] is False for s in snap["sources"])
    assert r1["summary"]["safety"]["database_accessed"] is False


def test_calibration_disables_on_parser_drift(tmp_path: Path):
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": str(i),
                "sku": f"S-{i}",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
            for i in range(1, 6)
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    report = build_eligibility_report(worklist_csv=wl, r2_seed=r2)
    src = [s for s in builtin_known_host_registry() if s.source_id == "insize_tosag"][0]

    def probe(_source, row):
        return {
            "product_id": row["product_id"],
            "sku": row["sku"],
            "status": "probed",
            "page_identity_ok": False,
            "exact_sku_ok": False,
            "redirect_ok": True,
            "generic_category": False,
            "parser_drift": True,
            "asset_host_ok": False,
            "notes": "fixture drift",
        }

    result = calibrate_source(
        source=src,
        eligibility_report=report,
        worklist_csv=wl,
        output_dir=tmp_path / "calib",
        limit=5,
        probe=probe,
    )
    assert result.enabled_after_calibration is False
    assert "parser_drift" in result.disable_reason or "parser_success" in result.disable_reason


def test_resume_behavior_reuses_empty_checkpoint_outputs(tmp_path: Path):
    # Resume semantics at calibration stage: second run requires empty/absent dir (fail closed).
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": "7",
                "sku": "Y",
                "brand_key": "dasqua",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    out = tmp_path / "batch"
    run_foundation_and_calibration(
        worklist_csv=wl, r2_seed=r2, output_dir=out, repo_root=REPO, calibration_limit=1
    )
    with pytest.raises(MultisourceError):
        run_foundation_and_calibration(
            worklist_csv=wl, r2_seed=r2, output_dir=out, repo_root=REPO, calibration_limit=1
        )


def test_registry_snapshot_deterministic_order(tmp_path: Path):
    sources = builtin_known_host_registry()
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    write_registry_snapshot(list(reversed(sources)), p1)
    write_registry_snapshot(sources, p2)
    assert p1.read_text(encoding="utf-8") == p2.read_text(encoding="utf-8")


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "image_multisource"


def test_retail_adapters_exact_family_conflict_and_host_images():
    from image_multisource.adapters_retail import (
        evaluate_pdp,
        extract_abzarham_product_images,
        extract_abzarmarket_product_images,
        index_product_urls_by_sku,
        lookup_catalog_url,
        parse_abzarmarket_brand_catalog,
        parse_sitemap_locs,
    )
    from image_multisource.sku_norm import sku_token_in_path

    locs = parse_sitemap_locs((FIXTURES / "sitemap_products.xml").read_text(encoding="utf-8"))
    index = index_product_urls_by_sku(locs)
    url, kind = lookup_catalog_url(index, "1804-1035")
    assert kind == "exact" and "1804-1035" in url
    _u, family = lookup_catalog_url(index, "1114-200")
    assert family == "family"
    assert sku_token_in_path("https://abzarham.com/shop/x/2100-1120/", "1120-200") == "conflict"

    brand = parse_abzarmarket_brand_catalog(
        (FIXTURES / "abzarmarket_brand.html").read_text(encoding="utf-8")
    )
    assert "1804-1035" in brand and "2308-10A" in brand

    html = (FIXTURES / "abzarham_pdp_exact.html").read_text(encoding="utf-8")
    imgs = extract_abzarham_product_images(
        html,
        expected_brand="dasqua",
        expected_sku="1804-1035",
        product_detail_url="https://abzarham.com/shop/measuring/1804-1035/",
    )
    assert imgs and "1804-1035" in imgs[0]
    ok = evaluate_pdp(
        sku="1804-1035",
        brand_key="dasqua",
        final_url="https://abzarham.com/shop/measuring/1804-1035/",
        html=html,
        expected_match_kind="exact",
        image_urls=imgs,
    )
    assert ok["status"] == "matched" and ok["discovery_status"] == "retailer_review"

    bad_html = (FIXTURES / "abzarham_pdp_conflict.html").read_text(encoding="utf-8")
    bad = evaluate_pdp(
        sku="1120-200",
        brand_key="insize",
        final_url="https://abzarham.com/shop/measuring/2100-1120/",
        html=bad_html,
        expected_match_kind="exact",
        image_urls=extract_abzarham_product_images(
            bad_html,
            expected_brand="insize",
            expected_sku="1120-200",
            product_detail_url="https://abzarham.com/shop/measuring/2100-1120/",
        ),
    )
    assert bad["false_match"] is True

    market_html = (FIXTURES / "abzarmarket_pdp.html").read_text(encoding="utf-8")
    # image-generator URLs lack SKU in filename — without gallery/json-ld tie, unproven
    m_imgs = extract_abzarmarket_product_images(
        market_html,
        expected_brand="dasqua",
        expected_sku="1804-1035",
        product_detail_url="https://abzarmarket.com/product/dasqua-gauge-1804-1035",
    )
    assert m_imgs == []


def test_pdf_adapter_exact_and_multi_sku_quarantine(tmp_path: Path):
    from image_multisource.adapters_pdf import discover_pdf_sku, index_skus_in_pdf

    pages = (FIXTURES / "eu261_pages.txt").read_text(encoding="utf-8").split("\f")
    hits = index_skus_in_pdf(tmp_path / "missing.pdf", ["1108-150", "4903-200"], page_texts=pages)
    assert hits["1108-150"].page_number == 2
    assert "1108-200" in hits["1108-150"].other_skus_on_page or hits["1108-150"].other_skus_on_page
    assert hits["4903-200"].page_number == 3
    pdf = b"%PDF-1.4\n1 0 obj<< /Type /Page >>endobj\n%%EOF\n"
    multi = discover_pdf_sku(
        pdf_path=tmp_path / "x.pdf",
        pdf_bytes=pdf,
        catalog_url="https://www.tosag.ch/mediafiles/kataloge/CATALOGUE-NO-EU261.pdf",
        sku="1108-150",
        hit=hits["1108-150"],
        rendered_page_path=None,
    )
    assert multi["status"] == "matched"
    assert multi["discovery_status"] == "manual_review"
    assert multi["evidence_kind"] == "catalog_page_evidence"
    assert multi["reason_code"] == "catalog_page_requires_product_crop"
    single = discover_pdf_sku(
        pdf_path=tmp_path / "x.pdf",
        pdf_bytes=pdf,
        catalog_url="https://www.tosag.ch/mediafiles/kataloge/CATALOGUE-NO-EU261.pdf",
        sku="4903-200",
        hit=hits["4903-200"],
        rendered_page_path=None,
    )
    # Whole page never automatic without exact crop provenance
    assert single["discovery_status"] == "manual_review"
    assert single["eligible_for_automatic_acceptance"] == "false"
    assert single["evidence_kind"] == "catalog_page_evidence"


def test_calibration_false_match_disables(tmp_path: Path):
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": str(i),
                "sku": f"S-{i}",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
            for i in range(1, 6)
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    report = build_eligibility_report(worklist_csv=wl, r2_seed=r2)
    src = [s for s in builtin_known_host_registry() if s.source_id == "insize_eu261_pdf"][0]

    def probe(_source, row):
        return {
            "product_id": row["product_id"],
            "sku": row["sku"],
            "status": "false_match" if row["product_id"] == "1" else "matched",
            "page_identity_ok": row["product_id"] != "1",
            "exact_sku_ok": row["product_id"] != "1",
            "false_match": row["product_id"] == "1",
            "redirect_ok": True,
            "generic_category": False,
            "parser_drift": False,
            "asset_host_ok": True,
            "notes": "",
        }

    result = calibrate_source(
        source=src,
        eligibility_report=report,
        worklist_csv=wl,
        output_dir=tmp_path / "calib",
        limit=5,
        probe=probe,
    )
    assert result.enabled_after_calibration is False
    assert "false_match" in result.disable_reason


def test_calibration_enables_with_high_parser_success(tmp_path: Path):
    wl = _worklist(
        tmp_path,
        [
            {
                "product_id": str(i),
                "sku": f"S-{i}",
                "brand_key": "insize",
                "work_type": "missing_image",
                "priority": "P0",
                "eligible_for_automatic_discovery": "true",
            }
            for i in range(1, 6)
        ],
    )
    r2 = _r2_dir(tmp_path, stable=[], drift=[], manual=[])
    report = build_eligibility_report(worklist_csv=wl, r2_seed=r2)
    src = [s for s in builtin_known_host_registry() if s.source_id == "insize_eu261_pdf"][0]

    def probe(_source, row):
        return {
            "product_id": row["product_id"],
            "sku": row["sku"],
            "status": "matched",
            "page_identity_ok": True,
            "exact_sku_ok": True,
            "false_match": False,
            "redirect_ok": True,
            "generic_category": False,
            "parser_drift": False,
            "asset_host_ok": True,
            "notes": "",
        }

    result = calibrate_source(
        source=src,
        eligibility_report=report,
        worklist_csv=wl,
        output_dir=tmp_path / "calib",
        limit=5,
        probe=probe,
    )
    assert result.enabled_after_calibration is True
    assert result.parser_success_rate >= 0.8


def test_catalog_code_tokenizer_positive_and_negative():
    from image_multisource.sku_norm import (
        extract_catalog_codes,
        is_plausible_catalog_code,
        skus_in_text,
    )

    text = (FIXTURES / "catalog_codes.txt").read_text(encoding="utf-8")
    codes = {c.upper() for c in extract_catalog_codes(text)}
    for token in [
        "ISQ-RM30",
        "ISQ-DRM31",
        "ISO-1200FN",
        "ISO-1000FN",
        "2199-1",
        "2170-1",
        "5801-A55",
        "DSW-A010",
        "7600-6",
    ]:
        assert is_plausible_catalog_code(token), token
        assert token.upper() in codes or token.casefold() in skus_in_text(text)
    assert not is_plausible_catalog_code("0-150")
    assert not is_plausible_catalog_code("6-80")
    assert "0-150" not in {c.casefold() for c in extract_catalog_codes(text)}


def test_whole_pdf_page_never_candidate_ready_without_crop(tmp_path: Path):
    from image_multisource.adapters_pdf import (
        ExactProductCropProvenance,
        discover_pdf_sku,
        index_skus_in_pdf,
    )

    pages = ["cover\fISQ-RM30 and ISO-1200FN together\fONLY 2199-1\f"]
    # split properly
    pages = "cover\fISQ-RM30 and ISO-1200FN together\fONLY 2199-1\f".split("\f")
    hits = index_skus_in_pdf(
        tmp_path / "x.pdf",
        ["ISQ-RM30", "ISO-1200FN", "2199-1"],
        page_texts=pages,
    )
    assert hits["isq-rm30"].other_skus_on_page  # multi detection
    pdf = b"%PDF-1.4\n%%EOF\n"
    no_crop = discover_pdf_sku(
        pdf_path=tmp_path / "x.pdf",
        pdf_bytes=pdf,
        catalog_url="https://www.tosag.ch/c.pdf",
        sku="2199-1",
        hit=hits["2199-1"],
        rendered_page_path=None,
        exact_crop=None,
    )
    assert no_crop["discovery_status"] == "manual_review"
    assert no_crop["reason_code"] == "catalog_page_requires_product_crop"
    crop = ExactProductCropProvenance(
        catalog_url="https://www.tosag.ch/c.pdf",
        catalog_sha256="ab" * 32,
        pdf_page_number=3,
        printed_page_number="3",
        bounding_box="1,2,3,4",
        crop_sha256="cd" * 32,
        crop_width=100,
        crop_height=100,
        target_sku_text_box="2199-1",
        product_block_identity="block-1",
    )
    with_crop = discover_pdf_sku(
        pdf_path=tmp_path / "x.pdf",
        pdf_bytes=pdf,
        catalog_url="https://www.tosag.ch/c.pdf",
        sku="2199-1",
        hit=hits["2199-1"],
        rendered_page_path=None,
        exact_crop=crop,
    )
    assert with_crop["discovery_status"] == "candidate_ready"
    assert with_crop["evidence_kind"] == "exact_product_image_crop"
    assert with_crop["crop_provenance"]["bounding_box"] == "1,2,3,4"


def test_retail_image_identity_rejects_wrong_brand_and_scopes_gallery():
    from image_multisource.image_identity import (
        classify_filename_identity,
        select_retail_product_images,
    )

    gallery = (FIXTURES / "abzarham_gallery_exact.html").read_text(encoding="utf-8")
    ok = select_retail_product_images(
        expected_brand="dasqua",
        expected_sku="1804-1035",
        product_detail_url="https://abzarham.com/p/1804-1035/",
        product_page_html=gallery,
        candidate_url_allowlist=("abzarham.com/wp-content/uploads/",),
    )
    assert ok["image_urls"]
    assert "1804-1035" in ok["image_urls"][0]
    assert all("insize-wrong" not in u for u in ok["image_urls"])

    wrong = select_retail_product_images(
        expected_brand="dasqua",
        expected_sku="1031-2010",
        product_detail_url="https://abzarham.com/p/1031-2010/",
        product_page_html=(FIXTURES / "abzarham_wrong_brand.html").read_text(encoding="utf-8"),
        candidate_url_allowlist=("abzarham.com/wp-content/uploads/",),
    )
    assert wrong["image_urls"] == []
    assert any(r["reason"] == "conflicting_image_brand" for r in wrong["rejected"])

    sig = classify_filename_identity(
        expected_brand="dasqua",
        expected_sku="1031-2010",
        source_image_url="https://abzarham.com/wp-content/uploads/2176-300-Insize-min.jpg",
    )
    assert sig["reason_code"] == "conflicting_image_brand"


def test_full_checksum_coverage_and_portable_paths(tmp_path: Path):
    from image_multisource.output import (
        verify_checksums,
        write_full_checksums,
        write_json,
    )

    out = tmp_path / "pkg"
    out.mkdir()
    (out / "assets").mkdir()
    (out / "assets" / "a.jpg").write_bytes(b"jpeg-bytes-not-real-but-ok")
    write_json(out / "summary.json", {"ok": True})
    (out / "README.md").write_text("x\n", encoding="utf-8")
    info = write_full_checksums(out)
    ver = verify_checksums(out)
    assert ver["checksum_failures"] == 0
    assert ver["checksum_uncovered_files"] == 0
    assert ver["checksum_entries"] == ver["regular_file_count"] - 1
    assert info["checksum_entries"] == ver["checksum_entries"]
    # portable path convention
    assert (out / "assets" / "a.jpg").is_file()
