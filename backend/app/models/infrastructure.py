"""Roads, villages, bridges, hospitals, schools - everything that has exposure."""
from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class InfrastructureType(str, enum.Enum):
    ROAD = "ROAD"
    BRIDGE = "BRIDGE"
    VILLAGE = "VILLAGE"
    TOWN = "TOWN"
    HOSPITAL = "HOSPITAL"
    SCHOOL = "SCHOOL"
    POWER_LINE = "POWER_LINE"
    OTHER = "OTHER"


class Infrastructure(Base, TimestampMixin):
    __tablename__ = "infrastructure"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[InfrastructureType] = mapped_column(
        Enum(InfrastructureType, native_enum=False, length=24),
        nullable=False,
        index=True,
    )
    importance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
