"""Unit tests for nav-groups seed matcher resolution."""

from app.services.nav_groups_seed import (
    DEFAULT_NAV_GROUP_SEEDS,
    resolve_root_ids_for_matchers,
)


def test_seed_resolves_metrology_and_cutting_without_overlap():
    roots = [
        (56, "اندازه گیری دقیق", "andaze-giri-daghigh-56"),
        (81, "CNC اندازه گیری", "cnc-andaze-giri-81"),
        (87, "اندازه گیری آزمایشگاهی", "andaze-giri-azmayeshgahi-87"),
        (3, "اینسرت", "insert-3"),
        (5, "مته", "mete-5"),
        (1, "ابزارگیر", "abzargir-1"),
        (9, "دستگاه‌های صنعتی", "machines-9"),
        (11, "لوازم جانبی صنعتی", "accessories-11"),
    ]
    assigned: set[int] = set()
    resolved: dict[str, list[int]] = {}
    for seed in DEFAULT_NAV_GROUP_SEEDS:
        resolved[seed["slug"]] = resolve_root_ids_for_matchers(
            roots,
            list(seed["matchers"]),
            assigned=assigned,
        )

    assert resolved["metrology"] == [56, 81, 87]
    assert resolved["cutting"] == [3, 5]
    assert resolved["holding"] == [1]
    assert resolved["machines"] == [9]
    assert resolved["accessories"] == [11]
    assert len(assigned) == 8
