
from fastapi import HTTPException, status

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