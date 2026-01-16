from fastapi import HTTPException, status

FarmStatsError = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Could not retrieve farm statistics.",
)