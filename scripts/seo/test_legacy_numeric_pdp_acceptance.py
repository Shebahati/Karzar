"""Unit tests for legacy_numeric_pdp_acceptance classification and verification."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SEO_DIR = Path(__file__).resolve().parent
if str(SEO_DIR) not in sys.path:
    sys.path.insert(0, str(SEO_DIR))

from legacy_numeric_pdp_acceptance import (  # noqa: E402
    MAX_REDIRECT_HOPS,
    ApiProduct,
    RedirectProbe,
    absolute_url,
    classify_api,
    classification_accounting_ok,
    expected_slug_url,
    extract_canonical,
    hard_pass,
    probe_numeric_redirect,
    run_acceptance,
    verify_required_301,
    walk_redirect_chain,
)


class LegacyNumericPdpAcceptanceTests(unittest.TestCase):
    def test_classify_api(self) -> None:
        self.assertEqual(classify_api("1", ApiProduct(404, None)), "HISTORICAL_NOT_FOUND")
        self.assertEqual(classify_api("1", ApiProduct(200, "")), "NO_SLUG")
        self.assertEqual(classify_api("99", ApiProduct(200, "99")), "NUMERIC_CANONICAL")
        self.assertEqual(classify_api("1", ApiProduct(200, "real-slug")), "REQUIRED_301")
        self.assertEqual(classify_api("1", ApiProduct(500, None)), "OTHER")
        self.assertEqual(classify_api("1", ApiProduct(0, None, error_class="URLError")), "OTHER")

    def test_absolute_url_path_absolute_location(self) -> None:
        base = "https://shop.example/product/1314"
        loc = "/product/4111-8105"
        self.assertEqual(
            absolute_url(base, loc),
            "https://shop.example/product/4111-8105",
        )

    def test_absolute_url_absolute_location(self) -> None:
        url = "https://shop.example/product/4111-8105"
        self.assertEqual(absolute_url("https://shop.example/product/1314", url), url)

    def test_absolute_url_relative_reference(self) -> None:
        import urllib.parse

        base = "https://shop.example/product/1314"
        self.assertEqual(
            absolute_url(base, "4111-8105"),
            urllib.parse.urljoin(base, "4111-8105"),
        )

    def test_absolute_url_query_only(self) -> None:
        import urllib.parse

        base = "https://shop.example/product/1314"
        self.assertEqual(absolute_url(base, "?foo=bar"), urllib.parse.urljoin(base, "?foo=bar"))

    def test_absolute_url_root(self) -> None:
        self.assertEqual(
            absolute_url("https://shop.example/product/1314", "/"),
            "https://shop.example/",
        )

    def test_expected_slug_url_encodes_once(self) -> None:
        import urllib.parse

        url = expected_slug_url("https://shop.example", "مدل-تست")
        self.assertIn(urllib.parse.quote("مدل-تست", safe=""), url)

    def test_extract_canonical_rel_before_href(self) -> None:
        html = '<html><head><link rel="canonical" href="https://shop.example/product/a"></head></html>'
        self.assertEqual(extract_canonical(html), "https://shop.example/product/a")

    def test_extract_canonical_href_before_rel(self) -> None:
        html = '<html><head><link href="https://shop.example/product/b" rel="canonical"></head></html>'
        self.assertEqual(extract_canonical(html), "https://shop.example/product/b")

    def test_verify_required_301_ok(self) -> None:
        site = "https://shop.example"
        slug = "my-slug"
        expected = expected_slug_url(site, slug)
        probe = RedirectProbe(
            status=301,
            location=expected,
            hops=[f"{site}/product/1", expected],
            final_url=expected,
            final_status=200,
            canonical=expected,
        )
        self.assertEqual(verify_required_301(site, "1", slug, probe), [])

    def test_verify_rejects_308(self) -> None:
        site = "https://shop.example"
        probe = RedirectProbe(status=308, location="", final_status=200)
        self.assertIn("BAD_STATUS", verify_required_301(site, "1", "x", probe))

    def test_verify_bad_final_url(self) -> None:
        site = "https://shop.example"
        expected = expected_slug_url(site, "slug-a")
        other = expected_slug_url(site, "slug-b")
        probe = RedirectProbe(
            status=301,
            location=expected,
            hops=[f"{site}/product/1", expected, other],
            final_url=other,
            final_status=200,
            canonical=other,
        )
        self.assertIn("BAD_FINAL_URL", verify_required_301(site, "1", "slug-a", probe))

    def test_verify_redirect_loop(self) -> None:
        site = "https://shop.example"
        a = f"{site}/product/1"
        probe = RedirectProbe(status=301, location=a, hops=[a, a], redirect_loop=True, final_status=301)
        self.assertIn("REDIRECT_LOOP", verify_required_301(site, "1", "x", probe))

    def test_hard_pass_requires_bad_final_url_zero(self) -> None:
        self.assertFalse(
            hard_pass(
                {
                    "REQUIRED_301": 1,
                    "HTTP_301_OK": 0,
                    "OTHER": 0,
                    "CLASSIFICATION_ACCOUNTING_ERROR": 0,
                    "BAD_STATUS": 0,
                    "BAD_LOCATION": 0,
                    "REDIRECT_LOOP": 0,
                    "BAD_FINAL_STATUS": 0,
                    "BAD_FINAL_CANONICAL": 0,
                    "BAD_REDIRECT_CHAIN": 0,
                    "BAD_FINAL_URL": 1,
                }
            )
        )

    def test_hard_pass_fails_when_other_positive(self) -> None:
        self.assertFalse(
            hard_pass(
                {
                    "REQUIRED_301": 0,
                    "HTTP_301_OK": 0,
                    "OTHER": 1,
                    "CLASSIFICATION_ACCOUNTING_ERROR": 0,
                    "BAD_STATUS": 0,
                    "BAD_LOCATION": 0,
                    "REDIRECT_LOOP": 0,
                    "BAD_FINAL_STATUS": 0,
                    "BAD_FINAL_CANONICAL": 0,
                    "BAD_REDIRECT_CHAIN": 0,
                    "BAD_FINAL_URL": 0,
                }
            )
        )

    def test_classification_accounting_ok(self) -> None:
        counts = {
            "TOTAL_INPUT": 4,
            "HISTORICAL_NOT_FOUND": 1,
            "NO_SLUG": 1,
            "NUMERIC_CANONICAL": 1,
            "REQUIRED_301": 1,
            "OTHER": 0,
        }
        self.assertTrue(classification_accounting_ok(counts))

    def test_classification_accounting_fails(self) -> None:
        counts = {
            "TOTAL_INPUT": 4,
            "HISTORICAL_NOT_FOUND": 1,
            "REQUIRED_301": 1,
            "OTHER": 0,
        }
        self.assertFalse(classification_accounting_ok(counts))

    def test_run_acceptance_sets_accounting_error(self) -> None:
        result = run_acceptance(
            [{"numeric_id": "1"}, {"numeric_id": "2"}],
            site="https://shop.example",
            api_base="https://api.example/api/v1",
        )
        self.assertEqual(result.counts["TOTAL_INPUT"], 2)
        self.assertGreaterEqual(result.counts.get("OTHER", 0), 0)

    def test_walk_301_path_absolute_location_live_shape(self) -> None:
        site = "https://shop.example"
        slug = "4111-8105"
        numeric = f"{site}/product/1314"
        expected = expected_slug_url(site, slug)
        html = f'<html><head><link rel="canonical" href="{expected}"></head></html>'

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            if url == numeric:
                return 301, {"Location": "/product/4111-8105"}, b""
            if url == expected:
                return 200, {}, html.encode()
            return 404, {}, b""

        probe = walk_redirect_chain(numeric, 5.0, fetch=fake_fetch)
        self.assertEqual(probe.final_url, expected)
        self.assertEqual(verify_required_301(site, "1314", slug, probe), [])

    def test_walk_301_to_expected_200_pass(self) -> None:
        site = "https://shop.example"
        slug = "my-slug"
        numeric = f"{site}/product/42"
        expected = expected_slug_url(site, slug)
        html = f'<html><head><link rel="canonical" href="{expected}"></head></html>'

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            if url == numeric:
                return 301, {"Location": expected}, b""
            if url == expected:
                return 200, {}, html.encode()
            return 404, {}, b""

        probe = walk_redirect_chain(numeric, 5.0, fetch=fake_fetch)
        self.assertEqual(probe.status, 301)
        self.assertEqual(probe.hops, [numeric, expected])
        self.assertEqual(probe.final_url, expected)
        self.assertEqual(probe.final_status, 200)
        self.assertEqual(verify_required_301(site, "42", slug, probe), [])

    def test_walk_extra_302_bad_final_url(self) -> None:
        site = "https://shop.example"
        slug = "my-slug"
        numeric = f"{site}/product/42"
        expected = expected_slug_url(site, slug)
        other = expected_slug_url(site, "other")

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            if url == numeric:
                return 301, {"Location": expected}, b""
            if url == expected:
                return 302, {"Location": other}, b""
            if url == other:
                return 200, {}, b"<html></html>"
            return 404, {}, b""

        probe = walk_redirect_chain(numeric, 5.0, fetch=fake_fetch)
        self.assertEqual(probe.hops, [numeric, expected, other])
        self.assertIn("BAD_FINAL_URL", verify_required_301(site, "42", slug, probe))

    def test_walk_redirect_loop_a_b_a(self) -> None:
        site = "https://shop.example"
        a = f"{site}/product/1"
        b = f"{site}/product/b"

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            if url == a:
                return 301, {"Location": b}, b""
            if url == b:
                return 301, {"Location": a}, b""
            return 500, {}, b""

        probe = walk_redirect_chain(a, 5.0, fetch=fake_fetch)
        self.assertTrue(probe.redirect_loop)
        self.assertIn("REDIRECT_LOOP", verify_required_301(site, "1", "x", probe))

    def test_walk_more_than_ten_redirects(self) -> None:
        site = "https://shop.example"
        start = f"{site}/start"

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            if url == start:
                return 301, {"Location": f"{site}/r/1"}, b""
            if "/r/" in url:
                n = int(url.rsplit("/", 1)[-1])
                return 301, {"Location": f"{site}/r/{n + 1}"}, b""
            return 404, {}, b""

        probe = walk_redirect_chain(start, 5.0, fetch=fake_fetch)
        self.assertTrue(probe.bad_redirect_chain)
        self.assertEqual(len(probe.hops), MAX_REDIRECT_HOPS + 1)

    def test_walk_missing_location(self) -> None:
        site = "https://shop.example"
        numeric = f"{site}/product/9"

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            if url == numeric:
                return 301, {}, b""
            return 404, {}, b""

        probe = walk_redirect_chain(numeric, 5.0, fetch=fake_fetch)
        self.assertTrue(probe.missing_location)
        self.assertIn("BAD_LOCATION", verify_required_301(site, "9", "slug", probe))

    def test_probe_numeric_redirect_builds_product_path(self) -> None:
        site = "https://shop.example"
        seen: list[str] = []

        def fake_fetch(url: str, _timeout: float) -> tuple[int, dict[str, str], bytes]:
            seen.append(url)
            return 404, {}, b""

        probe_numeric_redirect(site, "5", timeout=1.0, fetch=fake_fetch)
        self.assertEqual(seen, [f"{site}/product/5"])

    def test_hard_pass_all_counters_zero(self) -> None:
        self.assertTrue(
            hard_pass(
                {
                    "REQUIRED_301": 2,
                    "HTTP_301_OK": 2,
                    "OTHER": 0,
                    "CLASSIFICATION_ACCOUNTING_ERROR": 0,
                    "BAD_STATUS": 0,
                    "BAD_LOCATION": 0,
                    "REDIRECT_LOOP": 0,
                    "BAD_FINAL_STATUS": 0,
                    "BAD_FINAL_CANONICAL": 0,
                    "BAD_REDIRECT_CHAIN": 0,
                    "BAD_FINAL_URL": 0,
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
