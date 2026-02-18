from fastapi import APIRouter, Depends, HTTPException, status

from services.network import service
from services.network.schemas import CurrentNetwork, NetworkInfo, ConnectRequest, ConnectResponse
from services.network.errors import ConnectFailedError, NetworkUnavailableError
from services.auth.dependencies import get_current_user
from db.models import User, RoleEnum

router = APIRouter()


@router.get("/current", response_model=CurrentNetwork)
def get_current_network(current_user: User = Depends(get_current_user)) -> CurrentNetwork:
    try:
        return service.get_current_network()
    except NetworkUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)


@router.get("/list", response_model=list[NetworkInfo])
def list_networks(current_user: User = Depends(get_current_user)) -> list[NetworkInfo]:
    try:
        return service.list_networks()
    except NetworkUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)


@router.post("/connect", response_model=ConnectResponse)
def connect_network(
    body: ConnectRequest,
    current_user: User = Depends(get_current_user),
) -> ConnectResponse:
    if current_user.role not in [RoleEnum.ADMIN, RoleEnum.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les administrateurs peuvent changer le réseau WiFi.",
        )
    try:
        return service.connect(
            ssid=body.ssid,
            password=body.password,
            hidden=body.hidden,
        )
    except ConnectFailedError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=e.message)
    except NetworkUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)
