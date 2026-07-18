"""Category utilities package — re-exports from existing category_*.py modules."""

from app.utils.category_counts import (  # noqa: F401
    compute_subtree_product_counts,
    get_category_product_counts,
    get_direct_product_counts,
)
from app.utils.category_depth import (  # noqa: F401
    MAX_CATEGORY_DEPTH,
    CategoryMeta,
    build_category_metadata,
    is_selectable_product_category,
)
from app.utils.category_icons import (  # noqa: F401
    DEFAULT_ROOT_ICON,
    resolve_category_icon,
)
from app.utils.category_tree import build_category_tree  # noqa: F401
from app.utils.category_validation import (  # noqa: F401
    ensure_brand_exists,
    ensure_selectable_product_category,
)
