
from fastapi import HTTPException, status
import uuid
from typing import List

class CellNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cell not found",
        )

class ParentCellNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent cell not found",
        )

class InvalidDateRangeError(HTTPException):
    def __init__(self, detail: str = "The 'from' date cannot be after the 'to' date."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

class CellsNotFoundError(Exception):
    def __init__(self, not_found_ids: List[uuid.UUID]):
        self.not_found_ids = not_found_ids
        self.message = f"Les cellules avec les IDs suivants n'ont pas été trouvées : {', '.join(map(str, not_found_ids))}"
        super().__init__(self.message)