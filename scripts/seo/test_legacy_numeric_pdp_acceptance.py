"""Unit tests for legacy_numeric_pdp_acceptance classification and verification."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SEO_DIR = Path(__file__).resolve().parent
if str(SEO_DIR) not in sys.path:
    sys.path.insert(0, str(SEO_DIR))

from legacy_numeric_pdp_acceptance import (  # noqa: E402
    ApiProduct,
    RedirectProbe,
    classify_api,
    expected_slug_url,
    hard_pass,
    verify_required_301,
)


class LegacyNumericPdpAcceptanceTests(unittest.TestCase):
    def test_classify_api(self) -> None:
        self.assertEqual(classify_api("1", ApiProduct(404, None)), "HISTORICAL_NOT_FOUND")
        self.assertEqual(classify_api("1", ApiProduct(200, "")), "NO_SLUG")
        self.assertEqual(classify_api("99", ApiProduct(200, "99")), "NUMERIC_CANONICAL")
        self.assertEqual(classify_api("1", ApiProduct(200, "real-slug")), "REQUIRED_301")
        self.assertEqual(classify_api("1", ApiProduct(500, None)), "OTHER")

    def test_expected_slug_url_encodes_once(self) -> None:
        import urllib.parse

        url = expected_slug_url("https://www.karzartools.com", "مدل-تست")
        self.assertIn(urllib.parse.quote("مدل-تست", safe=""), url)

    def test_verify_required_301_ok(self) -> None:
        site = "https://www.karzartools.com"
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
        site = "https://www.karzartools.com"
        probe = RedirectProbe(status=308, location="", final_status=200)
        self.assertIn("BAD_STATUS", verify_required_301(site, "1", "x", probe))

    def test_verify_redirect_loop(self) -> None:
        site = "https://www.karzartools.com"
        a = f"{site}/product/1"
        probe = RedirectProbe(status=301, location=a, hops=[a, a], final_status=200, canonical=a)
        self.assertIn("REDIRECT_LOOP", verify_required_301(site, "1", "x", probe))

    def test_hard_pass(self) -> None:
        self.assertTrue(
            hard_pass(
                {
                    "REQUIRED_301": 2,
                    "HTTP_301_OK": 2,
                    "BAD_STATUS": 0,
                    "BAD_LOCATION": 0,
                    "REDIRECT_LOOP": 0,
                    "BAD_FINAL_STATUS": 0,
                    "BAD_FINAL_CANONICAL": 0,
                    "BAD_REDIRECT_CHAIN": 0,
                }
            )
        )
        self.assertFalse(hard_pass({"REQUIRED_301": 2, "HTTP_301_OK": 1, "BAD_STATUS": 1}))


if __name__ == "__main__":
    unittest.main()
