import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect 
from sqlalchemy.orm import sessionmaker
from models import Base, User, Space, UserSpace, ArduinoNode, Sensor, SensorData, Alert, AlertHistory, RefreshToken
import bcrypt
import random

DATABASE_FILE_NAME = "database.db"

# Construire le chemin absolu du fichier de base de données pour éviter les problèmes de répertoire de travail.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATABASE_PATH = os.path.join(PROJECT_ROOT, DATABASE_FILE_NAME)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed():
    """
    Fonction de remplissage de la base de données avec des données initiales.
    """
    print(f"DEBUG: Le script seed.py s'attend à trouver la base de données à : {DATABASE_PATH}")

    # Vérifie si le fichier de base de données existe physiquement
    if not os.path.exists(DATABASE_PATH):
        print(f"DEBUG: ERREUR - Le fichier de base de données n'existe PAS à : {DATABASE_PATH}")
        print("DEBUG: Cela signifie que 'make rebuild' n'a pas créé le fichier ou l'a créé ailleurs.")
        return

    db = SessionLocal()
    try:
        # Utilise l'inspecteur SQLAlchemy pour vérifier si la table 'users' existe dans la DB ouverte
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            print(f"DEBUG: ERREUR - La table 'users' n'existe PAS dans la base de données à : {DATABASE_PATH}")
            print("DEBUG: Les migrations n'ont peut-être pas été appliquées correctement à cette base de données.")
            return

        # Seed des utilisateurs
        seed_users(db)
        
        # Seed des espaces
        seed_spaces(db)
        
        # Seed des associations utilisateur-espace
        seed_user_spaces(db)
        
        # Seed des nœuds Arduino
        seed_arduino_nodes(db)
        
        # Seed des capteurs
        seed_sensors(db)
        
        # Seed des données de capteurs
        seed_sensor_data(db)
        
        # Seed des alertes
        seed_alerts(db)
        
        # Seed de l'historique des alertes
        seed_alert_history(db)
        
        # Seed des tokens de rafraîchissement
        seed_refresh_tokens(db)
        
        print("✅ Seeding terminé avec succès!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors du seeding : {e}")
    finally:
        db.close()

def seed_users(db):
    """Seed des utilisateurs"""
    users_data = [
        {"username": "sam", "email": "sam@garden.com", "password": "garden1", "role": "user"},
        {"username": "admin", "email": "admin@garden.com", "password": "admin123", "role": "admin"},
        {"username": "marie", "email": "marie@garden.com", "password": "marie123", "role": "user"},
        {"username": "john", "email": "john@garden.com", "password": "john123", "role": "user"},
        {"username": "tech", "email": "tech@garden.com", "password": "tech123", "role": "admin"},
    ]
    
    for user_data in users_data:
        existing = db.query(User).filter_by(username=user_data["username"]).first()
        if not existing:
            password = user_data["password"].encode('utf-8')
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password=bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8'),
                role=user_data["role"]
            )
            db.add(user)
            print(f"✅ Utilisateur {user_data['username']} ajouté.")
        else:
            print(f"⚠️  L'utilisateur {user_data['username']} existe déjà.")
    
    db.commit()

def seed_spaces(db):
    """Seed des espaces"""
    spaces_data = [
        {"name": "Jardin Principal", "description": "Espace principal du jardin", "type": "outdoor", "location": "Entrée"},
        {"name": "Serre 1", "description": "Première serre pour les légumes", "type": "greenhouse", "location": "Nord"},
        {"name": "Serre 2", "description": "Seconde serre pour les fleurs", "type": "greenhouse", "location": "Sud"},
        {"name": "Zone Compost", "description": "Zone de compostage", "type": "compost", "location": "Arrière"},
        {"name": "Réservoir d'eau", "description": "Réservoir principal d'eau", "type": "water", "location": "Centre"},
    ]
    
    for space_data in spaces_data:
        existing = db.query(Space).filter_by(name=space_data["name"]).first()
        if not existing:
            space = Space(**space_data)
            db.add(space)
            print(f"✅ Espace {space_data['name']} ajouté.")
        else:
            print(f"⚠️  L'espace {space_data['name']} existe déjà.")
    
    db.commit()

