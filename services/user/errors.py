from fastapi import HTTPException, status

class UserNotFoundErrorID(HTTPException):
    def __init__(self, user_id:int):
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
