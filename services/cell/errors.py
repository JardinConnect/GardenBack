from fastapi import HTTPException, status

CellNotFoundError = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Cell not found",
)

ParentCellNotFoundError = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Parent cell not found",
)