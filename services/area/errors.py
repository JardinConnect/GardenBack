from fastapi import HTTPException, status

AreaNotFoundError = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Area not found",
)