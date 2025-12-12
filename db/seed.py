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
        print("DEBUG: ERREUR - Le fichier de base de données SQLite n'existe PAS.")
        return

    db = SessionLocal()
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"): # Vérifie si la table users existe
            print("DEBUG: ERREUR - La table 'users' n'existe PAS. Assurez-vous que les migrations ont été appliquées.")
            return
            
        print("--- Démarrage du Seeding ---")

        # Nettoyage des anciennes données
        print("Nettoyage des tables...")
        db.query(Analytic).delete()
        db.query(Sensor).delete()
        db.query(Cell).delete()
        db.query(Area).delete()
        db.query(RefreshToken).delete()
        db.commit()

        # Seed des utilisateurs
        seed_users(db)
        
        # Seed de la structure hiérarchique : Areas -> Cells -> Sensors
        seed_garden_hierarchy(db)
        
        # Seed des données analytiques
        seed_analytics(db)
        
        # Seed des tokens de rafraîchissement
        seed_refresh_tokens(db)
        
        print("\n✅ Seeding terminé avec succès!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors du seeding : {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def seed_users(db):
    """Seed des utilisateurs"""
    print("\n📋 Seeding Utilisateurs...")
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


def seed_garden_hierarchy(db):
    """
    Seed de la structure hiérarchique complète du jardin.
    Structure : Parcelle (niveau 1) -> Planches (niveau 2) -> Cellules -> Capteurs
    """
    print("\n🌱 Seeding Structure Hiérarchique du Jardin...")
    
    # === NIVEAU 1 : PARCELLES ===
    print("\n  📍 Création des parcelles (Niveau 1)...")
    parcelle_nord = Area(
        name="Parcelle Nord",
        color="#2E8B57",
        level=1,
        parent_id=None
    )
    parcelle_sud = Area(
        name="Parcelle Sud", 
        color="#228B22",
        level=1,
        parent_id=None
    )
    
    db.add_all([parcelle_nord, parcelle_sud])
    db.commit()
    db.refresh(parcelle_nord)
    db.refresh(parcelle_sud)
    print(f"    ✓ Parcelle '{parcelle_nord.name}' (ID: {parcelle_nord.id})")
    print(f"    ✓ Parcelle '{parcelle_sud.name}' (ID: {parcelle_sud.id})")

    # === NIVEAU 2 : PLANCHES (enfants des parcelles) ===
    print("\n  📍 Création des planches (Niveau 2)...")
    
    # Planches de la Parcelle Nord
    planche_tomates = Area(
        name="Planche Tomates",
        color="#FF6347",
        level=2,
        parent_id=parcelle_nord.id
    )
    planche_salades = Area(
        name="Planche Salades",
        color="#90EE90",
        level=2,
        parent_id=parcelle_nord.id
    )
    
    # Planches de la Parcelle Sud
    planche_carottes = Area(
        name="Planche Carottes",
        color="#FFA500",
        level=2,
        parent_id=parcelle_sud.id
    )
    planche_herbes = Area(
        name="Planche Herbes Aromatiques",
        color="#9ACD32",
        level=2,
        parent_id=parcelle_sud.id
    )
    
    db.add_all([planche_tomates, planche_salades, planche_carottes, planche_herbes])
    db.commit()
    
    for planche in [planche_tomates, planche_salades, planche_carottes, planche_herbes]:
        db.refresh(planche)
        print(f"    ✓ Planche '{planche.name}' (ID: {planche.id}, Parent: {planche.parent_id})")

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
    db.refresh(sous_planche_tomates_cerises)
    db.refresh(sous_planche_tomates_coeur)
    print(f"    ✓ Sous-planche '{sous_planche_tomates_cerises.name}' (ID: {sous_planche_tomates_cerises.id})")
    print(f"    ✓ Sous-planche '{sous_planche_tomates_coeur.name}' (ID: {sous_planche_tomates_coeur.id})")

    # === COMPTEURS POUR LES SENSOR_ID UNIQUES ===
    sensor_counters = {
        "TA": 1, "TS": 1, "HA": 1, "HS": 1, "L": 1, "B": 1
    }
    def get_sensor_id(prefix: str) -> str:
        num = sensor_counters[prefix]
        sensor_counters[prefix] += 1
        return f"{prefix}-{num}"

    # === CELLULES ET CAPTEURS ===
    print("\n  📦 Création des cellules et capteurs...")
    
    # Dictionnaire pour stocker les configurations de cellules
    cells_config = [
        # Cellules de la sous-planche Tomates Cerises
        {
            "area": sous_planche_tomates_cerises,
            "cells": [
                {
                    "name": "Rangée A - Tomates Cerises",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                        {"prefix": "HA", "type": "air_humidity"},
                        {"prefix": "L", "type": "light"},
                        {"prefix": "TS", "type": "soil_temperature"},
                        {"prefix": "HS", "type": "soil_humidity"},
                        {"prefix": "B", "type": "battery"},
                    ]
                },
                {
                    "name": "Rangée B - Tomates Cerises",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                        {"prefix": "HA", "type": "air_humidity"},
                    ]
                }
            ]
        },
        # Cellules de la sous-planche Tomates Coeur de Boeuf
        {
            "area": sous_planche_tomates_coeur,
            "cells": [
                {
                    "name": "Rangée A - Coeur de Boeuf",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                        {"prefix": "HA", "type": "air_humidity"},
                    ]
                }
            ]
        },
        # Cellules de la planche Salades
        {
            "area": planche_salades,
            "cells": [
                {
                    "name": "Section Laitues",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                        {"prefix": "HA", "type": "air_humidity"},
                    ]
                },
                {
                    "name": "Section Roquette",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                    ]
                }
            ]
        },
        # Cellules de la planche Carottes
        {
            "area": planche_carottes,
            "cells": [
                {
                    "name": "Carottes Nantaises",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                        {"prefix": "HA", "type": "air_humidity"},
                    ]
                }
            ]
        },
        # Cellules de la planche Herbes
        {
            "area": planche_herbes,
            "cells": [
                {
                    "name": "Section Basilic",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                        {"prefix": "HA", "type": "air_humidity"},
                        {"prefix": "L", "type": "light"},
                    ]
                },
                {
                    "name": "Section Persil",
                    "sensors": [
                        {"prefix": "TA", "type": "air_temperature"},
                    ]
                }
            ]
        }
    ]
    
    # Créer toutes les cellules et capteurs
    all_sensors = []
    for area_config in cells_config:
        area = area_config["area"]
        print(f"\n    📍 Area '{area.name}':")
        
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
            db.add(cell)
            db.commit()
            db.refresh(cell)
            print(f"      ✓ Cellule '{cell.name}' (ID: {cell.id})")
            
            # Créer les capteurs de cette cellule
            for sensor_config in cell_config["sensors"]:
                sensor = Sensor(
                    sensor_id=get_sensor_id(sensor_config["prefix"]),
                    sensor_type=sensor_config["type"],
                    status="active",
                    cell_id=cell.id
                )
                db.add(sensor)
                all_sensors.append(sensor)
                print(f"        • Capteur '{sensor.sensor_id}' ({sensor.sensor_type})")
    
    db.commit()
    print(f"\n  ✅ Structure créée : {len(all_sensors)} capteurs répartis dans les cellules")


