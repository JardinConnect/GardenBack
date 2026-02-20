import pytest
from unittest.mock import patch

from services.network.errors import NetworkUnavailableError, ConnectFailedError


class TestGetCurrentNetworkErrors:
    @patch("services.network.service.get_current_network")
    def test_returns_503_when_network_unavailable(
        self, mock_get_current, client, headers_admin
    ):
        mock_get_current.side_effect = NetworkUnavailableError("nmcli not found")
        response = client.get("/network/current", headers=headers_admin)
        assert response.status_code == 503
        body = response.json()
        assert "detail" in body or "error" in body
        if "error" in body:
            assert "message" in body["error"] or "detail" in str(body)


class TestGetListErrors:
    @patch("services.network.service.list_networks")
    def test_returns_503_when_network_unavailable(
        self, mock_list, client, headers_admin
    ):
        mock_list.side_effect = NetworkUnavailableError("timeout")
        response = client.get("/network/list", headers=headers_admin)
        assert response.status_code == 503


class TestPostConnectErrors:
    @patch("services.network.service.connect")
    def test_returns_502_when_connect_fails(
        self, mock_connect, client, headers_admin
    ):
        mock_connect.side_effect = ConnectFailedError("Wrong password")
        response = client.post(
            "/network/connect",
            json={"ssid": "MyWiFi", "password": "wrong"},
            headers=headers_admin,
        )
        assert response.status_code == 502
        body = response.json()
        assert "detail" in body or "error" in body

    @patch("services.network.service.connect")
    def test_returns_503_when_network_unavailable(
        self, mock_connect, client, headers_admin
    ):
        mock_connect.side_effect = NetworkUnavailableError("nmcli not found")
        response = client.post(
            "/network/connect",
            json={"ssid": "MyWiFi"},
            headers=headers_admin,
        )
        assert response.status_code == 503

    def test_returns_422_when_ssid_missing(self, client, headers_admin):
        response = client.post(
            "/network/connect",
            json={"password": "secret"},
            headers=headers_admin,
        )
        assert response.status_code == 422
