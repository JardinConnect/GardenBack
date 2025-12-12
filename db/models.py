from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Integer, String, DateTime, Boolean, Float, ForeignKey
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, UTC

Base = declarative_base()


# =========================================================
# USERS
# =========================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    isAdmin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    if TYPE_CHECKING:
        refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user")
    else:
        refresh_tokens = relationship("RefreshToken", back_populates="user")


# =========================================================
# REFRESH TOKENS
# =========================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    else:
        user = relationship("User", back_populates="refresh_tokens")


# =========================================================
# AREA - Structure hiérarchique pour organiser les zones
# =========================================================
class Area(Base):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    color: Mapped[Optional[str]] = mapped_column(String)
    level: Mapped[int] = mapped_column(Integer, default=1)  # Niveau de profondeur
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Auto-référence pour la hiérarchie
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("areas.id"), nullable=True)

    # Relations
    if TYPE_CHECKING:
        parent: Mapped[Optional["Area"]] = relationship("Area", remote_side=[id], back_populates="children")
        children: Mapped[List["Area"]] = relationship("Area", back_populates="parent")
        cells: Mapped[List["Cell"]] = relationship("Cell", back_populates="area", cascade="all, delete-orphan")
    else:
        parent = relationship("Area", remote_side=[id], back_populates="children")
        children = relationship("Area", back_populates="parent")
        cells = relationship("Cell", back_populates="area", cascade="all, delete-orphan")


# =========================================================
# CELL - Cellule contenant des capteurs
# =========================================================
class Cell(Base):
    __tablename__ = "cells"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relation vers l'area parent
    area_id: Mapped[int] = mapped_column(Integer, ForeignKey("areas.id"), nullable=False)

    # Relations
    if TYPE_CHECKING:
        area: Mapped["Area"] = relationship("Area", back_populates="cells")
        sensors: Mapped[List["Sensor"]] = relationship("Sensor", back_populates="cell", cascade="all, delete-orphan")
    else:
        area = relationship("Area", back_populates="cells")
        sensors = relationship("Sensor", back_populates="cell", cascade="all, delete-orphan")


# =========================================================
# SENSOR - Capteur physique qui génère des analytics
# =========================================================
class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sensor_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    sensor_type: Mapped[str] = mapped_column(String, nullable=False)  # 'temperature', 'humidity', etc.
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 'active', 'inactive', 'error'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relation vers la cellule
    cell_id: Mapped[int] = mapped_column(Integer, ForeignKey("cells.id"), nullable=False)

    # Relations
    if TYPE_CHECKING:
        cell: Mapped["Cell"] = relationship("Cell", back_populates="sensors")
        analytics: Mapped[List["Analytic"]] = relationship("Analytic", back_populates="sensor")
    else:
        cell = relationship("Cell", back_populates="sensors")
        analytics = relationship("Analytic", back_populates="sensor")


# =========================================================
# ANALYTICS
# =========================================================
class AnalyticType(str, Enum):
    SOIL_TEMPERATURE = "SOIL_TEMPERATURE"
    AIR_TEMPERATURE = "AIR_TEMPERATURE"
    LIGHT = "LIGHT"
    SOIL_HUMIDITY = "SOIL_HUMIDITY"
    AIR_HUMIDITY = "AIR_HUMIDITY"
    BATTERY = "BATTERY"

    @classmethod
    def from_prefix(cls, prefix: str) -> "AnalyticType":
        prefix_map = {
            "TA": cls.AIR_TEMPERATURE,
            "TS": cls.SOIL_TEMPERATURE,
            "HA": cls.AIR_HUMIDITY,
            "HS": cls.SOIL_HUMIDITY,
            "L": cls.LIGHT,
            "B": cls.BATTERY,
        }
        try:
            return prefix_map[prefix.upper()]
        except KeyError:
            raise ValueError(f"Préfixe de capteur invalide: {prefix}")


class Analytic(Base):
    __tablename__ = "analytic"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    occured_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    analytic_type: Mapped[AnalyticType] = mapped_column(SqlEnum(AnalyticType), nullable=False)
    sensor_code: Mapped[str] = mapped_column(String, nullable=False)

    # Relations - maintenant lié au sensor au lieu du node
    sensor_id: Mapped[int] = mapped_column(Integer, ForeignKey("sensors.id"), index=True)
    
    if TYPE_CHECKING:
        sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="analytics")
    else:
        sensor = relationship("Sensor", back_populates="analytics")