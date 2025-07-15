from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    user_spaces = relationship("UserSpace", back_populates="user")

class Space(Base):
    """
    Modèle pour la table 'spaces'.
    Représente un espace ou un lieu.
    """
    __tablename__ = 'spaces'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    type = Column(String)
    location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relation récursive : Un espace peut contenir d'autres espaces (enfants)
    parent_id = Column(Integer, ForeignKey('spaces.id'), nullable=True)
    parent = relationship("Space", remote_side=[id], backref="children")

    # Relations
    users = relationship("UserSpace", back_populates="space")
    arduino_nodes = relationship("ArduinoNode", back_populates="space")

class UserSpace(Base):
    """
    Modèle pour la table d'association 'user_spaces'.
    Gère la relation N:M entre les utilisateurs et les espaces.
    """
    __tablename__ = 'user_spaces'

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String)
    permissions = Column(String)

    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    space_id = Column(Integer, ForeignKey('spaces.id'), index=True)

    # Relations
    user = relationship("User", back_populates="user_spaces")
    space = relationship("Space", back_populates="users")

class ArduinoNode(Base):
    """
    Modèle pour la table 'arduino_nodes'.
    Représente un nœud Arduino physique.
    """
    __tablename__ = 'arduino_nodes'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    firmware_version = Column(String)
    location = Column(String)
    api_key = Column(String, unique=True, nullable=False, index=True) 
    status = Column(String)   
    last_connection = Column(DateTime)
    battery_level = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    space_id = Column(Integer, ForeignKey('spaces.id'), index=True)
    space = relationship("Space", back_populates="arduino_nodes")
    sensors = relationship("Sensor", back_populates="arduino_node")

class Sensor(Base):
    """
    Modèle pour la table 'sensors'.
    Représente un capteur individuel.
    """
    __tablename__ = 'sensors'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String)
    model = Column(String) 
    position_on_node = Column(String) 
    is_active = Column(Boolean, default=True)
    min_value = Column(Float) 
    max_value = Column(Float) 
    calibration_offset = Column(Float) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    arduino_node_id = Column(Integer, ForeignKey('arduino_nodes.id'), index=True)
    arduino_node = relationship("ArduinoNode", back_populates="sensors")
    data_readings = relationship("SensorData", back_populates="sensor") 
    alerts = relationship("Alert", back_populates="sensor")

class SensorData(Base):
    """
    Modèle pour la table 'sensor_data'.
    Stocke les relevés de données des capteurs.
    """
    __tablename__ = 'sensor_data'

    id = Column(Integer, primary_key=True, index=True)
    value = Column(Float, nullable=False) 
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False) 
    unit_of_measure = Column(String) 

    # Relations
    sensor_id = Column(Integer, ForeignKey('sensors.id'), index=True)
    sensor = relationship("Sensor", back_populates="data_readings")

class Alert(Base):
    """
    Modèle pour la table 'alerts'.
    Définit les conditions d'alerte pour les capteurs.
    """
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    condition = Column(String, nullable=False) # Ex: ">", "<", "=="
    threshold = Column(Float, nullable=False) 
    is_active = Column(Boolean, default=True) 
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    sensor_id = Column(Integer, ForeignKey('sensors.id'), index=True)
    sensor = relationship("Sensor", back_populates="alerts")
    history = relationship("AlertHistory", back_populates="alert") 

class AlertHistory(Base):
    """
    Modèle pour la table 'alert_history'.
    Enregistre l'historique des déclenchements d'alertes.
    """
    __tablename__ = 'alert_history'

    id = Column(Integer, primary_key=True, index=True)
    triggered_at = Column(DateTime, nullable=False) 
    resolved_at = Column(DateTime, nullable=True) 
    status = Column(String, nullable=False) 
    message = Column(Text)

    # Relations
    alert_id = Column(Integer, ForeignKey('alerts.id'), index=True)
    alert = relationship("Alert", back_populates="history")

class RefreshToken(Base):
    """
    Modèle pour la table 'refresh_tokens'.
    Gère les tokens de rafraîchissement pour l'authentification.
    """
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    user = relationship("User", back_populates="refresh_tokens")