def seed_user_spaces(db):
    """Seed des associations utilisateur-espace"""
    users = db.query(User).all()
    spaces = db.query(Space).all()
    
    if not users or not spaces:
        print("⚠️  Impossible de créer les associations utilisateur-espace : utilisateurs ou espaces manquants.")
        return
    
    # Associer quelques utilisateurs à des espaces
    associations = [
        {"username": "sam", "space_name": "Jardin Principal", "role": "manager", "permissions": "read,write,admin"},
        {"username": "sam", "space_name": "Serre 1", "role": "manager", "permissions": "read,write,admin"},
        {"username": "marie", "space_name": "Serre 2", "role": "user", "permissions": "read,write"},
        {"username": "john", "space_name": "Zone Compost", "role": "user", "permissions": "read"},
        {"username": "tech", "space_name": "Réservoir d'eau", "role": "technician", "permissions": "read,write,maintain"},
    ]
    
    for assoc in associations:
        user = db.query(User).filter_by(username=assoc["username"]).first()
        space = db.query(Space).filter_by(name=assoc["space_name"]).first()
        
        if user and space:
            existing = db.query(UserSpace).filter_by(user_id=user.id, space_id=space.id).first()
            if not existing:
                user_space = UserSpace(
                    user_id=user.id,
                    space_id=space.id,
                    role=assoc["role"],
                    permissions=assoc["permissions"]
                )
                db.add(user_space)
                print(f"✅ Association {assoc['username']} -> {assoc['space_name']} ajoutée.")
    
    db.commit()

def seed_arduino_nodes(db):
    """Seed des nœuds Arduino"""
    spaces = db.query(Space).all()
    
    if not spaces:
        print("⚠️  Impossible de créer les nœuds Arduino : espaces manquants.")
        return
    
    nodes_data = [
        {"name": "Arduino-Garden-01", "description": "Nœud principal du jardin", "firmware_version": "1.2.3", "location": "Entrée", "status": "online", "battery_level": 85.5},
        {"name": "Arduino-Greenhouse-01", "description": "Nœud de la serre 1", "firmware_version": "1.2.3", "location": "Serre Nord", "status": "online", "battery_level": 92.1},
        {"name": "Arduino-Greenhouse-02", "description": "Nœud de la serre 2", "firmware_version": "1.2.2", "location": "Serre Sud", "status": "offline", "battery_level": 45.3},
        {"name": "Arduino-Water-01", "description": "Nœud du réservoir d'eau", "firmware_version": "1.2.3", "location": "Réservoir", "status": "online", "battery_level": 78.9},
    ]
    
    for i, node_data in enumerate(nodes_data):
        existing = db.query(ArduinoNode).filter_by(name=node_data["name"]).first()
        if not existing:
            node = ArduinoNode(
                name=node_data["name"],
                description=node_data["description"],
                firmware_version=node_data["firmware_version"],
                location=node_data["location"],
                api_key=str(uuid.uuid4()),
                status=node_data["status"],
                last_connection=datetime.utcnow() - timedelta(minutes=random.randint(1, 60)),
                battery_level=node_data["battery_level"],
                space_id=spaces[i % len(spaces)].id
            )
            db.add(node)
            print(f"✅ Nœud Arduino {node_data['name']} ajouté.")
        else:
            print(f"⚠️  Le nœud Arduino {node_data['name']} existe déjà.")
    
    db.commit()

def seed_sensors(db):
    """Seed des capteurs"""
    nodes = db.query(ArduinoNode).all()
    
    if not nodes:
        print("⚠️  Impossible de créer les capteurs : nœuds Arduino manquants.")
        return
    
    sensor_types = [
        {"name": "Température", "type": "temperature", "model": "DHT22", "min_value": -40, "max_value": 80, "unit": "°C"},
        {"name": "Humidité", "type": "humidity", "model": "DHT22", "min_value": 0, "max_value": 100, "unit": "%"},
        {"name": "Luminosité", "type": "light", "model": "BH1750", "min_value": 0, "max_value": 65535, "unit": "lux"},
        {"name": "Humidité du sol", "type": "soil_moisture", "model": "FC-28", "min_value": 0, "max_value": 1023, "unit": "raw"},
    ]
    
    for node in nodes:
        # Ajouter 2-3 capteurs par nœud
        for i in range(random.randint(2, 3)):
            sensor_data = random.choice(sensor_types)
            sensor_name = f"{sensor_data['name']} - {node.name}"
            
            existing = db.query(Sensor).filter_by(name=sensor_name).first()
            if not existing:
                sensor = Sensor(
                    name=sensor_name,
                    type=sensor_data["type"],
                    model=sensor_data["model"],
                    position_on_node=f"Port {i+1}",
                    is_active=True,
                    min_value=sensor_data["min_value"],
                    max_value=sensor_data["max_value"],
                    calibration_offset=random.uniform(-2, 2),
                    arduino_node_id=node.id
                )
                db.add(sensor)
                print(f"✅ Capteur {sensor_name} ajouté.")
    
    db.commit()

