from fastapi import APIRouter, HTTPException, status

from services.network import service
from services.network.schemas import CurrentNetwork, NetworkInfo, ConnectRequest, ConnectResponse
from services.network.errors import ConnectFailedError, NetworkUnavailableError

router = APIRouter()


@router.get("/current", response_model=CurrentNetwork)
def get_current_network() -> CurrentNetwork:
    try:
        return service.get_current_network()
    except NetworkUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)


@router.get("/list", response_model=list[NetworkInfo])
def list_networks() -> list[NetworkInfo]:
    try:
        return service.list_networks()
    except NetworkUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.message)


@router.post("/connect", response_model=ConnectResponse)
def connect_network(body: ConnectRequest) -> ConnectResponse:
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
