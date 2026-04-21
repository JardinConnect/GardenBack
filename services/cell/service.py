from typing import List, Dict, Optional
import uuid
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
import services.alerts.service as alerts_service
import services.cell.repository as repositoryCell
from datetime import datetime
import services.area.repository as repositoryArea 
import services.cell.schemas as schemas
import services.cell.errors as errors
from db.models import Analytic as AnalyticModel, AnalyticType, Sensor as SensorModel
from services.mqtt.pending_acks import create_pending_ack, wait_for_ack, cancel_pending_ack
from services.mqtt.client import publish
from settings import settings

import json
import asyncio
from typing import AsyncGenerator
from db.models import User

def _create_default_sensors_for_cell(db: Session, cell_id: uuid.UUID) -> None:
    """
    Crée les capteurs par défaut pour une cellule nouvellement créée.
    """
    default_sensors = [
        {"sensor_id": "1TS", "sensor_type": "soil_temperature"},
        {"sensor_id": "1TA", "sensor_type": "air_temperature"},
        {"sensor_id": "1L", "sensor_type": "light"},
        {"sensor_id": "1HS", "sensor_type": "soil_humidity"},
        {"sensor_id": "1HA", "sensor_type": "air_humidity"},
        {"sensor_id": "2HS", "sensor_type": "deep_soil_humidity"},
        {"sensor_id": "1VB", "sensor_type": "volt_battery"},
        {"sensor_id": "1SB", "sensor_type": "status_battery"},
    ]

    for sensor_data in default_sensors:
        sensor = SensorModel(
            sensor_id=sensor_data["sensor_id"],
            sensor_type=sensor_data["sensor_type"],
            status="active",
            cell_id=cell_id,
        )
        db.add(sensor)


def create_cell(db: Session, cell_data: schemas.CellCreate, current_user: User, commit: bool = True) -> schemas.Cell:
    """
    Crée une nouvelle cellule (Cell) dans la base de données.
    """
    if cell_data.area_id:
        area = repositoryArea.get_by_id(db, cell_data.area_id)
        if not area:
            raise errors.ParentCellNotFoundError

    # On passe commit=False au repository pour gérer la transaction ici
    cell = repositoryCell.create_cell(db, cell_data, current_user, commit=False)

    # Créer les capteurs par défaut associés à la cellule
    _create_default_sensors_for_cell(db, cell.id)

    # Associer l'alerte de batterie par défaut à la nouvelle cellule
    alerts_service.associate_cell_to_default_battery_alert(db, cell.id)

    if commit:
        db.commit()
        # Re-fetch to get all relationships correctly loaded after commit
        return repositoryCell.get_cell_by_id(db, cell.id)

    return cell

def delete_cell(db: Session, cell_id: uuid.UUID) -> bool:
    """
    Supprime une cellule de la base de données.
    """
    return repositoryCell.delete_cell(db, cell_id)

def update_cell(db: Session, cell_id: uuid.UUID, cell_data: schemas.CellUpdate, current_user: User) -> schemas.Cell:
    """
    Met à jour une cellule de la base de données.
    """
    # Validate area if provided
    if cell_data.area_id:
        area = repositoryArea.get_by_id(db, cell_data.area_id)
        if not area:
            raise errors.ParentCellNotFoundError
    
    return repositoryCell.update_cell(db, cell_id, cell_data, current_user)

def get_cell(db: Session, cell_id: uuid.UUID, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> schemas.Cell:
    """
    Récupère une cellule de la base de données.
    """
    if from_date and to_date and from_date > to_date:
        raise errors.InvalidDateRangeError("La date de début (from) ne peut pas être postérieure à la date de fin (to).")

    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    analytics = get_all_analytics_for_cell(db, cell_id, from_date, to_date)
    cell.analytics = analytics
    return cell

def get_cells(db: Session) -> List[schemas.Cell]:
    """
    Récupère toutes les cellules de la base de données.
    """
    cells = repositoryCell.get_cells(db)
    for cell in cells:
        analytics = get_analytics_for_cell(db, cell.id)
        cell.analytics = analytics
    return cells


def get_analytics_for_cell(db: Session, cell_id: uuid.UUID) -> List[Dict[AnalyticType, AnalyticModel]]:
    """
    Récupère la dernière analytique de chaque type pour tous les capteurs d'une cellule.
    """
    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    
    sensor_ids = [sensor.id for sensor in cell.sensors]
    if not sensor_ids:
        return {}

    # Sous-requête pour trouver la dernière analytique de chaque type
    subquery = db.query(
        AnalyticModel.analytic_type,
        func.max(AnalyticModel.occurred_at).label('last_date')
    ).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    ).group_by(AnalyticModel.analytic_type).subquery()

    # Récupérer les analytiques correspondant à la sous-requête
    latest_analytics = db.query(AnalyticModel).join(
        subquery,
        and_(
            AnalyticModel.analytic_type == subquery.c.analytic_type,
            AnalyticModel.occurred_at == subquery.c.last_date
        )
    ).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    ).all()

    # Construire le dictionnaire
    latest_by_type = {a.analytic_type: [schemas.AnalyticSchema.model_validate(a)] for a in latest_analytics}
    return latest_by_type

