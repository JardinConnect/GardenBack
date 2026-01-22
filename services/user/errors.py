from fastapi import HTTPException, status
from uuid import UUID

class UserNotFoundErrorID(HTTPException):
    def __init__(self, user_id: UUID):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur avec l'ID '{user_id}' est introuvable."
        )

class UserNotFoundErrorEmail(HTTPException):
    def __init__(self, user_email:str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Utilisateur avec l'email '{user_email}' est introuvable."
        )

class UserAlreadyExistsError(HTTPException):
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un utilisateur avec l'email '{email}' existe déjà."
        )
