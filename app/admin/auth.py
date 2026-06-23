"""SQLAdmin session-based authentication restricted to super_admin users."""

from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from app.core.config import settings
from app.core.security import verify_password
from app.db.database import async_session_maker
from app.db.models.user import User, UserRole


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        phone_number = form.get("username")
        password = form.get("password")

        if not phone_number or not password:
            return False

        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.phone_number == str(phone_number))
            )
            user = result.scalars().first()

        if (
            not user
            or not user.is_active
            or user.role != UserRole.SUPER_ADMIN
            or not verify_password(str(password), user.hashed_password)
        ):
            return False

        request.session.update({"admin_user_id": user.id})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        user_id = request.session.get("admin_user_id")
        if not user_id:
            return False

        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()

        return bool(
            user
            and user.is_active
            and user.role == UserRole.SUPER_ADMIN
        )


admin_auth_backend = AdminAuth(secret_key=settings.SECRET_KEY)
