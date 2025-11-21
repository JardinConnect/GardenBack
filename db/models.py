from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Integer, String, DateTime, Text, Boolean, Float, ForeignKey
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

from datetime import datetime, UTC

Base = declarative_base()


# =========================================================
# USER
# =========================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    isAdmin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relations
    if TYPE_CHECKING:
        refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user")
        user_spaces: Mapped[List["UserSpace"]] = relationship("UserSpace", back_populates="user")
    else:
        refresh_tokens = relationship("RefreshToken", back_populates="user")
        user_spaces = relationship("UserSpace", back_populates="user")


# =========================================================
# SPACE
# =========================================================
class Space(Base):
    __tablename__ = "spaces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relation récursive : un espace peut contenir d'autres espaces
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("spaces.id"), nullable=True)

    # Relations
    if TYPE_CHECKING:
        parent: Mapped[Optional["Space"]] = relationship("Space", remote_side=[id], backref="children")
        users: Mapped[List["UserSpace"]] = relationship("UserSpace", back_populates="space")
        nodes: Mapped[List["Node"]] = relationship("Node", back_populates="space")
    else:
        parent = relationship("Space", remote_side=[id], backref="children")
        users = relationship("UserSpace", back_populates="space")
        nodes = relationship("Node", back_populates="space")


# =========================================================
# USERSPACE
# =========================================================
class UserSpace(Base):
    __tablename__ = "user_spaces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    permissions: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    space_id: Mapped[int] = mapped_column(Integer, ForeignKey("spaces.id"), index=True)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), index=True)

    # Relations
    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User", back_populates="user_spaces")
        space: Mapped["Space"] = relationship("Space", back_populates="users")
        role: Mapped["Role"] = relationship("Role", back_populates="user_spaces")
    else:
        user = relationship("User", back_populates="user_spaces")
        space = relationship("Space", back_populates="users")
        role = relationship("Role", back_populates="user_spaces")


# =========================================================
# ROLE
# =========================================================
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relations
    if TYPE_CHECKING:
        user_spaces: Mapped[List["UserSpace"]] = relationship("UserSpace", back_populates="role")
    else:
        user_spaces = relationship("UserSpace", back_populates="role")


# =========================================================
# NODE
# =========================================================
class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uid: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    RSSI: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relations
    space_id: Mapped[int] = mapped_column(Integer, ForeignKey("spaces.id"), index=True)

    # Un node contient des relevés analytiques
    if TYPE_CHECKING:
        space: Mapped["Space"] = relationship("Space", back_populates="nodes")
        analytics: Mapped[List["Analytic"]] = relationship("Analytic", back_populates="node")
        alerts: Mapped[List["Alert"]] = relationship("Alert", back_populates="node")
    else:
        space = relationship("Space", back_populates="nodes")
        analytics = relationship("Analytic", back_populates="node")
        alerts = relationship("Alert", back_populates="node")


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
        """
        Convertit un préfixe de capteur en type d'analytique.
        Exemple: 'TA' -> AnalyticType.AIR_TEMPERATURE
        """
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

    # Relations
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("nodes.id"), index=True)
    if TYPE_CHECKING:
        node: Mapped["Node"] = relationship("Node", back_populates="analytics")
    else:
        node = relationship("Node", back_populates="analytics")


# =========================================================
# ALERTS
# =========================================================
class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    condition: Mapped[str] = mapped_column(String, nullable=False)  # Ex: ">", "<", "=="
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    sensor_code: Mapped[str] = mapped_column(String, nullable=False)

    # Relations
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("nodes.id"), index=True)
    if TYPE_CHECKING:
        node: Mapped["Node"] = relationship("Node", back_populates="alerts")
        history: Mapped[List["AlertHistory"]] = relationship("AlertHistory", back_populates="alert")
    else:
        node = relationship("Node", back_populates="alerts")
        history = relationship("AlertHistory", back_populates="alert")


# =========================================================
# ALERT HISTORY
# =========================================================
class AlertHistory(Base):
    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id"), index=True)
    if TYPE_CHECKING:
        alert: Mapped["Alert"] = relationship("Alert", back_populates="history")
    else:
        alert = relationship("Alert", back_populates="history")


# =========================================================
# REFRESH TOKENS
# =========================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Relations
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    if TYPE_CHECKING:
        user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    else:
        user = relationship("User", back_populates="refresh_tokens")
