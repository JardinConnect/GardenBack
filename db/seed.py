import os
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker, Session
from db.models import (
    AnalyticType, User, Area, Analytic, RefreshToken, Cell, Sensor, RoleEnum, Farm,
    Alert, AlertEvent, SeverityEnum,
)
from services.area.service import get_full_location_path_for_cell
import bcrypt
import random
import math

DATABASE_FILE_NAME = "database.db"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATABASE_PATH = os.path.join(PROJECT_ROOT, DATABASE_FILE_NAME)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed():
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

        print("Nettoyage des tables...")
        db.query(AlertEvent).delete()
        db.query(Alert).delete()
        db.query(Analytic).delete()
        db.query(Sensor).delete()
        db.query(Cell).delete()
        db.query(Area).delete()
        db.query(User).delete()
        db.query(RefreshToken).delete()
        db.query(Farm).delete()
        db.commit()

        # Ferme
        print("\n🏡 Seeding Ferme...")
        db.add(Farm(
            name="Ferme de Léo le BG",
            address="123 Rue de la Ferme",
            zip_code="44000",
            city="Nanoed",
            phone_number="0240123456"
        ))
        db.commit()
        print("  ✓ Ferme 'Ferme de test' créée.")

        seed_users(db)
        cells = seed_garden_hierarchy(db)
        seed_analytics(db)
        seed_refresh_tokens(db)
        seed_alerts(db, cells)

        print("\n✅ Seeding terminé avec succès!")

    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors du seeding : {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def seed_users(db: Session):
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
            password = user_data["password"].encode("utf-8")
            user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                phone_number=user_data.get("phone_number"),
                email=user_data["email"],
                password=bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8"),
                role=user_data["role"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(user)
            print(f"  ✓ Utilisateur '{user_data['first_name']} {user_data['last_name']}' créé")

    db.commit()


def seed_garden_hierarchy(db: Session) -> list[Cell]:
    """
    Seed de la structure hiérarchique.
    Retourne la liste de toutes les cellules créées (pour le seed des alertes).
    """
    print("\n🌱 Seeding Structure Hiérarchique du Jardin...")

    admin_user = db.query(User).filter(User.email == "admin@garden.com").first()
    if not admin_user:
        raise Exception("Admin user not found. Cannot seed areas without an originator.")
    admin_user_id = admin_user.id

    # Niveau 1 — Parcelles
    print("\n  📍 Création des parcelles (Niveau 1)...")
    parcelle_nord = Area(name="Parcelle Nord", color="#2E8B57", originator_id=admin_user_id, updater_id=admin_user_id)
    parcelle_sud = Area(name="Parcelle Sud", color="#228B22", originator_id=admin_user_id, updater_id=admin_user_id)
    db.add_all([parcelle_nord, parcelle_sud])
    db.commit()
    db.refresh(parcelle_nord)
    db.refresh(parcelle_sud)
    print(f"    ✓ '{parcelle_nord.name}' / '{parcelle_sud.name}'")

    # Niveau 2 — Planches
    print("\n  📍 Création des planches (Niveau 2)...")
    planche_tomates = Area(name="Planche Tomates", color="#FF6347", parent_id=parcelle_nord.id, originator_id=admin_user_id, updater_id=admin_user_id)
    planche_salades = Area(name="Planche Salades", color="#90EE90", parent_id=parcelle_nord.id, originator_id=admin_user_id, updater_id=admin_user_id)
    planche_carottes = Area(name="Planche Carottes", color="#FFA500", parent_id=parcelle_sud.id, originator_id=admin_user_id, updater_id=admin_user_id)
    planche_herbes = Area(name="Planche Herbes Aromatiques", color="#9ACD32", parent_id=parcelle_sud.id, originator_id=admin_user_id, updater_id=admin_user_id)
    db.add_all([planche_tomates, planche_salades, planche_carottes, planche_herbes])
    db.commit()
    for p in [planche_tomates, planche_salades, planche_carottes, planche_herbes]:
        db.refresh(p)
        print(f"    ✓ '{p.name}'")

    # Niveau 3 — Sous-planches
    print("\n  📍 Création des sous-planches (Niveau 3)...")
    sous_planche_tomates_cerises = Area(name="Section Tomates Cerises", color="#FF4500", parent_id=planche_tomates.id, originator_id=admin_user_id, updater_id=admin_user_id)
    sous_planche_tomates_coeur = Area(name="Section Tomates Coeur de Boeuf", color="#DC143C", parent_id=planche_tomates.id, originator_id=admin_user_id, updater_id=admin_user_id)
    db.add_all([sous_planche_tomates_cerises, sous_planche_tomates_coeur])
    db.commit()
    db.refresh(sous_planche_tomates_cerises)
    db.refresh(sous_planche_tomates_coeur)

    # Cellules & capteurs
    print("\n  📦 Création des cellules et capteurs...")
    cells_config = [
        {
            "area": sous_planche_tomates_cerises,
            "cells": [
                {"name": "Rangée A - Tomates Cerises", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                    {"sensor_id": "1HA", "type": "air_humidity"},
                    {"sensor_id": "1L", "type": "light"},
                    {"sensor_id": "1TS", "type": "soil_temperature"},
                    {"sensor_id": "1HS", "type": "soil_humidity"},
                    {"sensor_id": "2HS", "type": "deep_soil_humidity"},
                    {"sensor_id": "1VB", "type": "battery_voltage"},
                    {"sensor_id": "1SB", "type": "battery_soc"},
                ]},
                {"name": "Rangée B - Tomates Cerises", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                    {"sensor_id": "1HA", "type": "air_humidity"},
                ]},
            ],
        },
        {
            "area": sous_planche_tomates_coeur,
            "cells": [
                {"name": "Rangée A - Coeur de Boeuf", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                    {"sensor_id": "1HA", "type": "air_humidity"},
                ]},
            ],
        },
        {
            "area": planche_salades,
            "cells": [
                {"name": "Section Laitues", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                    {"sensor_id": "1HA", "type": "air_humidity"},
                ]},
                {"name": "Section Roquette", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                ]},
            ],
        },
        {
            "area": planche_carottes,
            "cells": [
                {"name": "Carottes Nantaises", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                    {"sensor_id": "1HA", "type": "air_humidity"},
                ]},
            ],
        },
        {
            "area": planche_herbes,
            "cells": [
                {"name": "Section Basilic", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                    {"sensor_id": "1HA", "type": "air_humidity"},
                    {"sensor_id": "1L", "type": "light"},
                ]},
                {"name": "Section Persil", "sensors": [
                    {"sensor_id": "1TA", "type": "air_temperature"},
                ]},
            ],
        },
    ]

    all_cells: list[Cell] = []
    all_sensors: list[Sensor] = []

    cell_counter = 1
    for area_config in cells_config:
        area = area_config["area"]
        print(f"\n    📍 Area '{area.name}':")
        for cell_config in area_config["cells"]:
            # Ajout du deviceID obligatoire
            cell = Cell(name=cell_config["name"], area_id=area.id, deviceID=f"SEED-DEVICE-{cell_counter}")
            cell_counter += 1
            db.add(cell)
            db.commit()
            db.refresh(cell)
            all_cells.append(cell)
            print(f"      ✓ Cellule '{cell.name}' (ID: {cell.id})")
            for sensor_config in cell_config["sensors"]:
                sensor = Sensor(
                    sensor_id=sensor_config["sensor_id"],
                    sensor_type=sensor_config["type"],
                    status="active",
                    cell_id=cell.id,
                )
                db.add(sensor)
                all_sensors.append(sensor)
                print(f"        • Capteur '{sensor.sensor_id}' ({sensor.sensor_type})")

    db.commit()
    print(f"\n  ✅ Structure créée : {len(all_sensors)} capteurs dans {len(all_cells)} cellules")
    return all_cells


