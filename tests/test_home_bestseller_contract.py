"""Owner curated products: schema and unauthenticated write rejection."""
import pytest
from pydantic import ValidationError

from app.api.endpoints.home_merchandising import (
    BestsellerSelectionWrite,
    MAX_ITEMS,
    as_response,
)

def test_payload_limits_and_positive_ids():
    assert BestsellerSelectionWrite(product_ids=[1, 2], expected_revision=0).product_ids == [1, 2]
    with pytest.raises(ValidationError):
        BestsellerSelectionWrite(product_ids=[1] * (MAX_ITEMS + 1), expected_revision=0)
    with pytest.raises(ValidationError):
        BestsellerSelectionWrite(product_ids=[0], expected_revision=0)
    with pytest.raises(ValidationError):
        BestsellerSelectionWrite(product_ids=[1], expected_revision=-1)

def test_missing_selection_is_explicitly_empty():
    missing = as_response(None)
    assert missing.product_ids == []
    assert missing.revision == 0
    assert missing.published_at is None
