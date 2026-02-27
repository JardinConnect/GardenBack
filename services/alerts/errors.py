from fastapi import HTTPException, status
from typing import List
import uuid


class AlertNotFoundError(HTTPException):
    def __init__(self, alert_id: uuid.UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerte '{alert_id}' non trouvée.",
        )


class AlertEventNotFoundError(HTTPException):
    def __init__(self, event_id: uuid.UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Événement d'alerte '{event_id}' non trouvé.",
        )


class AlertConflictError(HTTPException):
    """Levée quand overwriteExisting=False et que des conflits existent."""

    def __init__(self, conflicts: List[dict]):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "hasConflicts": True,
                "conflicts": conflicts,
            },
        )


class AlertValidationError(HTTPException):
    """Levée pour des erreurs de validation métier (ex : plage critique manquante)."""

    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )


class CellNotFoundError(HTTPException):
    def __init__(self, cell_id: uuid.UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cellule '{cell_id}' non trouvée.",
        )
