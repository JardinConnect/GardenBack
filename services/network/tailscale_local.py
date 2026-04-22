import json
import os
from typing import Any

import httpx

from settings import settings
from services.network.errors import TailscaleBadResponseError, TailscaleUnavailableError
from services.network.schemas import TailscaleAuthStatus

_LOCALAPI_STATUS_URL = "http://local-tailscaled.sock/localapi/v0/status"
_TIMEOUT_SEC = 3.0


def _mock_status_payload() -> dict[str, Any]:
    """Réponse minimale lorsque MOCK_TAILSCALE est actif (pas d’appel socket)."""
    return {"AuthURL": "", "BackendState": "Running"}


def fetch_tailscale_status_raw() -> dict[str, Any]:
    """
    Appelle la LocalAPI Tailscale GET /localapi/v0/status (JSON brut).
    """
    if settings.MOCK_TAILSCALE:
        return _mock_status_payload()

    if not os.path.exists(settings.TAILSCALE_SOCKET):
        raise TailscaleUnavailableError(
            "Socket Tailscale introuvable (tailscaled installé et démarré ?)."
        )

    transport = httpx.HTTPTransport(uds=settings.TAILSCALE_SOCKET)
    try:
        with httpx.Client(transport=transport, timeout=_TIMEOUT_SEC) as client:
            resp = client.get(_LOCALAPI_STATUS_URL)
    except (httpx.ConnectError, OSError) as exc:
        raise TailscaleUnavailableError(
            f"Impossible de contacter tailscaled: {exc}"
        ) from exc

    if resp.status_code == 403:
        raise TailscaleUnavailableError(
            "Accès à la LocalAPI Tailscale refusé (droits sur le socket ?)."
        )
    if resp.status_code != 200:
        raise TailscaleBadResponseError(
            f"LocalAPI Tailscale status HTTP {resp.status_code}."
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise TailscaleBadResponseError(
            "Réponse LocalAPI Tailscale invalide (JSON)."
        ) from exc

    if not isinstance(data, dict):
        raise TailscaleBadResponseError(
            "Réponse LocalAPI Tailscale invalide (objet JSON attendu)."
        )
    return data


def get_tailscale_auth_status() -> TailscaleAuthStatus:
    data = fetch_tailscale_status_raw()
    raw_auth = data.get("AuthURL")
    auth_url: str | None
    if raw_auth is None or (isinstance(raw_auth, str) and not raw_auth.strip()):
        auth_url = None
    elif isinstance(raw_auth, str):
        auth_url = raw_auth
    else:
        raise TailscaleBadResponseError("Champ AuthURL inattendu dans la réponse.")

    raw_backend = data.get("BackendState")
    backend_state: str | None
    if raw_backend is None or (isinstance(raw_backend, str) and not raw_backend):
        backend_state = None
    elif isinstance(raw_backend, str):
        backend_state = raw_backend
    else:
        backend_state = str(raw_backend)

    return TailscaleAuthStatus(auth_url=auth_url, backend_state=backend_state)
