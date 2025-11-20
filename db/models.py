from enum import Enum
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


# =========================================================
# USER
# =========================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    isAdmin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    user_spaces = relationship("UserSpace", back_populates="user")


# =========================================================
# SPACE
# =========================================================
class Space(Base):
    __tablename__ = "spaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    type = Column(String)
    location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation récursive : un espace peut contenir d'autres espaces
    parent_id = Column(Integer, ForeignKey("spaces.id"), nullable=True)
    parent = relationship("Space", remote_side=[id], backref="children")

    # Relations
    users = relationship("UserSpace", back_populates="space")
    nodes = relationship("Node", back_populates="space")


# =========================================================
# USERSPACE
# =========================================================
class UserSpace(Base):
    __tablename__ = "user_spaces"

    id = Column(Integer, primary_key=True, index=True)
    permissions = Column(String)

    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    space_id = Column(Integer, ForeignKey("spaces.id"), index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), index=True)

    # Relations
    user = relationship("User", back_populates="user_spaces")
    space = relationship("Space", back_populates="users")
    role = relationship("Role", back_populates="user_spaces")


# =========================================================
# ROLE
# =========================================================
class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user_spaces = relationship("UserSpace", back_populates="role")


# =========================================================
# NODE
# =========================================================
class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, nullable=False)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)
    RSSI = Column(Integer)

    # Relations
    space_id = Column(Integer, ForeignKey("spaces.id"), index=True)
    space = relationship("Space", back_populates="nodes")

    # Un node contient des relevés analytiques
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

    @classmethod
    def from_prefix(cls, prefix: str) -> "AnalyticType":
        """
        Convertit un préfixe de capteur en type d'analytique.
        Exemple: 'AT' -> AnalyticType.AIR_TEMPERATURE
        """
        prefix_map = {
            "AT": cls.AIR_TEMPERATURE,
            "AH": cls.AIR_HUMIDITY,
            "SH": cls.SOIL_HUMIDITY,
            "LI": cls.LIGHT,
        }
        try:
            return prefix_map[prefix.upper()]
        except KeyError:
            raise ValueError

class Analytic(Base):
    __tablename__ = "analytic"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    value = Column(Float, nullable=False)
    occured_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    analytic_type = Column(SqlEnum(AnalyticType), nullable=False)
    sensor_code = Column(String, nullable=False)

    # Relations
    node_id = Column(Integer, ForeignKey("nodes.id"), index=True)
    node = relationship("Node", back_populates="analytics")


# =========================================================
# ALERTS
# =========================================================
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    condition = Column(String, nullable=False)  # Ex: ">", "<", "=="
    threshold = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sensor_code = Column(String, nullable=False)

    # Relations
    node_id = Column(Integer, ForeignKey("nodes.id"), index=True)
    node = relationship("Node", back_populates="alerts")
    history = relationship("AlertHistory", back_populates="alert")


# =========================================================
# ALERT HISTORY
# =========================================================
class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    triggered_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)
    message = Column(Text)

    # Relations
    alert_id = Column(Integer, ForeignKey("alerts.id"), index=True)
    alert = relationship("Alert", back_populates="history")


# =========================================================
# REFRESH TOKENS
# =========================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    user = relationship("User", back_populates="refresh_tokens")
