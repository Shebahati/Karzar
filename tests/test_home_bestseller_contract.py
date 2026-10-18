"""Owner-curated bestseller request validation and missing publication behavior."""

from app.api.endpoints import home_merchandising


def test_payload_limits_and_positive_ids():
    request = home_merchandising.BestsellerSelectionWrite
    assert request(product_ids=[1, 2], expected_revision=0).product_ids == [1, 2]
    invalid = [
        {"product_ids": [1] * (home_merchandising.MAX_ITEMS + 1), "expected_revision": 0},
        {"product_ids": [0], "expected_revision": 0},
        {"product_ids": [1], "expected_revision": -1},
    ]
    for payload in invalid:
        try:
            request(**payload)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid bestseller publication payload was accepted")


def test_missing_selection_is_explicitly_empty():
    missing = home_merchandising.as_response(None)
    assert missing.product_ids == []
    assert missing.revision == 0
    assert missing.published_at is None
