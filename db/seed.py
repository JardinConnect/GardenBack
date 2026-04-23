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
            name="Plume de courgette",
            address="95 Chemin du Gué Nantais",
            zip_code="44240",
            city="La Chapelle-sur-Erdre",
            phone_number="0683654823"
        ))
        db.commit()
        farm = db.query(Farm).first()
        print(f"  ✓ Ferme '{farm.name}' créée.")

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
        {"first_name": "Fanny", "last_name": "Lerou", "email": "fanny@yahoo.com", "phone_number": "0600000000", "password": "admin1234", "role": RoleEnum.SUPERADMIN},
        {"first_name": "Florian", "last_name": "Confit", "email": "florianconfit@gmail.com", "phone_number": "0600000000", "password": "user1234", "role": RoleEnum.ADMIN},
        {"first_name": "Guillaume", "last_name": "Lacha", "email": "lachaguillaume@gmail.com", "phone_number": "0600000000", "password": "saiso1234", "role": RoleEnum.EMPLOYEES},
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
 
    admin_user = db.query(User).filter(User.email == "florianconfit@gmail.com").first()
    if not admin_user:
        raise Exception("Admin user not found. Cannot seed areas without an originator.")
    admin_user_id = admin_user.id
 
    # --- Création de la nouvelle hiérarchie ---
 
    # Espaces (Niveau 1)
    print("\n  📍 Création des Espaces (Niveau 1)...")
    espace_1 = Area(name="Espace_1", color="#4682B4", originator_id=admin_user_id, updater_id=admin_user_id)
    espace_2 = Area(name="Espace_2", color="#6A5ACD", originator_id=admin_user_id, updater_id=admin_user_id)
    bi_1 = Area(name="Bi_1", color="#8A2BE2", originator_id=admin_user_id, updater_id=admin_user_id)
    bi_2 = Area(name="Bi_2", color="#9932CC", originator_id=admin_user_id, updater_id=admin_user_id)
    bi_3 = Area(name="Bi_3", color="#BA55D3", originator_id=admin_user_id, updater_id=admin_user_id)
    espace_3 = Area(name="Espace_3", color="#DDA0DD", originator_id=admin_user_id, updater_id=admin_user_id)
 
    root_areas = [espace_1, espace_2, bi_1, bi_2, bi_3, espace_3]
    db.add_all(root_areas)
    db.commit()
    for area in root_areas:
        db.refresh(area)
        print(f"    ✓ '{area.name}'")
 
    all_leaf_areas = []
 
    # Jardins (Niveau 2) sous Espace_1 et Espace_2
    print("\n  📍 Création des Jardins (Niveau 2)...")
    jardins = []
    for i in range(1, 5):
        jardin = Area(name=f"Jardin_{i}", color="#3CB371", parent_id=espace_1.id, originator_id=admin_user_id, updater_id=admin_user_id)
        jardins.append(jardin)
    for i in range(5, 9):
        jardin = Area(name=f"Jardin_{i}", color="#2E8B57", parent_id=espace_2.id, originator_id=admin_user_id, updater_id=admin_user_id)
        jardins.append(jardin)
 
    db.add_all(jardins)
    db.commit()
    for jardin in jardins:
        db.refresh(jardin)
        print(f"    ✓ '{jardin.name}'")
 
    # Planches (Niveau 3) sous les Jardins
    print("\n  📍 Création des Planches (Niveau 3)...")
    for i, jardin in enumerate(jardins, 1):
        planches = []
        for j in range(1, 11):
            planche = Area(name=f"Planche_{i}-{j}", color="#FFD700", parent_id=jardin.id, originator_id=admin_user_id, updater_id=admin_user_id)
            planches.append(planche)
        db.add_all(planches)
        db.commit()
        for planche in planches:
            db.refresh(planche)
            all_leaf_areas.append(planche)
        print(f"    ✓ 10 planches créées pour '{jardin.name}'")
 
    # Bi_Planches (Niveau 2) sous Bi_1, Bi_2, Bi_3
    print("\n  📍 Création des Bi_Planches (Niveau 2)...")
    bi_parents = [bi_1, bi_2, bi_3]
    for i, bi_parent in enumerate(bi_parents, 1):
        bi_planches = []
        for j in range(1, 15):
            bi_planche = Area(name=f"Bi_Planche_{i}-{j}", color="#FF69B4", parent_id=bi_parent.id, originator_id=admin_user_id, updater_id=admin_user_id)
            bi_planches.append(bi_planche)
        db.add_all(bi_planches)
        db.commit()
        for bi_planche in bi_planches:
            db.refresh(bi_planche)
            all_leaf_areas.append(bi_planche)
        print(f"    ✓ 14 bi_planches créées pour '{bi_parent.name}'")
 
    # Cellules & capteurs
    print("\n  📦 Création des cellules et capteurs...")
    # On ne peuple que quelques zones pour garder le seed rapide et les données de démo gérables.
    cells_to_create_in = all_leaf_areas[0:2] + all_leaf_areas[10:12]  # e.g., Planche_1-1, 1-2, 2-1, 2-2
 
    all_cells: list[Cell] = []
    all_sensors: list[Sensor] = []
 
    cell_counter = 1
    for area in cells_to_create_in:
        print(f"\n    📍 Area '{area.name}':")
        # Créer 1 cellule par zone pour la simplicité
        cell_name = f"Cellule principale - {area.name}"
        cell = Cell(name=cell_name, area_id=area.id, deviceID=f"SEED-DEVICE-{cell_counter}")
        cell_counter += 1
        db.add(cell)
        db.commit()
        db.refresh(cell)
        all_cells.append(cell)
        print(f"      ✓ Cellule '{cell.name}' (ID: {cell.id})")
 
        # Ajouter des capteurs
        sensors_config = [
            {"sensor_id": "1TA", "type": "air_temperature"},
            {"sensor_id": "1HA", "type": "air_humidity"},
            {"sensor_id": "1L", "type": "light"},
            {"sensor_id": "1TS", "type": "soil_temperature"},
            {"sensor_id": "1HS", "type": "soil_humidity"},
            {"sensor_id": "1DHS", "type": "deep_soil_humidity"},
            {"sensor_id": "1VB", "type": "battery_voltage"},
            {"sensor_id": "1SB", "type": "battery_soc"},
        ]
        for sensor_config in sensors_config:
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
    total_days = 60  # On génère des données pour les 2 derniers mois
    hours_step = 4   # Une donnée toutes les 4 heures pour plus de granularité

    now = datetime.now(UTC)

    for sensor in sensors:
        try:
            # Logique plus robuste pour extraire le préfixe (ex: "1TA" -> "TA", "10L" -> "L")
            prefix = ''.join(c for c in sensor.sensor_id if c.isalpha())
            analytic_type = AnalyticType.from_prefix(prefix)
        except (ValueError, IndexError):
            print(f"  ⚠️  Impossible de déterminer le type d'analytique pour le capteur ID '{sensor.sensor_id}'. On ignore.")
            continue

        # Paramètres pour la génération de données
        if analytic_type in [AnalyticType.AIR_TEMPERATURE, AnalyticType.SOIL_TEMPERATURE]:
            base_value, seasonal_amp, daily_amp, noise = 15.0, 10.0, 5.0, 0.5
        elif analytic_type in [AnalyticType.AIR_HUMIDITY, AnalyticType.SOIL_HUMIDITY, AnalyticType.DEEP_SOIL_HUMIDITY]:
            base_value, seasonal_amp, daily_amp, noise = 65.0, -15.0, -10.0, 2.0
        elif analytic_type == AnalyticType.LIGHT:
            base_value, seasonal_amp, daily_amp, noise = 0, 0, 80.0, 5.0
        elif analytic_type == AnalyticType.BATTERY:
            base_value, seasonal_amp, daily_amp, noise = 100.0, 0, 0, 0.5
        else:
            continue

        # Itérer du plus ancien (il y a 60 jours) au plus récent (aujourd'hui)
        for day_ago in range(total_days - 1, -1, -1):
            for hour_offset in range(0, 24, hours_step):
                occurred_at = (now - timedelta(days=day_ago)).replace(hour=hour_offset, minute=0, second=0, microsecond=0)

                # Variation saisonnière (basée sur le jour de l'année)
                day_of_year = occurred_at.timetuple().tm_yday
                seasonal_factor = -math.cos(2 * math.pi * day_of_year / 365)

                # Variation journalière (basée sur l'heure)
                daily_factor = -math.cos(2 * math.pi * hour_offset / 24)

                value = base_value + (seasonal_amp * seasonal_factor) + random.uniform(-noise, noise)

                # Ajouter la variation journalière
                if daily_amp != 0:
                    value += (daily_amp * daily_factor)

                # Pas de lumière la nuit
                if analytic_type == AnalyticType.LIGHT and (hour_offset < 6 or hour_offset > 20):
                    value = random.uniform(0, 2)

                # Décharge lente de la batterie
                if analytic_type == AnalyticType.BATTERY:
                    days_since_start = (now - occurred_at).days
                    value = 100 - (days_since_start / 365 * 90) + random.uniform(-noise, noise)

                analytics_to_add.append(Analytic(
                    sensor_id=sensor.id,
                    sensor_code=sensor.sensor_id,
                    analytic_type=analytic_type,
                    value=round(max(0, value), 2),
                    occurred_at=occurred_at,
                ))

    db.bulk_save_objects(analytics_to_add)
    db.commit()
    print(f"  ✅ {len(analytics_to_add)} points de données générés sur les {total_days} derniers jours.")


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
        cell_id: uuid.UUID,
        sensor_type: str,
        new_value: float,
        severity: SeverityEnum,
        days_ago: int,
        is_archived: bool
    ):
        # 1. Trouver la cellule et le capteur cibles
        cell = db.query(Cell).filter(Cell.id == cell_id).first()
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
            # print(f"    - AVERTISSEMENT: Aucun analytic trouvé pour {sensor_type} il y a {days_ago} jours. Impossible de créer l'événement.")
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
    print("  Génération d'événements aléatoires sur les 2 derniers mois...")

    # Boucler sur les 60 derniers jours
    for days_ago in range(59, 0, -1):
        # 7 chances sur 10 de générer un événement pour un jour donné
        if random.random() > 0.7:
            continue

        # Choisir une alerte active au hasard
        active_alerts = [a for a in alerts if a.is_active and a.sensors and a.cell_ids]
        if not active_alerts:
            continue
        target_alert = random.choice(active_alerts)
            
        # Choisir un capteur et une cellule au hasard parmi ceux de l'alerte
        sensor_config = random.choice(target_alert.sensors)
        cell_id_str = random.choice(target_alert.cell_ids)
        sensor_type = sensor_config['type']

        # Décider si c'est un événement critique ou d'avertissement
        is_warning = target_alert.warning_enabled and sensor_config.get('warningRange') and random.random() > 0.5
        severity = SeverityEnum.WARNING if is_warning else SeverityEnum.CRITICAL
        
        threshold_range = sensor_config.get('warningRange') if is_warning else sensor_config.get('criticalRange')
        if not threshold_range:
            continue
        
        # Générer une valeur en dehors des seuils
        if random.random() > 0.5: # Déclencher au-dessus du max
            value = threshold_range['max'] + random.uniform(1, 5)
        else: # Déclencher en dessous du min
            value = threshold_range['min'] - random.uniform(1, 5)
            
        # S'assurer que la valeur n'est pas négative pour certains types
        if sensor_type in ['light', 'battery', 'soil_humidity', 'deep_soil_humidity']:
            value = max(0, value)

        # Les événements plus anciens sont plus susceptibles d'être archivés
        is_archived = days_ago > 10 and random.random() > 0.3

        event = create_event_from_analytic(
            alert=target_alert,
            cell_id=uuid.UUID(cell_id_str),
            sensor_type=sensor_type,
            new_value=round(value, 2),
            severity=severity,
            days_ago=days_ago,
            is_archived=is_archived
        )
        
        if event:
            events_to_create.append(event)

    if events_to_create:
        db.add_all(events_to_create)
        db.commit()
        print(f"    ✅ {len(events_to_create)} événements aléatoires créés et liés à des analytics modifiés.")
    else:
        print("    ⚠️ Aucun événement aléatoire n'a pu être créé.")


if __name__ == "__main__":
    seed()
