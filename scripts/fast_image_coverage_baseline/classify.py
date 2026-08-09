"""Six-state classification for storefront primary-image coverage."""

from __future__ import annotations

from .contracts import (
    AssetValidation,
    DetailImage,
    ProductClassification,
    ProductListItem,
)
from .placeholders import mark_placeholder


def discovery_lane_hint(state: str) -> str | None:
    if state == "missing_all_images":
        return "iranian_retailer_exact"
    if state == "broken_only":
        return "official_manufacturer"
    if state == "known_placeholder_only":
        return "distributor_catalog"
    if state == "ambiguous_current_state":
        return "manual_hold"
    if state == "promotable_existing_image":
        return None
    return None


def _usable(v: AssetValidation | None) -> bool:
    return bool(
        v
        and v.decode_ok
        and not v.is_known_placeholder
        and not mark_placeholder(v.url, v.sha256)
    )


def _placeholder_only(v: AssetValidation | None) -> bool:
    return bool(v and v.decode_ok and (v.is_known_placeholder or mark_placeholder(v.url, v.sha256)))


def select_best_reusable(
    images: list[DetailImage],
    validations: dict[str, AssetValidation],
    *,
    exclude_urls: set[str],
) -> tuple[DetailImage, AssetValidation] | None:
    """Deterministic: first presenter-ordered image that validates as usable."""
    for img in images:
        if img.url in exclude_urls:
            continue
        v = validations.get(img.url)
        if _usable(v):
            assert v is not None
            return img, v
    return None