def seed_sensor_data(db):
    """Seed des données de capteurs"""
    sensors = db.query(Sensor).all()
    
    if not sensors:
        print("⚠️  Impossible de créer les données de capteurs : capteurs manquants.")
        return
    
    # Générer des données pour les 7 derniers jours
    for sensor in sensors:
        for day in range(7):
            for hour in range(0, 24, 2):  # Toutes les 2 heures
                timestamp = datetime.utcnow() - timedelta(days=day, hours=hour)
                
                # Générer des valeurs réalistes selon le type de capteur
                if sensor.type == "temperature":
                    value = random.uniform(15, 35)
                elif sensor.type == "humidity":
                    value = random.uniform(30, 80)
                elif sensor.type == "light":
                    value = random.uniform(100, 50000)
                elif sensor.type == "soil_moisture":
                    value = random.uniform(200, 800)
                else:
                    value = random.uniform(0, 100)
                
                data = SensorData(
                    sensor_id=sensor.id,
                    value=value,
                    timestamp=timestamp,
                    unit_of_measure=get_unit_for_sensor_type(sensor.type)
                )
                db.add(data)
    
    db.commit()
    print("✅ Données de capteurs générées pour les 7 derniers jours.")

def get_unit_for_sensor_type(sensor_type):
    """Retourne l'unité de mesure pour un type de capteur donné"""
    units = {
        "temperature": "°C",
        "humidity": "%",
        "light": "lux",
        "soil_moisture": "raw"
    }
    return units.get(sensor_type, "unit")

def seed_alerts(db):
    """Seed des alertes"""
    sensors = db.query(Sensor).all()
    
    if not sensors:
        print("⚠️  Impossible de créer les alertes : capteurs manquants.")
        return
    
    # Créer des alertes pour certains capteurs
    for sensor in sensors:
        if sensor.type == "temperature":
            # Alerte température trop élevée
            alert = Alert(
                name=f"Température élevée - {sensor.name}",
                condition=">",
                threshold=30.0,
                is_active=True,
                sensor_id=sensor.id
            )
            db.add(alert)
            
        elif sensor.type == "humidity":
            # Alerte humidité trop faible
            alert = Alert(
                name=f"Humidité faible - {sensor.name}",
                condition="<",
                threshold=40.0,
                is_active=True,
                sensor_id=sensor.id
            )
            db.add(alert)
            
        elif sensor.type == "soil_moisture":
            # Alerte sol trop sec
            alert = Alert(
                name=f"Sol sec - {sensor.name}",
                condition="<",
                threshold=300.0,
                is_active=True,
                sensor_id=sensor.id
            )
            db.add(alert)
    
    db.commit()
    print("✅ Alertes créées pour les capteurs.")

def seed_alert_history(db):
    """Seed de l'historique des alertes"""
    alerts = db.query(Alert).all()
    
    if not alerts:
        print("⚠️  Impossible de créer l'historique des alertes : alertes manquantes.")
        return
    
    # Créer quelques déclenchements d'alertes dans l'historique
    for alert in alerts:
        # Créer 1-3 déclenchements d'alerte dans les 7 derniers jours
        for _ in range(random.randint(1, 3)):
            triggered_at = datetime.utcnow() - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))
            resolved_at = triggered_at + timedelta(minutes=random.randint(30, 240)) if random.choice([True, False]) else None
            
            history = AlertHistory(
                alert_id=alert.id,
                triggered_at=triggered_at,
                resolved_at=resolved_at,
                status="resolved" if resolved_at else "active",
                message=f"Alerte déclenchée : {alert.name}"
            )
            db.add(history)
    
    db.commit()
    print("✅ Historique des alertes créé.")

def seed_refresh_tokens(db):
    """Seed des tokens de rafraîchissement"""
    users = db.query(User).all()
    
    if not users:
        print("⚠️  Impossible de créer les tokens de rafraîchissement : utilisateurs manquants.")
        return
    
    # Créer des tokens pour certains utilisateurs
    for user in users[:3]:  # Seulement pour les 3 premiers utilisateurs
        token = RefreshToken(
            token=str(uuid.uuid4()),
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.add(token)
    
    db.commit()
    print("✅ Tokens de rafraîchissement créés.")

if __name__ == "__main__":
    seed()