def get_all_analytics_for_cell(db: Session, cell_id: uuid.UUID, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> Dict[AnalyticType, List[schemas.AnalyticSchema]]:
    cell = repositoryCell.get_cell_by_id(db, cell_id)
    if not cell:
        raise errors.CellNotFoundError
    
    sensor_ids = [sensor.id for sensor in cell.sensors]
    if not sensor_ids:
        return {}
    
    query = db.query(AnalyticModel).filter(
        AnalyticModel.sensor_id.in_(sensor_ids)
    )
    
    if from_date:
        query = query.filter(AnalyticModel.occurred_at >= from_date)
    if to_date:
        query = query.filter(AnalyticModel.occurred_at <= to_date)
    
    analytics = query.all()

    # Grouper par type et convertir en schémas
    analytics_by_type = {}
    for analytic in analytics:
        if analytic.analytic_type not in analytics_by_type:
            analytics_by_type[analytic.analytic_type] = []
        analytics_by_type[analytic.analytic_type].append(schemas.AnalyticSchema.model_validate(analytic))
    
    return analytics_by_type

def update_multiple_cells_settings(db: Session, settings_data: schemas.CellSettingsUpdate):
    """
    Logique métier pour mettre à jour les paramètres de plusieurs cellules.
    """
    # 1. Récupérer les cellules cibles
    cells_to_update = repositoryCell.get_cells_by_ids(db, settings_data.cell_ids)
    
    # 2. Vérifier que toutes les cellules demandées ont été trouvées
    found_ids = {cell.id for cell in cells_to_update}
    requested_ids = set(settings_data.cell_ids)
    
    if not_found_ids := requested_ids - found_ids:
        raise errors.CellsNotFoundError(list(not_found_ids))

    # 3. Préparer le dictionnaire de settings à appliquer
    settings_payload = {
        "daily_update_count": settings_data.daily_update_count,
        "update_times": settings_data.update_times,
        "measurement_frequency": settings_data.measurement_frequency,
    }

    # 3.5 Préparer le dictionnaire de settings IoT à appliquer
    device_send_interval = (24 / max(settings_data.daily_update_count, 1)) * 60 * 60
    settings_payload_iot = {
        "device.send_interval": device_send_interval,
        "power.sleep_interval": settings_data.measurement_frequency,
    }

    # 4. Mettre à jour le champ 'settings' de chaque cellule
    for cell in cells_to_update:
        if cell.settings is None:
            cell.settings = {}
        cell.settings.update(settings_payload)
        flag_modified(cell, "settings")
        try:
            payload = json.dumps({
                "uid": str(cell.deviceID),
                "data": settings_payload_iot,
            })
            publish(settings.MQTT_TOPIC_DEVICES_SETTINGS, payload)
            print(f"[MQTT][cell] Device {cell.deviceID} settings published: {payload}")
        except Exception as e:
            print(f"[MQTT][cell] Error publishing device settings: {e}")

    # 5. Appliquer la transaction
    db.commit()
 
 
async def _mock_mqtt_pairing_ack(ack_id: str) -> dict:
    """
    Simule la réponse d'un device IoT pour le processus de pairing.
    Retourne un dictionnaire qui imite la structure d'un ACK MQTT de pairing réussi.
    """
    await asyncio.sleep(2)  # Simule le délai réseau / scan
    device_uid = f"CELL-{uuid.uuid4().hex[:6].upper()}"
    return {
        "status": "ok",
        "uid": device_uid,
        "name": f"Cellule {device_uid}",
        "firmware_version": "1.0.0",
        "ack_id": ack_id,
    }

async def _mock_mqtt_refresh_ack(ack_id: str) -> dict:
    """
    Simule la réponse d'un device IoT pour le rafraîchissement des analytiques.
    """
    await asyncio.sleep(1)  # Simule un délai plus court pour le refresh
    return {"status": "OK", "message": "Analytics refreshed successfully (mocked)", "device_count": 3, "ack_id": ack_id}


async def refresh_all_analytics_stream(
    db: Session,
) -> AsyncGenerator[dict, None]:
    """
    Générateur SSE pour déclencher un rafraîchissement des analytiques
    sur tous les devices IoT et attendre leur acquittement.
 
    Émet dans l'ordre :
      - event:status  step:sending_command — envoi de la commande MQTT
      - event:status  step:waiting_ack     — en attente de l'ack des devices
      - event:completed step:completed     — ack reçu, commande traitée
    En cas d'erreur à n'importe quelle étape :
      - event:error step:failed
    """
 
    def _event(event_type: str, step: str, message: str, **extra) -> dict:
        """Helper interne — construit un dict compatible EventSourceResponse."""
        return {
            "event": event_type,
            "data": json.dumps({"step": step, "message": message, **extra}, default=str),
        }
 
    ack_id = str(uuid.uuid4())
 
    try:
        # ── Étape 1 : envoi de la commande MQTT ──────────────────────────
        yield _event("status", "sending_command", "Envoi de la commande de rafraîchissement des analytiques...")
 
        if settings.MOCK_MQTT:
            print(f"[MQTT Mock] Simulating refresh command for ack_id: {ack_id}")
            result = await _mock_mqtt_refresh_ack(ack_id)
        else:
            command_payload = json.dumps({
                "command": "instant_analytics",
                "ack_id": ack_id,
            })
            create_pending_ack(ack_id)
            publish(settings.MQTT_TOPIC_DEVICES_COMMAND, command_payload)
            # ── Étape 2 : attente de l'acquittement ──────────────────────────
            yield _event("status", "waiting_ack", "En attente de l'acquittement des devices...")
            result = await wait_for_ack(ack_id, timeout=30.0) # Augmentation du timeout pour plusieurs devices
 
        if result is None:
            yield _event("error", "timeout", "Les devices n'ont pas répondu dans le délai imparti.")
            return
 
        if result.get("status") != "OK":  # Vérification du statut "OK" comme spécifié
            error_msg = result.get("message", "Erreur inconnue des devices.")
            yield _event("error", "device_error", error_msg, device_response=result)
            return
 
        device_count = result.get("device_count", 0)
 
        # ── Étape 3 : succès ────────────────────────────────────────────
        yield _event(
            "completed",
            "completed",
            f"Rafraîchissement des analytiques terminé pour {device_count} device(s).",
            device_count=device_count,
            device_response=result,
        )
 
    except Exception as exc:
        cancel_pending_ack(ack_id)
        yield _event("error", "failed", str(exc))
async def pair_cell_stream(
    db: Session,
    current_user: User,
    area_id: Optional[uuid.UUID] = None,
) -> AsyncGenerator[dict, None]:
    """
    Générateur SSE pour le pairing d'une cellule IoT.
 
    Émet dans l'ordre :
      - event:status  step:scanning      — début du scan MQTT
      - event:status  step:device_found  — device détecté (données IoT)
      - event:status  step:creating      — écriture en base
      - event:completed step:completed   — cellule créée, payload complet
    En cas d'erreur à n'importe quelle étape :
      - rollback automatique de la transaction (annule l'insertion en base)
      - event:error step:failed
    """
 
    def _event(event_type: str, step: str, message: str, **extra) -> dict:
        """Helper interne — construit un dict compatible EventSourceResponse."""
        return {
            "event": event_type,
            "data": json.dumps({"step": step, "message": message, **extra}, default=str),
        }
    
    ack_id = str(uuid.uuid4())
 
    try:
        # ── Étape 1 : scan ────────────────────────────────────────────────
        yield _event("status", "scanning", "Recherche d'un device IoT en cours...")
 
        # ── Étape 2 : détection device ────────────────────────────────────
        if settings.MOCK_MQTT:
            print(f"[MQTT Mock] Simulating pairing scan for ack_id: {ack_id}")
            result = await _mock_mqtt_pairing_ack(ack_id)
        else:
            config_payload = json.dumps({
                "event" : "start", # MQTT Event
                "ack_id": ack_id,
            })
            create_pending_ack(ack_id)
            publish(settings.MQTT_TOPIC_PAIRING, config_payload)
            result = await wait_for_ack(ack_id, timeout=15.0)

        if result is None:
            yield _event("error", "timeout", "Le device n'a pas répondu dans le délai imparti.")
            return

        if result.get("status") != "ok":
            error_msg = result.get("message", "Erreur inconnue du device.")
            yield _event("error", "device_error", error_msg, device_response=result)
            return

        uid = result.get("uid")
        if not uid:
            yield _event("error", "device_error", "UID manquant dans la réponse du device.", device_response=result)
            return

        device_data = {
            "device_id": uid,
            "ack_id": ack_id,
            "status": result.get("status"),
        }

        yield _event(
            "status",
            "device_found",
            f"Device détecté : {device_data['device_id']}",
            device=device_data,
        )

        # ── Étape 3 : création en base ────────────────────────────────────
        yield _event("status", "creating", "Création de la cellule en base de données...")
 
        cell_data = schemas.CellCreate(
            name=uid,
            deviceID=uid,
            area_id=area_id
        )
        
        # On passe commit=False pour garder la transaction ouverte
        cell = create_cell(db, cell_data, current_user, commit=False)  # peut lever ParentCellNotFoundError
 
        cell_dto = schemas.CellDTO.from_cell(cell)
        
        # ── Étape 4 : Validation finale de la transaction ─────────────────
        db.commit()
        
        yield _event(
            "completed",
            "completed",
            "Cellule créée avec succès.",
            cell=cell_dto.model_dump(mode="json"),
        )
 
    except Exception as exc:
        # Le cancel_pending_ack est géré dans wait_for_ack.
        db.rollback()
        yield _event("error", "failed", str(exc))