def classify_product(
    item: ProductListItem,
    *,
    thumb_validation: AssetValidation | None,
    detail_images: list[DetailImage] | None,
    image_validations: dict[str, AssetValidation],
    detail_fetched: bool,
) -> ProductClassification:
    """Apply mutually exclusive six-state taxonomy."""
    thumb = (item.thumbnail or "").strip() or None
    primary_present = bool(thumb)

    base_kwargs = dict(
        product_id=item.product_id,
        sku=item.sku,
        slug=item.slug,
        name=item.name,
        brand_key=item.brand_key,
        brand_id=item.brand_id,
        category_id=item.category_id,
        category_slug=item.category_slug,
        category_name=item.category_name,
        primary_image_present=primary_present,
        primary_image_reference=thumb,
        primary_decode_ok=thumb_validation.decode_ok if thumb_validation else None,
        primary_width=thumb_validation.width if thumb_validation else None,
        primary_height=thumb_validation.height if thumb_validation else None,
        primary_sha256=thumb_validation.sha256 if thumb_validation else None,
        primary_http_status=thumb_validation.http_status if thumb_validation else None,
        detail_fetched=detail_fetched,
        images_count=len(detail_images or []),
        priority_tier="unassigned",
        priority_basis="none",
    )

    # A: usable current thumbnail
    if primary_present and _usable(thumb_validation):
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="usable_primary",
            placeholder_flag=False,
            broken_flag=False,
            fast_coverage_needed=False,
            reason_code="thumbnail_usable",
            notes="storefront thumbnail fetches and decodes",
            suggested_discovery_lane=None,
        )

    # Thumbnail is known placeholder only — still inspect detail for other assets
    thumb_is_placeholder = primary_present and _placeholder_only(thumb_validation)
    thumb_broken = primary_present and not _usable(thumb_validation) and not thumb_is_placeholder

    images = detail_images if detail_images is not None else []
    # If we needed detail but do not have it, ambiguous
    need_detail = (not primary_present) or thumb_broken or thumb_is_placeholder
    if need_detail and not detail_fetched:
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="ambiguous_current_state",
            placeholder_flag=bool(thumb_is_placeholder),
            broken_flag=bool(thumb_broken),
            fast_coverage_needed=True,
            reason_code="detail_required_unavailable",
            notes="detail fetch required but unavailable",
            suggested_discovery_lane=discovery_lane_hint("ambiguous_current_state"),
        )

    exclude = {thumb} if thumb else set()
    reusable = select_best_reusable(images, image_validations, exclude_urls=exclude)

    # Also allow reusable to be a usable image even if same URL excluded failed? No.

    # If thumbnail missing/broken but another image works → promotable
    if reusable is not None:
        img, val = reusable
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="promotable_existing_image",
            placeholder_flag=False,
            broken_flag=False,
            fast_coverage_needed=True,
            reason_code="secondary_image_reusable",
            notes="current thumbnail unusable/missing; existing image reusable",
            reusable_image_id=img.image_id,
            reusable_image_url=img.url,
            reusable_is_primary=img.is_primary,
            reusable_display_order=img.display_order,
            reusable_decode_ok=val.decode_ok,
            reusable_width=val.width,
            reusable_height=val.height,
            reusable_sha256=val.sha256,
            reusable_selection_reason="first_presenter_ordered_usable_nonprimary_candidate",
            suggested_discovery_lane=None,
        )

    # Collect validation outcomes for all referenced images (thumb + detail)
    refs: list[str] = []
    if thumb:
        refs.append(thumb)
    for img in images:
        if img.url not in refs:
            refs.append(img.url)

    if not refs:
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="missing_all_images",
            placeholder_flag=False,
            broken_flag=False,
            fast_coverage_needed=True,
            reason_code="no_image_references",
            notes="thumbnail absent and detail images[] empty",
            suggested_discovery_lane=discovery_lane_hint("missing_all_images"),
        )

    vals = [image_validations.get(u) or (thumb_validation if u == thumb else None) for u in refs]
    # Fill thumb into map conceptually
    if thumb and thumb_validation is not None:
        image_validations.setdefault(thumb, thumb_validation)
        vals = [image_validations.get(u) for u in refs]

    any_transient = any(v and v.transient_exhausted and not v.decode_ok for v in vals if v)
    any_decode = any(v and v.decode_ok for v in vals if v)
    all_placeholder = bool(vals) and all(
        v is not None and v.decode_ok and (v.is_known_placeholder or mark_placeholder(v.url, v.sha256))
        for v in vals
    )
    any_failed_tech = any(
        v is not None and not v.decode_ok for v in vals if v is not None
    ) or any(v is None for v in vals)

    if all_placeholder:
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="known_placeholder_only",
            placeholder_flag=True,
            broken_flag=False,
            fast_coverage_needed=True,
            reason_code="all_usable_assets_are_known_placeholders",
            notes="every decodable asset matches known placeholder signature",
            suggested_discovery_lane=discovery_lane_hint("known_placeholder_only"),
        )

    if any_decode and not all_placeholder:
        # Decodable non-placeholder existed but select_best_reusable missed — ambiguous
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="ambiguous_current_state",
            placeholder_flag=False,
            broken_flag=False,
            fast_coverage_needed=True,
            reason_code="decode_ok_but_not_selected",
            notes="decodable asset present but could not assign A/B safely",
            suggested_discovery_lane=discovery_lane_hint("ambiguous_current_state"),
        )

    if any_transient and not any_failed_tech:
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="ambiguous_current_state",
            placeholder_flag=False,
            broken_flag=False,
            fast_coverage_needed=True,
            reason_code="transient_network_exhausted",
            notes="retries exhausted on transient HTTP failures",
            suggested_discovery_lane=discovery_lane_hint("ambiguous_current_state"),
        )

    if any_failed_tech or (refs and not any_decode):
        return ProductClassification(
            **base_kwargs,  # type: ignore[arg-type]
            image_state="broken_only",
            placeholder_flag=False,
            broken_flag=True,
            fast_coverage_needed=True,
            reason_code="all_references_unusable",
            notes="image references exist but none fetch/decode successfully",
            suggested_discovery_lane=discovery_lane_hint("broken_only"),
        )

    return ProductClassification(
        **base_kwargs,  # type: ignore[arg-type]
        image_state="ambiguous_current_state",
        placeholder_flag=False,
        broken_flag=False,
        fast_coverage_needed=True,
        reason_code="unclassified",
        notes="deterministic rules could not place product into A–E",
        suggested_discovery_lane=discovery_lane_hint("ambiguous_current_state"),
    )


def reconcile_states(classifications: list[ProductClassification]) -> dict[str, int]:
    counts = {s: 0 for s in (
        "usable_primary",
        "promotable_existing_image",
        "missing_all_images",
        "broken_only",
        "known_placeholder_only",
        "ambiguous_current_state",
    )}
    seen: set[int] = set()
    dup = 0
    for c in classifications:
        if c.product_id in seen:
            dup += 1
        seen.add(c.product_id)
        counts[c.image_state] = counts.get(c.image_state, 0) + 1
    counts["duplicate_product_ids_across_states"] = dup
    return counts
