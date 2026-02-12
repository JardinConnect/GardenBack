from fastapi import APIRouter, Depends, Path, status, HTTPException
import uuid
from typing import List
from sqlalchemy.orm import Session

from .schemas import Area, AreaCreate, AreaUpdate
from . import service
from .errors import AreaNotFoundError, ParentAreaNotFoundError
from db.database import get_db
from services.auth.bearer import JWTBearer

router = APIRouter()

@router.get("/", response_model=List[Area], dependencies=[Depends(JWTBearer())])
def get_all_areas(db: Session = Depends(get_db)) -> List[Area]:
    """
    Récupère toutes les zones de jardin sous forme d'arborescence.

    Retourne une liste des zones racines (celles sans parent), chacune contenant
    ses sous-zones, cellules et analytiques agrégées.
    """
    return service.get_all_areas_with_analytics(db)


@router.post("/", response_model=Area, status_code=status.HTTP_201_CREATED, dependencies=[Depends(JWTBearer())])
def create_area(
    area_data: AreaCreate,
    db: Session = Depends(get_db),
) -> Area:
    """
    Crée une nouvelle zone de jardin.

    - **area_data**: Données de la nouvelle zone à créer.
        - `name`: Nom de la zone (obligatoire).
        - `color`: Couleur hexadécimale pour l'affichage (ex: "#FF5733").
        - `parent_id`: (Optionnel) ID de la zone parente.
        - `is_tracked`: (Optionnel) Indique si la zone doit être suivie pour les analyses. Par défaut à `false`.

    **Erreurs possibles :**
    - `404 Not Found`: Si le `parent_id` fourni ne correspond à aucune zone existante.
    """
    try:
        return service.create_area(db, area_data)
    except ParentAreaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{area_id}", response_model=Area, dependencies=[Depends(JWTBearer())])
def update_area(
    area_data: AreaUpdate,
    area_id: uuid.UUID = Path(..., title="The ID of the area to update"),
    db: Session = Depends(get_db),
) -> Area:
    """
    Met à jour une zone.

    - **area_id**: L'ID de la zone à mettre à jour.
    - **area_data**: Données à mettre à jour. Seuls les champs fournis seront modifiés.
        - `name`: Nouveau nom de la zone.
        - `color`: Nouvelle couleur hexadécimale.
        - `parent_id`: Nouvel ID de la zone parente. Mettre à `null` pour la déplacer à la racine.
        - `is_tracked`: Indique si la zone doit être suivie pour les analyses.

    **Erreurs possibles :**
    - `404 Not Found`: Si l'ID de la zone ou le `parent_id` fourni n'existe pas.
    - `400 Bad Request`: Si une tentative de créer une dépendance cyclique est détectée (ex: déplacer une zone dans un de ses propres enfants).
    """
    try:
        updated_area = service.update_area(db, area_id, area_data)
        return updated_area
    except (AreaNotFoundError, ParentAreaNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        # Capturer les erreurs de validation de la logique métier (ex: dépendance cyclique)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(JWTBearer())])
def delete_area(
    area_id: uuid.UUID = Path(..., title="The ID of the area to delete"),
    db: Session = Depends(get_db),
) -> None:
    """
    Supprime une zone de jardin et toutes ses sous-zones.

    - **area_id**: L'ID de la zone à supprimer.
    - Les sous-zones sont supprimées en cascade.
    - Les cellules qui étaient dans les zones supprimées ne sont PAS supprimées,
      mais sont détachées (leur `area_id` devient `null`).

    **Erreurs possibles :**
    - `404 Not Found`: Si l'ID de la zone n'existe pas.
    """
    try:
        service.delete_area(db, area_id)
    except AreaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return None

@router.get("/{area_id}", response_model=Area, dependencies=[Depends(JWTBearer())])
def get_area(
    area_id: uuid.UUID = Path(..., title="The ID of the area to get"),
    db: Session = Depends(get_db),
) -> Area:
    """
    Récupère une zone de jardin spécifique par son ID, avec toute sa hiérarchie et les moyennes analytiques.

    - **area_id**: L'ID de la zone à récupérer.
    - La réponse inclut les sous-zones imbriquées et un résumé des données analytiques
      des 7 derniers jours pour la zone et toutes ses descendantes.

    **Erreurs possibles :**
    - `404 Not Found`: Si l'ID de la zone n'existe pas.
    """
    area = service.get_area_with_analytics(db, area_id)
    if not area:
        # Le service retourne None si la zone n'est pas trouvée.
        # Nous levons l'exception HTTP ici pour être explicite.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Area with id {area_id} not found")
    return area
