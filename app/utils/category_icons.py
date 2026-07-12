"""Default react-iconly icon names for root category nodes in the mega menu."""

from typing import Optional

DEFAULT_ROOT_ICON = "Category"

# Keyword → icon name (react-iconly). Roots without a DB icon use this map.
_ROOT_ICON_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("برقی", "Activity"),
    ("اندازه", "Filter2"),
    ("تراش", "Setting"),
    ("فرز", "Work"),
    ("سوراخ", "Category"),
    ("ایمنی", "Category"),
    ("جوش", "Work"),
    ("بادی", "Activity"),
    ("باغبانی", "Category"),
)


def resolve_category_icon(category_name: str, stored_icon: Optional[str], *, is_root: bool) -> Optional[str]:
    """Return icon for tree nodes; only roots expose an icon per storefront contract."""
    if not is_root:
        return None
    if stored_icon:
        return stored_icon
    lowered = category_name.casefold()
    for keyword, icon in _ROOT_ICON_KEYWORDS:
        if keyword in lowered:
            return icon
    return DEFAULT_ROOT_ICON
