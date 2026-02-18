from services.network.providers import LinuxNmcliProvider
from services.network.schemas import CurrentNetwork, NetworkInfo, ConnectResponse
from services.network.errors import ConnectFailedError

_provider = LinuxNmcliProvider()


def get_current_network() -> CurrentNetwork:
    return _provider.get_current_network()


def list_networks() -> list[NetworkInfo]:
    return _provider.list_networks()


def connect(ssid: str, password: str | None = None, hidden: bool = False) -> ConnectResponse:
    success, message = _provider.connect(ssid, password=password, hidden=hidden)
    return ConnectResponse(success=success, message=message, ssid=ssid)