def seed_analytics(db):
    """
    Seed des données analytiques pour tous les capteurs.
    Génère 7 jours d'historique avec des relevés toutes les heures.
    """
    print("\n📊 Seeding Données Analytiques...")
    
    sensors = db.query(Sensor).all()
    
    if not sensors:
        print("  ⚠️  Aucun capteur trouvé. Impossible de générer des analytics.")
        return
    
    analytics_to_add = []
    total_days = 7
    
    for sensor in sensors:
        print(f"  📡 Génération de données pour '{sensor.sensor_id}' ({sensor.sensor_type})...")
        
        # Déterminer le type d'analytique à partir du préfixe du sensor_id
        try:
            prefix = sensor.sensor_id.split('-')[0]
            analytic_type = AnalyticType.from_prefix(prefix)
        except (ValueError, IndexError):
            print(f"  ⚠️  Impossible de déterminer le type d'analytique pour '{sensor.sensor_id}'. Utilisation de AIR_TEMPERATURE par défaut.")
            analytic_type = AnalyticType.AIR_TEMPERATURE

        # Configuration de base selon le type d'analytique
        if analytic_type in [AnalyticType.AIR_TEMPERATURE, AnalyticType.SOIL_TEMPERATURE]:
            base_value = 22.0
            amplitude = 6.0
            noise = 0.5
        elif analytic_type in [AnalyticType.AIR_HUMIDITY, AnalyticType.SOIL_HUMIDITY]:
            base_value = 65.0
            amplitude = -10.0  # Inverse de la température (quand il fait chaud, moins humide)
            noise = 2.0
        elif analytic_type == AnalyticType.LIGHT:
            base_value = 50.0
            amplitude = 40.0
            noise = 5.0
        elif analytic_type == AnalyticType.BATTERY:
            base_value = 95.0
            amplitude = -5.0 # La batterie se décharge un peu
            noise = 1.0
        else:
            continue
        
        # Générer les données pour chaque jour et chaque heure
        # On génère des données pour aujourd'hui (day=0) et les 6 jours précédents.
        for day in range(total_days):
            for hour in range(24):
                occured_at = datetime.now(UTC) - timedelta(days=day, hours=hour)
                
                # Simulation d'un cycle journalier (sinusoïdal) sur 24h
                # Pic vers 14h, creux vers 4h du matin
                hour_factor = 1 - ((hour - 14) / 12) ** 2
                cycle_value = hour_factor + random.uniform(-0.1, 0.1)
                
                value = base_value + (amplitude * cycle_value) + random.uniform(-noise, noise)
                
                # Éviter les valeurs négatives
                value = max(0, value)
                
                analytic = Analytic(
                    sensor_id=sensor.id,
                    sensor_code=sensor.sensor_id,
                    analytic_type=analytic_type,
                    value=round(value, 2),
                    occured_at=occured_at
                )
                analytics_to_add.append(analytic)
    
    # Insertion en masse pour les performances
    db.bulk_save_objects(analytics_to_add)
    db.commit()
    
    print(f"  ✅ {len(analytics_to_add)} points de données analytiques générés")
    print(f"     ({total_days} jours × 24 heures × {len(sensors)} capteurs)")


def seed_refresh_tokens(db):
    """Seed des tokens de rafraîchissement"""
    print("\n🔑 Seeding Tokens de Rafraîchissement...")
    users = db.query(User).all()
    
    if not users:
        print("  ⚠️  Impossible de créer les tokens : utilisateurs manquants.")
        return
    
    for user in users:
        token = RefreshToken(
            token=str(uuid.uuid4()),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30)
        )
        db.add(token)
        print(f"  ✓ Token créé pour '{user.username}'")
    
    db.commit()


if __name__ == "__main__":
    seed()