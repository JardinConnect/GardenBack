from enum import Enum as PyEnum
from typing import Optional, List, TYPE_CHECKING
import uuid
from sqlalchemy import (
    String, DateTime, Float, ForeignKey, UUID, JSON, Boolean
) 
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from datetime import datetime, UTC

Base = declarative_base()

class RoleEnum(str, PyEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    EMPLOYEES = "employees"
    TRAINEE = "trainee"


# =========================================================
# USERS
# =========================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SqlEnum(RoleEnum), nullable=False, default=RoleEnum.EMPLOYEES)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    else:
        user = relationship("User", back_populates="refresh_tokens")


# =========================================================
# AREA - Structure hiérarchique pour organiser les zones
# =========================================================
class Area(Base):
    __tablename__ = "areas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    color: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False)


    # Auto-référence pour la hiérarchie
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=True)

    # Relations
    if TYPE_CHECKING:
        parent: Mapped[Optional["Area"]] = relationship("Area", remote_side=[id], back_populates="children")
        children: Mapped[List["Area"]] = relationship("Area", back_populates="parent")
        cells: Mapped[List["Cell"]] = relationship("Cell", back_populates="area")
    else:
        parent = relationship("Area", remote_side=[id], back_populates="children")
        children = relationship("Area", back_populates="parent")
        cells = relationship("Cell", back_populates="area")


# =========================================================
# CELL - Cellule contenant des capteurs
# =========================================================
class Cell(Base):
    __tablename__ = "cells"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relation vers l'area parent
    area_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=True)

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    sensor_type: Mapped[str] = mapped_column(String, nullable=False)  # 'temperature', 'humidity', etc.
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 'active', 'inactive', 'error'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relation vers la cellule
    cell_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cells.id"), nullable=False)

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
class AnalyticType(str, PyEnum):
    SOIL_TEMPERATURE = "soil_temperature"
    AIR_TEMPERATURE = "air_temperature"
    LIGHT = "light"
    SOIL_HUMIDITY = "soil_humidity"
    AIR_HUMIDITY = "air_humidity"
    DEEP_SOIL_HUMIDITY = "deep_soil_humidity"
    BATTERY = "battery"

    @classmethod
    def from_prefix(cls, prefix: str) -> "AnalyticType":
        prefix_map = {
            "TA": cls.AIR_TEMPERATURE,
            "TS": cls.SOIL_TEMPERATURE,
            "HA": cls.AIR_HUMIDITY,
            "HS": cls.SOIL_HUMIDITY,
            "DHS": cls.DEEP_SOIL_HUMIDITY,
            "L": cls.LIGHT,
            "B": cls.BATTERY,
        }
        try:
            return prefix_map[prefix.upper()]
        except KeyError:
            raise ValueError(f"Préfixe de capteur invalide: {prefix}")


class Analytic(Base):
    __tablename__ = "analytic"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    analytic_type: Mapped[AnalyticType] = mapped_column(SqlEnum(AnalyticType), nullable=False)
    sensor_code: Mapped[str] = mapped_column(String, nullable=False)

    # Relations - maintenant lié au sensor au lieu du node
    sensor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sensors.id"), index=True)
    
    if TYPE_CHECKING:
        sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="analytics")
    else:
        sensor = relationship("Sensor", back_populates="analytics")

# =========================================================
# FARM
# =========================================================
class Farm(Base):
    __tablename__ = 'farms'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
