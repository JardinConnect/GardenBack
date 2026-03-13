from fastapi import HTTPException, status

FarmStatsError = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Could not retrieve farm statistics.",
)

class FarmAlreadyExistsError(Exception):
    """Levée lorsque la ferme a déjà été configurée."""
    def __init__(self, message: str = "La ferme a déjà été configurée. Cette opération ne peut être effectuée qu'une seule fois."):
        self.message = message
        super().__init__(self.message)