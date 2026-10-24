"""Order acquisition attribution resolver tests."""

from datetime import UTC, datetime, timedelta

from app.services.order_attribution import (
    AcquisitionCheckoutSnapshot,
    AcquisitionTouch,
    classify_visit,
    merge_client_state,
    resolve_order_snapshot,
)


def _touch(source: str, **kwargs) -> AcquisitionTouch:
    return AcquisitionTouch(
        source=source,
        method=kwargs.get("method", "utm"),
        landing_path="/",
        captured_at=kwargs.get("captured_at", datetime.now(UTC)),
        source_subtype=kwargs.get("source_subtype"),
        campaign=kwargs.get("campaign"),
    )


def test_torob_utm():
    t = classify_visit(landing_path="/p", referrer=None, utm_source="torob")
    assert t.source == "torob"


def test_emalls_referrer():
    t = classify_visit(landing_path="/", referrer="https://www.emalls.ir/x", utm_source=None)
    assert t.source == "emalls"


def test_google_paid():
    t = classify_visit(
        landing_path="/",
        referrer=None,
        utm_source="google",
        utm_medium="cpc",
    )
    assert t.source == "google"
    assert t.source_subtype == "google_paid"


def test_direct():
    t = classify_visit(landing_path="/", referrer=None, utm_source=None)
    assert t.source == "direct"


def test_merge_direct_return_preserves_first_touch():
    first = _touch("torob")
    state = merge_client_state(None, first)
    direct = classify_visit(landing_path="/", referrer=None, utm_source=None)
    state = merge_client_state(state, direct)
    assert state.first_touch is not None
    assert state.first_touch.source == "torob"
    assert state.last_non_direct_touch is not None
    assert state.last_non_direct_touch.source == "torob"


def test_resolve_uses_last_non_direct():
    now = datetime.now(UTC)
    payload = AcquisitionCheckoutSnapshot(
        first_touch=_touch("torob", captured_at=now),
        last_non_direct_touch=_touch("instagram", captured_at=now),
    )
    snap = resolve_order_snapshot(payload, now=now)
    assert snap.source == "instagram"
    assert snap.first_touch_source == "torob"


def test_expired_attribution_unknown():
    old = datetime.now(UTC) - timedelta(days=40)
    payload = AcquisitionCheckoutSnapshot(first_touch=_touch("torob", captured_at=old))
    snap = resolve_order_snapshot(payload)
    assert snap.source == "unknown"


def test_fake_google_host_not_classified_as_google():
    t = classify_visit(landing_path="/", referrer="https://fake-google.example/path", utm_source=None)
    assert t.source == "other"


def test_utm_emalls_wins_over_torob_referrer():
    t = classify_visit(
        landing_path="/",
        referrer="https://torob.com/product/1",
        utm_source="emalls",
    )
    assert t.source == "emalls"
    assert t.method == "utm"


def test_future_touch_rejected():
    future = datetime.now(UTC) + timedelta(days=1)
    payload = AcquisitionCheckoutSnapshot(first_touch=_touch("torob", captured_at=future))
    snap = resolve_order_snapshot(payload)
    assert snap.source == "unknown"
