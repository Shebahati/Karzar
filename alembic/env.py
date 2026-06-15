# alembic/env.py
# alembic/env.py
import sys
import os

# اضافه کردن مسیر فعلی به مسیرهای پایتون
sys.path.append(os.getcwd())

# ... حالا بقیه ایمپورت‌ها ...
from app.core.config import settings
# ...

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.core.config import settings
from app.db.models import Base  # این همان فایلی است که Base در آن است

config = context.config
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URI)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# بقیه کد دقیقا همان ساختار استاندارد async است که در مرحله قبل دیدیم
# ... (کدهای run_migrations_offline و run_async_migrations را از پیام قبلی کپی کنید)