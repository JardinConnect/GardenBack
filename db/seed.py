import os
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
# Importer les modèles qui existent dans la migration
from db.models import (
    User, Space, Role, UserSpace, Node, Analytic, Alert, AlertHistory, RefreshToken, AnalyticType
)
try:
    from settings import settings
except ImportError:
    settings = None
import bcrypt
import random

DATABASE_FILE_NAME = "database.db"

# Construire le chemin absolu du fichier de base de données
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
    print(f"DEBUG: Le script seed.py utilise l'URL de base de données : {DATABASE_URL}")

    # Extraire le chemin du fichier depuis l'URL
    db_path = DATABASE_URL.split("sqlite:///")[-1]
    if "sqlite" in DATABASE_URL and not os.path.exists(db_path):
        print(f"DEBUG: ERREUR - Le fichier de base de données SQLite n'existe PAS.")
        return

    db = SessionLocal()
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"): # Vérifie si la table users existe
            print(f"DEBUG: ERREUR - La table 'users' n'existe PAS. Assurez-vous que les migrations ont été appliquées.")
            return
            
        print("--- Démarrage du Seeding ---")

        # Seed des rôles
        seed_roles(db) 

        # Seed des utilisateurs
        seed_users(db)
        
        # Seed des espaces
        seed_spaces(db)
        
        # Seed des associations utilisateur-espace
        seed_user_spaces(db)
        
        # Seed des nœuds (Nodes) - Modifié pour correspondre au schéma
        seed_nodes(db)
        
        # Seed des données analytiques - Remplace seed_sensor_data
        seed_analytic(db)
        
        # Seed des alertes - Modifié pour correspondre au schéma
        seed_alerts(db)
        
        # Seed de l'historique des alertes
        seed_alert_history(db)
        
        # Seed des tokens de rafraîchissement
        seed_refresh_tokens(db)
        
        print("\n✅ Seeding terminé avec succès!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors du seeding : {e}")
        # Ligne utile pour le débogage, imprime la trace de l'erreur
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def seed_users(db):
    """Seed des utilisateurs (Compatible)"""
    print("Seeding Utilisateurs...")
    users_data = [
        {"first_name": "Sam", "last_name": "Gardener", "phone_number": "0611223344", "email": "sam@garden.com", "password": "garden1", "isAdmin": False},
        {"first_name": "Admin", "last_name": "Istrator", "phone_number": "0655667788", "email": "admin@garden.com", "password": "admin123", "isAdmin": True},
        {"first_name": "Marie", "last_name": "Fleur", "phone_number": "0699887766", "email": "marie@garden.com", "password": "marie123", "isAdmin": False},
    ]
    
    for user_data in users_data:
        existing = db.query(User).filter_by(email=user_data["email"]).first()
        if not existing:
            password = user_data["password"].encode('utf-8')
            user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone_number=user_data["phone_number"],
                email=user_data["email"],
                password=bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8'),
                isAdmin=user_data["isAdmin"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            try:
                db.add(user)
                db.commit()
                print(f"  > Utilisateur {user_data['first_name']} {user_data['last_name']} ajouté.")
            except Exception as e:
                db.rollback()
                print(f"  > ⚠️  Erreur lors de l'ajout de l'utilisateur {user_data['email']}: {e}")
        else:
            print(f"  > Utilisateur {user_data['email']} existe déjà, ignoré.")

def seed_roles(db):
    """Seed des rôles (Compatible)"""
    print("Seeding Rôles...")
    roles_data = [
        {"name": "manager"},
        {"name": "user"},
        {"name": "technician"},
    ]

    for role_data in roles_data:
        existing = db.query(Role).filter_by(name=role_data["name"]).first()
        if not existing:
            role = Role(
                name=role_data["name"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            db.add(role)
            print(f"  > Rôle {role_data['name']} ajouté.")
    db.commit()


def seed_spaces(db):
    """Seed des espaces (Compatible)"""
    print("Seeding Espaces (avec hiérarchie)...")
    spaces_data = [
        {"name": "Jardin Principal", "description": "Espace principal du jardin", "type": "outdoor", "location": "Entrée"},
        {"name": "Serre 1", "description": "Première serre pour les légumes", "type": "greenhouse", "location": "Nord"},
        {"name": "Serre 2", "description": "Seconde serre pour les fleurs", "type": "greenhouse", "location": "Sud"},
        {"name": "Zone Compost", "description": "Zone de compostage", "type": "compost", "location": "Arrière"},
    ]

    for space_data in spaces_data:
        existing = db.query(Space).filter_by(name=space_data["name"]).first()
        if not existing:
            space = Space(**space_data)
            db.add(space)
            print(f"  > Espace {space_data['name']} ajouté.")
    db.commit()

    # Création de la hiérarchie : Les serres appartiennent au Jardin Principal
    jardin = db.query(Space).filter_by(name="Jardin Principal").first()
    serre1 = db.query(Space).filter_by(name="Serre 1").first()
    serre2 = db.query(Space).filter_by(name="Serre 2").first()
    if jardin and serre1 and serre2:
        serre1.parent_id = jardin.id
        serre2.parent_id = jardin.id
        print("  > Hiérarchie des espaces créée.")
        db.commit()

def seed_user_spaces(db):
    """Seed des associations utilisateur-espace (Compatible)"""
    print("Seeding Associations User-Space...")
    users = {u.email: u.id for u in db.query(User.id, User.email).all()}
    spaces = {s.name: s.id for s in db.query(Space.id, Space.name).all()}
    roles = {r.name: r.id for r in db.query(Role.id, Role.name).all()}

    if not users or not spaces or not roles:
        print("  > ⚠️  Impossible de créer les associations : utilisateurs, espaces ou rôles manquants.")
        return

    associations = [
        {"email": "sam@garden.com", "space_name": "Jardin Principal", "role_name": "manager", "permissions": "read,write,admin"},
        {"email": "sam@garden.com", "space_name": "Serre 1", "role_name": "manager", "permissions": "read,write,admin"},
        {"email": "marie@garden.com", "space_name": "Serre 2", "role_name": "user", "permissions": "read,write"},
    ]

    for assoc in associations:
        user_id = users.get(assoc["email"])
        space_id = spaces.get(assoc["space_name"])
        role_id = roles.get(assoc["role_name"])

        if user_id and space_id and role_id:
            existing = db.query(UserSpace).filter_by(user_id=user_id, space_id=space_id).first()
            if not existing:
                user_space = UserSpace(
                    user_id=user_id,
                    space_id=space_id,
                    role_id=role_id,
                    permissions=assoc["permissions"]
                )
                db.add(user_space)
                print(f"  > Association {assoc['email']} -> {assoc['space_name']} ajoutée.")
    db.commit()

def seed_nodes(db):
    """Seed des nœuds (Nodes) - Adapté au schéma de la migration"""
    print("Seeding Nœuds...")
    spaces = {s.name: s.id for s in db.query(Space.id, Space.name).all()}
    
    if not spaces:
        print("  > ⚠️  Impossible de créer les nœuds : espaces manquants.")
        return
    
    nodes_data = [
        {"uid": "4C01", "status": "online", "RSSI": -55, "space_name": "Jardin Principal"},
        {"uid": "B3D4", "status": "online", "RSSI": -62, "space_name": "Serre 1"},
        {"uid": "A8F2", "status": "offline", "RSSI": -90, "space_name": "Serre 2"},
        {"uid": "9E1C", "status": "online", "RSSI": -71, "space_name": "Zone Compost"},
    ]
    
    for node_data in nodes_data:
        existing = db.query(Node).filter_by(uid=node_data["uid"]).first()
        if not existing:
            space_id = spaces.get(node_data["space_name"])
            if not space_id:
                print(f"  > ⚠️  Espace '{node_data['space_name']}' non trouvé. Nœud {node_data['uid']} non créé.")
                continue
                
            node = Node(
                uid=node_data["uid"],
                status=node_data["status"],
                RSSI=node_data["RSSI"],
                space_id=space_id
            )
            db.add(node)
            print(f"  > Nœud {node_data['uid']} ajouté à l'espace {node_data['space_name']}.")
    
    db.commit()

def seed_analytic(db):
    """Seed des données analytiques - Adapté au schéma de la migration"""
    print("Seeding Données (Analytic)...")
    nodes = db.query(Node).all()
    
    if not nodes:
        print("  > ⚠️  Impossible de créer des données analytiques : nœuds manquants.")
        return
    
    # Définition des capteurs avec des codes au format string
    sensor_definitions = [
        {"code": "TA-1", "type": AnalyticType.AIR_TEMPERATURE, "base": 18, "amplitude": 10}, # Température Air
        {"code": "TS-1", "type": AnalyticType.SOIL_TEMPERATURE, "base": 16, "amplitude": 5}, # Température Sol
        {"code": "HA-1", "type": AnalyticType.AIR_HUMIDITY, "base": 60, "amplitude": -20}, # Humidité Air (inverse de la temp)
        {"code": "HS-1", "type": AnalyticType.SOIL_HUMIDITY, "base": 55, "amplitude": 0}, # Humidité Sol
        {"code": "L-1", "type": AnalyticType.LIGHT, "base": 5, "amplitude": 4}, # Luminosité
        {"code": "B-1", "type": AnalyticType.BATTERY, "base": 95, "amplitude": 0}, # Batterie
    ]
    
    data_to_add = []
    
    for node in nodes:
        # Chaque nœud a tous les capteurs pour la démo
        node_sensors = sensor_definitions
        
        for sensor in node_sensors:
            for day in range(5):  # 5 jours de données
                for hour in range(24):  # Toutes les heures
                    occured_at = datetime.now(UTC) - timedelta(days=day, hours=hour)
                    
                    cycle = 0.0
                    # Simulation d'un cycle journalier (sinusoïdal) sur 24h
                    # Pic vers 14h, creux vers 4h du matin
                    if sensor["type"] == AnalyticType.LIGHT:
                        if 6 <= hour <= 20: # La lumière n'est présente que pendant la journée
                            cycle = (1 + random.uniform(-0.1, 0.1) - ((hour - 14) / 8) ** 2)
                        # else cycle reste 0 (pas de lumière la nuit)
                    else: # Pour les autres capteurs, la variation est continue
                        cycle = (1 + random.uniform(-0.1, 0.1) - ((hour - 14) / 12) ** 2)
                    
                    value = sensor["base"] + (sensor["amplitude"] * cycle) + random.uniform(-0.5, 0.5)
                    data = Analytic(
                        node_id=node.id,
                        sensor_code=sensor["code"],
                        analytic_type=sensor["type"],
                        value=round(value, 2),
                        occured_at=occured_at,
                    )
                    data_to_add.append(data)
    
    db.bulk_save_objects(data_to_add)
    db.commit()
    print(f"  > {len(data_to_add)} points de données analytiques générés.")

def seed_alerts(db):
    """Seed des alertes - Adapté au schéma de la migration"""
    print("Seeding Alertes...")
    
    analytics_to_alert_on = db.query(Analytic.node_id, Analytic.sensor_code)\
                              .distinct()\
                              .all()
    
    if not analytics_to_alert_on:
        print("  > ⚠️  Impossible de créer des alertes : aucune donnée analytique à surveiller.")
        return

    alert_templates = [
        {"name": "Température élevée", "condition": ">", "threshold": 28.0, "code_prefix": "TA"},
        {"name": "Sol trop sec", "condition": "<", "threshold": 30.0, "code_prefix": "HS"},
        {"name": "Batterie faible", "condition": "<", "threshold": 20.0, "code_prefix": "B"},
    ]
    
    for node_id, sensor_code in analytics_to_alert_on:
        for template in alert_templates:
            # Si le début du sensor_code correspond au préfixe de l'alerte
            if sensor_code.startswith(template["code_prefix"]):
                node_uid = db.query(Node.uid).filter(Node.id == node_id).scalar()
                alert_name = f"{template['name']} sur {node_uid}"
                
                existing = db.query(Alert).filter_by(name=alert_name).first()
                if not existing:
                    alert = Alert(
                        name=alert_name,
                        condition=template["condition"],
                        threshold=template["threshold"],
                        sensor_code=sensor_code,
                        node_id=node_id
                    )
                    db.add(alert)
                    print(f"  > Alerte '{alert_name}' créée.")
    
    db.commit()

def seed_alert_history(db):
    """Seed de l'historique des alertes (Compatible)"""
    print("Seeding Historique des Alertes...")
    alerts = db.query(Alert).all()
    
    if not alerts:
        print("  > ⚠️  Impossible de créer l'historique : alertes manquantes.")
        return
    
    history_to_add = []
    
    for alert in alerts:
        for _ in range(random.randint(1, 3)):
            triggered_at = datetime.now(UTC) - timedelta(days=random.randint(0, 4), hours=random.randint(0, 23))
            resolved_at = triggered_at + timedelta(minutes=random.randint(30, 240)) if random.choice([True, False]) else None
            
            history = AlertHistory(
                alert_id=alert.id,
                triggered_at=triggered_at,
                resolved_at=resolved_at,
                status="resolved" if resolved_at else "active",
                message=f"Alerte déclenchée : {alert.name} (valeur X)"
            )
            history_to_add.append(history)
            
    db.bulk_save_objects(history_to_add)
    db.commit()
    print(f"  > {len(history_to_add)} entrées d'historique d'alertes créées.")

def seed_refresh_tokens(db):
    """Seed des tokens de rafraîchissement (Compatible)"""
    print("Seeding Tokens de Rafraîchissement...")
    users = db.query(User).all()
    
    if not users:
        print("  > ⚠️  Impossible de créer les tokens : utilisateurs manquants.")
        return
    
    for user in users:
        token = RefreshToken(
            token=str(uuid.uuid4()),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30)
        )
        db.add(token)
    
    db.commit()
    print(f"  > {len(users)} tokens de rafraîchissement créés.")

if __name__ == "__main__":
    seed()