def seed_analytics(db: Session):
    print("\n📊 Seeding Données Analytiques...")
    sensors = db.query(Sensor).filter(Sensor.deleted_at.is_(None)).all()

    if not sensors:
        print("  ⚠️  Aucun capteur trouvé.")
        return

    analytics_to_add = []
    total_days = 365

    for sensor in sensors:
        try:
            prefix = sensor.sensor_id[1:]
            analytic_type = AnalyticType.from_prefix(prefix)
        except (ValueError, IndexError):
            analytic_type = AnalyticType.AIR_TEMPERATURE

        if analytic_type in [AnalyticType.AIR_TEMPERATURE, AnalyticType.SOIL_TEMPERATURE]:
            base_value, amplitude, noise = 22.0, 6.0, 0.5
        elif analytic_type in [AnalyticType.AIR_HUMIDITY, AnalyticType.SOIL_HUMIDITY, AnalyticType.DEEP_SOIL_HUMIDITY]:
            base_value, amplitude, noise = 65.0, -10.0, 2.0
        elif analytic_type == AnalyticType.LIGHT:
            base_value, amplitude, noise = 50.0, 40.0, 5.0
        elif analytic_type == AnalyticType.BATTERY:
            base_value, amplitude, noise = 95.0, -5.0, 1.0
        else:
            continue

        # Générer une seule donnée par jour pour les 365 derniers jours
        for day in range(total_days):
            # Une seule donnée par jour, à midi.
            occurred_at = (datetime.now(UTC) - timedelta(days=day)).replace(hour=12, minute=0, second=0, microsecond=0)

            # Génération de valeur simplifiée pour un point de donnée quotidien.
            # Simule une variation saisonnière approximative.
            # Le facteur saisonnier varie de -1 (hiver) à +1 (été) sur l'année.
            seasonal_factor = -math.cos(2 * math.pi * day / 365)
            value = base_value + (amplitude * seasonal_factor) + random.uniform(-noise, noise)

            # Cas spécial pour la batterie pour simuler une décharge lente
            if analytic_type == AnalyticType.BATTERY:
                value = 100 - (day / total_days * 90) + random.uniform(-noise, noise)

            analytics_to_add.append(Analytic(
                sensor_id=sensor.id,
                sensor_code=sensor.sensor_id,
                analytic_type=analytic_type,
                value=round(max(0, value), 2),
                occurred_at=occurred_at,
            ))

    db.bulk_save_objects(analytics_to_add)
    db.commit()
    print(f"  ✅ {len(analytics_to_add)} points de données générés")


