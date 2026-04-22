from pydantic import BaseModel
from typing import Optional


class CurrentNetwork(BaseModel):
    connected: bool
    ssid: Optional[str] = None
    signal: Optional[int] = None
    security: Optional[str] = None
    interface: str
    ip_address: Optional[str] = None
    gateway: Optional[str] = None
    mac_address: Optional[str] = None


class NetworkInfo(BaseModel):
    ssid: str
    signal: int
    security: str
    frequency: Optional[int] = None
    channel: Optional[int] = None


class ConnectRequest(BaseModel):
    ssid: str
    password: Optional[str] = None
    hidden: bool = False


class ConnectResponse(BaseModel):
    success: bool
    message: str
    ssid: Optional[str] = None


class TailscaleAuthStatus(BaseModel):
    """État d’auth Tailscale via LocalAPI (/localapi/v0/status)."""

    auth_url: Optional[str] = None
    backend_state: Optional[str] = None
