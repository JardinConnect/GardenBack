from unittest.mock import patch

from services.network.errors import TailscaleBadResponseError, TailscaleUnavailableError
from services.network.schemas import TailscaleAuthStatus


class TestGetTailscaleContract:
    @patch("services.network.router.tailscale_local.get_tailscale_auth_status")
    def test_returns_200_with_auth_url_when_pending_login(self, mock_status, client):
        mock_status.return_value = TailscaleAuthStatus(
            auth_url="https://login.tailscale.com/a/xxxxxxxxxxxxxxxx",
            backend_state="NeedsLogin",
        )
        response = client.get("/api/network/tailscale")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_url"] == "https://login.tailscale.com/a/xxxxxxxxxxxxxxxx"
        assert data["backend_state"] == "NeedsLogin"
        TailscaleAuthStatus(**data)

    @patch("services.network.router.tailscale_local.get_tailscale_auth_status")
    def test_returns_200_with_null_auth_url_when_connected(self, mock_status, client):
        mock_status.return_value = TailscaleAuthStatus(
            auth_url=None,
            backend_state="Running",
        )
        response = client.get("/api/network/tailscale")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_url"] is None
        assert data["backend_state"] == "Running"
        TailscaleAuthStatus(**data)

    @patch("services.network.router.tailscale_local.get_tailscale_auth_status")
    def test_returns_503_when_tailscale_unavailable(self, mock_status, client):
        mock_status.side_effect = TailscaleUnavailableError("Socket introuvable.")
        response = client.get("/api/network/tailscale")
        assert response.status_code == 503
        body = response.json()
        assert body["error"]["message"] == "Socket introuvable."

    @patch("services.network.router.tailscale_local.get_tailscale_auth_status")
    def test_returns_502_on_bad_tailscale_response(self, mock_status, client):
        mock_status.side_effect = TailscaleBadResponseError("Réponse invalide.")
        response = client.get("/api/network/tailscale")
        assert response.status_code == 502
        assert response.json()["error"]["message"] == "Réponse invalide."
