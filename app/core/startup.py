"""One-time application bootstrap tasks executed at startup."""

from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.db.database import async_session_maker
from app.db.models.product import Brand, Category, Product, StockUnitEnum
from app.db.models.user import User, UserRole

logger = get_logger(__name__)

_DEV_SAMPLE_SKU = "DEV-CHECKOUT-001"


async def bootstrap_super_admin() -> None:
    """Create or promote the initial super admin when env credentials are set.

    Skips silently when credentials are absent or a super admin already exists.
    """
    if not settings.INITIAL_SUPER_ADMIN_PHONE or not settings.INITIAL_SUPER_ADMIN_PASSWORD:
        return

    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.role == UserRole.SUPER_ADMIN)
        )
        if result.scalars().first():
            return

        existing = await session.execute(
            select(User).where(User.phone_number == settings.INITIAL_SUPER_ADMIN_PHONE)
        )
        user = existing.scalars().first()
        if user:
            user.role = UserRole.SUPER_ADMIN
            user.is_active = True
            if settings.INITIAL_SUPER_ADMIN_PASSWORD:
                user.hashed_password = get_password_hash(settings.INITIAL_SUPER_ADMIN_PASSWORD)
            logger.info("Promoted existing user to super admin: %s", user.phone_number)
        else:
            user = User(
                phone_number=settings.INITIAL_SUPER_ADMIN_PHONE,
                hashed_password=get_password_hash(settings.INITIAL_SUPER_ADMIN_PASSWORD),
                full_name=settings.INITIAL_SUPER_ADMIN_NAME,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
            )
            session.add(user)
            logger.info("Created bootstrap super admin: %s", user.phone_number)

        await session.commit()


async def bootstrap_catalog_seed() -> None:
    """Seed minimal categories, brands, and a purchasable product for local E2E testing."""
    async with async_session_maker() as session:
        existing = await session.execute(select(Category).limit(1))
        if existing.scalars().first():
            return

        root = Category(name="ابزار تراشکاری")
        session.add(root)
        await session.flush()

        inserts = Category(name="الماس تراشکاری (اینسرت)", parent_id=root.id, spec_template_key="insert")
        session.add(inserts)
        await session.flush()

        leaf = Category(name="اینسرت CNGG", parent_id=inserts.id, spec_template_key="insert")
        session.add(leaf)
        await session.flush()

        brands = [
            Brand(name="سندویک کرومانت", country="سوئد"),
            Brand(name="ایسکار", country="اسرائیل"),
            Brand(name="میتوتویو", country="ژاپن"),
        ]
        session.add_all(brands)
        await session.flush()

        sample_product = Product(
            sku=_DEV_SAMPLE_SKU,
            name="اینسرت نمونه توسعه (DEV)",
            category_id=leaf.id,
            brand_id=brands[0].id,
            base_price=Decimal("250000.00"),
            stock_quantity=Decimal("100"),
            stock_unit=StockUnitEnum.PIECE,
            is_active=True,
            tax_percent=Decimal("9"),
            description="محصول نمونه برای تست checkout و پرداخت در محیط توسعه.",
            original_price=Decimal("300000.00"),
            specifications={
                "technical_specs": {"grade": "GC4325", "coating": "PVD"},
                "features": {"is_original": True},
                "dimensions": {"IC": "12.7"},
                "optional_accessories": [],
            },
        )
        session.add(sample_product)
        await session.commit()
        logger.info(
            "Seeded bootstrap catalog: categories + brands + sample product (%s)",
            _DEV_SAMPLE_SKU,
        )
