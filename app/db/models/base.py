# app/db/models/base.py
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.0 Declarative models.
    """
    
    # استفاده از server_default برای واگذاری محاسبه زمان به خودِ دیتابیس
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    # onupdate=func.now() باعث می‌شود هر بار ردیفی آپدیت شد، Postgres خودش زمان را رفرش کند
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )