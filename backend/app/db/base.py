"""SQLAlchemy declarative base + naming conventions for Alembic."""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention makes Alembic autogenerate produce stable constraint names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        cls = type(self).__name__
        keys = [c.name for c in self.__table__.primary_key.columns]
        parts = ", ".join(f"{k}={getattr(self, k, None)!r}" for k in keys)
        return f"<{cls} {parts}>"
