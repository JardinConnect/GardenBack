from fastapi import HTTPException, status

class SensorNotFoundError(HTTPException):
    def __init__(self, sensor_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capteur avec l'ID {sensor_id} introuvable."
        )

class InvalidDateRangeError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de fin doit être postérieure à la date de début."
        )

class InvalidAnalyticTypeError(HTTPException):
    def __init__(self, analytic_type: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type d'analytique '{analytic_type}' invalide. Types supportés: average, min, max, count, latest."
        )

class DataNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune donnée trouvée pour les critères spécifiés."
        )