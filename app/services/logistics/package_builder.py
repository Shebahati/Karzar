"""Deterministic package construction — independent of Postex HTTP.

v1 algorithm (conservative rectangular union):

1. Each catalog unit is one packaged box (product package_length/width/height_cm).
2. Quantity N of the same SKU is N identical boxes.
3. Normalize each box by sorting edges descending: (d1 >= d2 >= d3).
4. Combined parcel:
   - length = max(d1)
   - width  = max(d2)
   - height = sum(d3)   (stack along the smallest axis)
5. Weight = sum(weight_grams × quantity), rounded up to whole grams.
6. Fit into the smallest official provider box that can contain the result
   after trying all axis permutations of the combined parcel.
7. If no official box fits, or any parcel SKU lacks weight/dimensions,
   do not fabricate numbers — the caller returns freight/incomplete.

This overestimates volume vs an optimal bin pack and is intentional for v1.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.logistics.exceptions import (
    ShippingDataIncompleteError,
    ShippingFreightRequiredError,
)
from app.services.logistics.models import BoxType, PackageSpec, QuoteLine, ShippingClass


def _ceil_positive(value: Decimal) -> int:
    quantized = value.to_integral_value(rounding="ROUND_CEILING")
    return int(quantized)


def _sorted_edges(length: int, width: int, height: int) -> tuple[int, int, int]:
    edges = sorted((length, width, height), reverse=True)
    return edges[0], edges[1], edges[2]


def _fits(parcel: tuple[int, int, int], box: tuple[int, int, int]) -> bool:
    p = sorted(parcel)
    b = sorted(box)
    return p[0] <= b[0] and p[1] <= b[1] and p[2] <= b[2]


def select_box(package: PackageSpec, boxes: list[BoxType]) -> PackageSpec:
    """Choose the smallest-volume official box that can contain *package*."""
    usable: list[tuple[int, BoxType, int]] = []
    for box in boxes:
        if box.length_cm is None or box.width_cm is None or box.height_cm is None:
            continue
        if box.length_cm <= 0 or box.width_cm <= 0 or box.height_cm <= 0:
            continue
        if _fits(
            (package.length_cm, package.width_cm, package.height_cm),
            (box.length_cm, box.width_cm, box.height_cm),
        ):
            volume = box.length_cm * box.width_cm * box.height_cm
            usable.append((volume, box, box.id))
    if not usable:
        raise ShippingFreightRequiredError(
            "محاسبه‌شده در ابعاد جعبه‌های رسمی پستکس جا نمی‌شود؛ ارسال باربری/استعلام لازم است."
        )
    usable.sort(key=lambda item: (item[0], item[2]))
    chosen = usable[0][1]
    return PackageSpec(
        length_cm=package.length_cm,
        width_cm=package.width_cm,
        height_cm=package.height_cm,
        weight_grams=package.weight_grams,
        is_fragile=package.is_fragile,
        is_liquid=package.is_liquid,
        box_type_id=chosen.id,
        box_name=chosen.name,
    )


def build_package(lines: list[QuoteLine], boxes: list[BoxType] | None = None) -> PackageSpec:
    if not lines:
        raise ValueError("at least one line is required to build a package")

    freight = [line for line in lines if line.shipping_class == ShippingClass.FREIGHT_ONLY.value]
    if freight:
        raise ShippingFreightRequiredError(
            "برخی اقلام فقط به‌صورت باربری/استعلام قابل ارسال هستند.",
        )

    incomplete: list[dict[str, object]] = []
    units: list[tuple[int, int, int]] = []
    total_weight = Decimal("0")
    any_fragile = False
    any_liquid = False

    for line in lines:
        missing: list[str] = []
        if line.weight_grams is None:
            missing.append("weight_grams")
        if line.length_cm is None:
            missing.append("package_length_cm")
        if line.width_cm is None:
            missing.append("package_width_cm")
        if line.height_cm is None:
            missing.append("package_height_cm")
        if missing:
            incomplete.append(
                {
                    "product_id": line.product_id,
                    "sku": line.sku,
                    "missing": missing,
                }
            )
            continue
        assert line.weight_grams is not None
        assert line.length_cm is not None
        assert line.width_cm is not None
        assert line.height_cm is not None
        if line.weight_grams < 0 or line.length_cm < 0 or line.width_cm < 0 or line.height_cm < 0:
            incomplete.append(
                {
                    "product_id": line.product_id,
                    "sku": line.sku,
                    "missing": ["negative_measurement"],
                }
            )
            continue
        length = _ceil_positive(line.length_cm)
        width = _ceil_positive(line.width_cm)
        height = _ceil_positive(line.height_cm)
        if length <= 0 or width <= 0 or height <= 0:
            incomplete.append(
                {
                    "product_id": line.product_id,
                    "sku": line.sku,
                    "missing": ["zero_dimension"],
                }
            )
            continue
        d1, d2, d3 = _sorted_edges(length, width, height)
        for _ in range(line.quantity):
            units.append((d1, d2, d3))
        total_weight += line.weight_grams * line.quantity
        any_fragile = any_fragile or line.is_fragile
        any_liquid = any_liquid or line.is_liquid

    if incomplete:
        raise ShippingDataIncompleteError(
            "اطلاعات بسته‌بندی برخی محصولات ناقص است.",
            products=incomplete,
        )

    length = max(u[0] for u in units)
    width = max(u[1] for u in units)
    height = sum(u[2] for u in units)
    weight = _ceil_positive(total_weight)
    if weight <= 0:
        raise ShippingDataIncompleteError(
            "وزن مرسوله باید بزرگ‌تر از صفر باشد.",
            products=[
                {"product_id": line.product_id, "sku": line.sku, "missing": ["weight_grams"]}
                for line in lines
            ],
        )

    spec = PackageSpec(
        length_cm=length,
        width_cm=width,
        height_cm=height,
        weight_grams=weight,
        is_fragile=any_fragile,
        is_liquid=any_liquid,
    )
    if boxes is None:
        return spec
    return select_box(spec, boxes)
