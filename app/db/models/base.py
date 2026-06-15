from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.0 Declarative models.
    All future models (e.g., Products, Categories) will inherit from this class.
    """
    pass