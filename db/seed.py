import os
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine, inspect 
from sqlalchemy.orm import sessionmaker, Session
from models import AnalyticType, User, Area, Analytic, RefreshToken, Cell, Sensor, RoleEnum, Farm
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
    print(f"DEBUG: Le script seed.py s'attend à trouver la base de données à : {DATABASE_PATH}")

    if not os.path.exists(DATABASE_PATH):
        print(f"DEBUG: ERREUR - Le fichier de base de données n'existe PAS à : {DATABASE_PATH}")
        return

    db = SessionLocal()
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            print(f"DEBUG: ERREUR - La table 'users' n'existe PAS dans la base de données à : {DATABASE_PATH}")
            return
            
        print("--- Démarrage du Seeding ---")

        # Nettoyage des anciennes données
        print("Nettoyage des tables...")
        db.query(Analytic).delete()
        db.query(Sensor).delete()
        db.query(Cell).delete()
        db.query(Area).delete()
        db.query(User).delete()  # On supprime les users pour repartir de zéro
        db.query(RefreshToken).delete()
        db.query(Farm).delete()
        db.commit()

        # Seed de la ferme
        print("\n🏡 Seeding Ferme...")
        if not db.query(Farm).first():
            db.add(Farm(name="Ferme de test"))
            db.commit()
            print("  ✓ Ferme 'Ferme de test' créée.")
        else:
            print("  - La ferme existe déjà, ignoré.")

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

def seed_users(db: Session):
    """Seed des utilisateurs"""
    print("\n📋 Seeding Utilisateurs...")
    users_data = [
        {"first_name": "Sam", "last_name": "Gardener", "phone_number": "0611223344", "email": "sam@garden.com", "password": "garden1", "role": RoleEnum.EMPLOYEES},
        {"first_name": "Admin", "last_name": "Istrator", "phone_number": "0655667788", "email": "admin@garden.com", "password": "admin123", "role": RoleEnum.ADMIN},
        {"first_name": "Marie", "last_name": "Fleur", "phone_number": "0699887766", "email": "marie@garden.com", "password": "marie123", "role": RoleEnum.EMPLOYEES},
        {"first_name": "Super", "last_name": "Admin", "phone_number": "0600000000", "email": "superadmin@garden.com", "password": "superadmin123", "role": RoleEnum.SUPERADMIN},
    ]

    for user_data in users_data:
        existing = db.query(User).filter_by(email=user_data["email"]).first()
        if not existing:
            password = user_data["password"].encode('utf-8')
            user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone_number=user_data.get("phone_number"),
                email=user_data["email"],
                password=bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8'),
                role=user_data["role"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            db.add(user)
            print(f"  ✓ Utilisateur '{user_data['first_name']} {user_data['last_name']}' créé")
        else:
            print(f"  - Utilisateur '{user_data['email']}' existe déjà, ignoré.")
    
    db.commit()


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
        parent_id=None
    )
    parcelle_sud = Area(
        name="Parcelle Sud", 
        color="#228B22",
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
        parent_id=parcelle_nord.id
    )
    planche_salades = Area(
        name="Planche Salades",
        color="#90EE90",
        parent_id=parcelle_nord.id
    )
    
    # Planches de la Parcelle Sud
    planche_carottes = Area(
        name="Planche Carottes",
        color="#FFA500",
        parent_id=parcelle_sud.id
    )
    planche_herbes = Area(
        name="Planche Herbes Aromatiques",
        color="#9ACD32",
        parent_id=parcelle_sud.id
    )
    
    db.add_all([planche_tomates, planche_salades, planche_carottes, planche_herbes])
    db.commit()
    
    for planche in [planche_tomates, planche_salades, planche_carottes, planche_herbes]:
        db.refresh(planche)
        print(f"    ✓ Planche '{planche.name}' (ID: {planche.id}, Parent: {planche.parent_id})")

    # === NIVEAU 3 : SOUS-PLANCHES (exemple avec une planche qui contient d'autres planches) ===
    print("\n  📍 Création des sous-planches (Niveau 3)...")
    
    sous_planche_tomates_cerises = Area(
        name="Section Tomates Cerises",
        color="#FF4500",
        parent_id=planche_tomates.id
    )
    sous_planche_tomates_coeur = Area(
        name="Section Tomates Coeur de Boeuf",
        color="#DC143C",
        parent_id=planche_tomates.id
    )
    
    db.add_all([sous_planche_tomates_cerises, sous_planche_tomates_coeur])
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
        
        for cell_config in area_config["cells"]:
            # Créer la cellule
            cell = Cell(
                name=cell_config["name"],
                area_id=area.id
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
                occurred_at = datetime.now(UTC) - timedelta(days=day, hours=hour)
                
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
                    occurred_at=occurred_at
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
        print(f"  ✓ Token créé pour '{user.email}'")
    
    db.commit()


if __name__ == "__main__":
    seed()