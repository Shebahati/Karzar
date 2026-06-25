"""Category spec-template registry and resolver for product entry forms."""

from typing import Any, Dict, List, Optional

from app.db.models.product import Category

FeatureDetailTemplate = Dict[str, Any]
FeatureTemplate = Dict[str, Any]
SpecTemplate = Dict[str, Any]

# ---------------------------------------------------------------------------
# Template definitions (returned to the admin panel as JSON)
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATE: SpecTemplate = {
    "technical_specs": {
        "suggested_keys": ["material", "standard", "grade", "coating"],
        "value_options": {
            "material": ["کارباید", "HSS", "HSS-Co", "سرامیک"],
            "standard": ["DIN", "ISO", "ANSI"],
            "grade": [],
            "coating": ["TiN", "TiAlN", "AlTiN", "CVD", "PVD"],
        },
    },
    "features": [
        {"key": "is_original", "label": "اورجینال", "type": "boolean"},
        {"key": "has_certification", "label": "دارای گواهی", "type": "boolean"},
    ],
    "dimensions": {"suggested_keys": ["L", "W", "H"]},
}

_MEASUREMENT_PRECISE_TEMPLATE: SpecTemplate = {
    "technical_specs": {
        "suggested_keys": [
            "range",
            "accuracy",
            "resolution",
            "material",
            "standard",
            "battery_type",
        ],
        "value_options": {
            "range": ["0-150mm", "0-200mm", "0-300mm", "0-600mm"],
            "accuracy": ["±0.02mm", "±0.03mm", "±0.01mm"],
            "resolution": ["0.01mm", "0.001mm", "0.0005\""],
            "material": ["فولاد ضدزنگ", "Stainless steel", "کربن"],
            "standard": ["DIN862", "ISO13385", "JIS"],
            "battery_type": ["CR2032", "SR44", "LR44"],
        },
    },
    "features": [
        {"key": "waterproof", "label": "ضدآب (IP)", "type": "boolean"},
        {"key": "data_output", "label": "خروجی داده", "type": "boolean"},
        {"key": "auto_power_off", "label": "خاموش شدن خودکار", "type": "boolean"},
        {
            "key": "has_buttons",
            "label": "دارای دکمه",
            "type": "boolean",
            "detail": {
                "key": "buttons_list",
                "label": "چه دکمه‌هایی دارد؟",
                "type": "string_array",
                "placeholder": "on/off",
            },
        },
        {
            "key": "has_certification",
            "label": "گواهی بازرسی",
            "type": "boolean",
            "detail": {
                "key": "certification_text",
                "label": "متن گواهی",
                "type": "string",
                "placeholder": "Supplied with manufacturer inspection certificate",
            },
        },
    ],
    "dimensions": {"suggested_keys": ["L", "a", "b", "c", "d"]},
}

_INSERT_TEMPLATE: SpecTemplate = {
    "technical_specs": {
        "suggested_keys": ["grade", "coating", "geometry", "insert_shape", "corner_radius_mm"],
        "value_options": {
            "grade": ["GC4325", "IC907", "TP2500", "YBC251"],
            "coating": ["CVD", "PVD", "TiAlN", "AlTiN"],
            "geometry": ["PM", "MM", "MF"],
            "insert_shape": ["C (80°)", "D (55°)", "V (35°)", "W (80°)"],
            "corner_radius_mm": ["0.4", "0.8", "1.2"],
        },
    },
    "features": [
        {"key": "coolant_through", "label": "آبسردکن داخلی", "type": "boolean"},
        {"key": "is_original", "label": "اورجینال", "type": "boolean"},
    ],
    "dimensions": {"suggested_keys": ["IC", "S", "r", "d"]},
}

_END_MILL_TEMPLATE: SpecTemplate = {
    "technical_specs": {
        "suggested_keys": ["diameter_mm", "flutes", "coating", "helix_angle", "length_of_cut_mm"],
        "value_options": {
            "diameter_mm": ["6", "8", "10", "12", "16", "20"],
            "flutes": ["2", "3", "4", "6"],
            "coating": ["AlTiN", "TiN", "DLC", "بدون روکش"],
            "helix_angle": ["30°", "35°", "45°", "50°"],
            "length_of_cut_mm": [],
        },
    },
    "features": [
        {"key": "coolant_through", "label": "آبسردکن داخلی", "type": "boolean"},
        {"key": "is_original", "label": "اورجینال", "type": "boolean"},
    ],
    "dimensions": {"suggested_keys": ["D", "L", "Lc", "d_shank"]},
}

_DRILL_TEMPLATE: SpecTemplate = {
    "technical_specs": {
        "suggested_keys": ["diameter_mm", "material", "standard", "point_angle", "flute_length_mm"],
        "value_options": {
            "diameter_mm": ["3", "5", "8", "10", "13", "16"],
            "material": ["HSS", "HSS-Co5", "کارباید", "کبالت"],
            "standard": ["DIN338", "DIN1897", "DIN340"],
            "point_angle": ["118°", "135°", "140°"],
            "flute_length_mm": [],
        },
    },
    "features": [
        {"key": "coolant_through", "label": "آبسردکن داخلی", "type": "boolean"},
        {"key": "is_original", "label": "اورجینال", "type": "boolean"},
    ],
    "dimensions": {"suggested_keys": ["D", "L", "Lc"]},
}

# Explicit overrides for high-traffic leaf categories (optional fine-tuning).
_CATEGORY_ID_OVERRIDES: Dict[int, SpecTemplate] = {
    57: _MEASUREMENT_PRECISE_TEMPLATE,  # انواع کولیس
    58: _MEASUREMENT_PRECISE_TEMPLATE,  # انواع میکرومتر
    33: _INSERT_TEMPLATE,
    34: _INSERT_TEMPLATE,
}

# Match when any ancestor id is in this set (root / branch level).
_BRANCH_TEMPLATE_BY_ANCESTOR: Dict[int, SpecTemplate] = {
    7: _MEASUREMENT_PRECISE_TEMPLATE,   # اندازه گیری
    3: _INSERT_TEMPLATE,                # اینسرت
    4: _END_MILL_TEMPLATE,              # ابزار انگشتی
    5: _DRILL_TEMPLATE,                 # مته
    2: _INSERT_TEMPLATE,                # ابزار اینسرتی (holders)
}


def resolve_spec_template(
    category: Category,
    categories_by_id: Dict[int, Category],
) -> SpecTemplate:
    """Pick the best template for a leaf category based on id override or ancestry."""
    if category.id in _CATEGORY_ID_OVERRIDES:
        return _deep_copy_template(_CATEGORY_ID_OVERRIDES[category.id])

    ancestor_ids = _collect_ancestor_ids(category, categories_by_id)
    for ancestor_id in reversed(ancestor_ids):
        if ancestor_id in _BRANCH_TEMPLATE_BY_ANCESTOR:
            return _deep_copy_template(_BRANCH_TEMPLATE_BY_ANCESTOR[ancestor_id])

    return _deep_copy_template(_DEFAULT_TEMPLATE)


def _collect_ancestor_ids(category: Category, by_id: Dict[int, Category]) -> List[int]:
    chain: List[int] = []
    current: Optional[Category] = category
    while current is not None:
        chain.append(current.id)
        current = by_id.get(current.parent_id) if current.parent_id is not None else None
    return list(reversed(chain))


def _deep_copy_template(template: SpecTemplate) -> SpecTemplate:
    """Return a shallow-safe copy so callers cannot mutate module constants."""
    import copy

    return copy.deepcopy(template)
