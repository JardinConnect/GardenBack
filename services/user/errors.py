class UserAlreadyExistsError(Exception):
    """Levée lorsqu'un utilisateur avec cet email existe déjà."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"L'utilisateur avec l'email '{email}' existe déjà.")

class UserNotFoundErrorID(Exception):
    """Levée lorsqu'un utilisateur n'est pas trouvé par son ID."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"L'utilisateur avec l'ID '{user_id}' n'a pas été trouvé.")

class InvalidPasswordError(Exception):
    """Levée lorsque le mot de passe actuel fourni est incorrect."""
    def __init__(self, message: str = "Le mot de passe actuel est incorrect."):
        self.message = message
        super().__init__(self.message)