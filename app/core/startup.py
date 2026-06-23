"""One-time application bootstrap tasks executed at startup."""

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.db.database import async_session_maker
from app.db.models.user import User, UserRole

logger = get_logger(__name__)


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