def seed_refresh_tokens(db: Session):
    print("\n🔑 Seeding Tokens de Rafraîchissement...")
    users = db.query(User).all()
    if not users:
        print("  ⚠️  Aucun utilisateur trouvé.")
        return
    for user in users:
        db.add(RefreshToken(
            token=str(uuid.uuid4()),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        ))
        print(f"  ✓ Token créé pour '{user.email}'")
    db.commit()


def seed_alerts(db: Session, cells: list[Cell]):
    """
    Seed des alertes et de quelques événements d'alerte d'exemple.
    On crée une alerte par type de capteur représentatif,
    associée à plusieurs cellules.
    """
    print("\n🔔 Seeding Alertes...")

    if not cells:
        print("  ⚠️  Aucune cellule disponible pour créer des alertes.")
        return

    # On prend les 3 premières cellules pour les associer aux alertes
    target_cells = cells[:3]
    cell_ids = [str(c.id) for c in target_cells]

    alerts_config = [
        {
            "title": "Alerte Température Air",
            "sensors": [
                {
                    "type": "air_temperature",
                    "index": 0,
                    "criticalRange": {"min": -5.0, "max": 40.0},
                    "warningRange": {"min": 0.0, "max": 35.0},
                }
            ],
            "warning_enabled": True,
        },
        {
            "title": "Alerte Humidité Sol",
            "sensors": [
                {
                    "type": "soil_humidity",
                    "index": 0,
                    "criticalRange": {"min": 10.0, "max": 90.0},
                    "warningRange": {"min": 20.0, "max": 80.0},
                }
            ],
            "warning_enabled": True,
        },
        {
            "title": "Alerte Sécheresse Profonde",
            "sensors": [
                {
                    "type": "deep_soil_humidity",
                    "index": 0,
                    "criticalRange": {"min": 0.0, "max": 20.0},
                    "warningRange": {"min": 20.0, "max": 35.0},
                }
            ],
            "warning_enabled": True,
        },
        {
            "title": "Alerte Multi-capteurs",
            "sensors": [
                {
                    "type": "light",
                    "index": 0,
                    "criticalRange": {"min": 10.0, "max": 90.0},
                    "warningRange": None,
                },
                {
                    "type": "air_humidity",
                    "index": 0,
                    "criticalRange": {"min": 5.0, "max": 95.0},
                    "warningRange": None,
                },
                {
                    "type": "soil_temperature",
                    "index": 0,
                    "criticalRange": {"min": 2.0, "max": 35.0},
                    "warningRange": None,
                }
            ],
            "warning_enabled": False,
        },
        {
            "title": "Alerte Batteries",
            "sensors": [
                {
                    "type": "battery",
                    "index": 0,
                    "criticalRange": {"min": 0, "max": 10.0},
                    "warningRange": {"min": 10.1, "max": 20.0},
                }
            ],
            "warning_enabled": True,
        },
    ]

    created_alerts: list[Alert] = []
    for config in alerts_config:
        alert = Alert(
            title=config["title"],
            is_active=True,
            warning_enabled=config["warning_enabled"],
            cell_ids=cell_ids,
            sensors=config["sensors"],
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        created_alerts.append(alert)
        print(f"  ✓ Alerte '{alert.title}' créée (ID: {alert.id})")

    # Désactiver la dernière alerte pour avoir de la variété
    created_alerts[-1].is_active = False
    db.commit()
    print(f"  • Alerte '{created_alerts[-1].title}' désactivée")

    # Seed de quelques événements d'alerte
    print("\n  📋 Seeding Événements d'Alerte...")
    seed_alert_events(db, created_alerts)

    print(f"\n  ✅ {len(created_alerts)} alertes créées")


def seed_alert_events(db: Session, alerts: list[Alert]):
    """
    Génère des événements d'alerte variés pour l'historique.
    Cette fonction modifie quelques données analytiques existantes pour qu'elles
    déclenchent des alertes, puis crée les événements correspondants pour
    assurer la cohérence des données de démo.
    """
    events_to_create = []

    # --- Helper pour créer un événement ---
    def create_event_from_analytic(
        alert: Alert,
        sensor_type: str,
        new_value: float,
        severity: SeverityEnum,
        days_ago: int,
        is_archived: bool
    ):
        # 1. Trouver une cellule et un capteur cibles
        if not alert.cell_ids:
            return None
        cell_id_str = alert.cell_ids[0]
        cell = db.query(Cell).filter(Cell.id == uuid.UUID(cell_id_str)).first()
        if not cell:
            return None
        
        sensor = db.query(Sensor).filter(Sensor.cell_id == cell.id, Sensor.sensor_type == sensor_type).first()
        if not sensor:
            return None

        # 2. Trouver un analytic à une date approximative et le modifier
        target_date = (datetime.now(UTC) - timedelta(days=days_ago)).date()
        analytic_to_modify = db.query(Analytic).filter(
            Analytic.sensor_id == sensor.id,
            func.date(Analytic.occurred_at) == target_date
        ).first()

        if not analytic_to_modify:
            # Si aucun analytic n'est trouvé pour ce jour, on ne peut pas créer l'événement
            print(f"    - AVERTISSEMENT: Aucun analytic trouvé pour {sensor_type} il y a {days_ago} jours. Impossible de créer l'événement.")
            return None

        # 3. Modifier la valeur et persister
        analytic_to_modify.value = new_value
        db.commit()
        db.refresh(analytic_to_modify)

        # 4. Créer l'événement d'alerte
        sensor_config = next((s for s in alert.sensors if s['type'] == sensor_type), None)
        if not sensor_config: 
            return None

        threshold_range = sensor_config['criticalRange']
        if severity == SeverityEnum.WARNING and sensor_config.get('warningRange'):
            threshold_range = sensor_config['warningRange']

        event = AlertEvent(
            alert_id=alert.id,
            alert_title=alert.title,
            cell_id=cell.id,
            cell_name=cell.name,
            cell_location=get_full_location_path_for_cell(cell),
            sensor_type=sensor_type,
            severity=severity,
            value=new_value,
            threshold_min=threshold_range['min'],
            threshold_max=threshold_range['max'],
            timestamp=analytic_to_modify.occurred_at,
            is_archived=is_archived,
        )
        return event

    # --- Configuration des événements à générer ---
    
    # Trouver les alertes spécifiques dont on a besoin
    temp_alert = next((a for a in alerts if any(s['type'] == 'air_temperature' for s in a.sensors)), None)
    humidity_alert = next((a for a in alerts if any(s['type'] == 'soil_humidity' for s in a.sensors)), None)

    if not temp_alert:
        print("  ⚠️  Impossible de trouver les alertes de température pour le seeding.")
        return
    if not humidity_alert:
        print("  ⚠️  Impossible de trouver les alertes d'humidité pour le seeding.")
        return

    # Définir les événements à créer
    event_definitions = [
        { "alert": temp_alert, "type": "air_temperature", "value": 44.2, "severity": SeverityEnum.CRITICAL, "days": 1, "archived": False },
        { "alert": temp_alert, "type": "air_temperature", "value": 36.8, "severity": SeverityEnum.WARNING, "days": 2, "archived": False },
        { "alert": humidity_alert, "type": "soil_humidity", "value": 7.3, "severity": SeverityEnum.CRITICAL, "days": 3, "archived": False },
        { "alert": temp_alert, "type": "air_temperature", "value": -6.1, "severity": SeverityEnum.CRITICAL, "days": 15, "archived": True },
        { "alert": humidity_alert, "type": "soil_humidity", "value": 92.5, "severity": SeverityEnum.CRITICAL, "days": 20, "archived": True },
    ]

    for definition in event_definitions:
        event = create_event_from_analytic(
            alert=definition["alert"],
            sensor_type=definition["type"],
            new_value=definition["value"],
            severity=definition["severity"],
            days_ago=definition["days"],
            is_archived=definition["archived"]
        )
        if event:
            events_to_create.append(event)
            status_label = "archivé" if event.is_archived else "actif"
            print(f"    • Événement [{event.severity.value}] {event.sensor_type} -> {event.value} ({status_label}) préparé.")

    if events_to_create:
        db.add_all(events_to_create)
        db.commit()
        print(f"    ✅ {len(events_to_create)} événements créés et liés à des analytics modifiés.")
    else:
        print("    ⚠️ Aucun événement n'a pu être créé.")


if __name__ == "__main__":
    seed()
