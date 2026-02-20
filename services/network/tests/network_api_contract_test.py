import pytest
from unittest.mock import patch

from services.network.schemas import CurrentNetwork, NetworkInfo, ConnectResponse


class TestGetCurrentNetworkContract:
    @patch("services.network.service.get_current_network")
    def test_returns_200_and_valid_schema_when_connected(
        self, mock_get_current, client, headers_admin
    ):
        mock_get_current.return_value = CurrentNetwork(
            connected=True,
            ssid="MyWiFi",
            signal=75,
            security="WPA2",
            interface="wlan0",
            ip_address="192.168.1.10",
            gateway="192.168.1.1",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        response = client.get("/network/current", headers=headers_admin)
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["ssid"] == "MyWiFi"
        assert data["signal"] == 75
        assert data["interface"] == "wlan0"
        CurrentNetwork(**data)

    @patch("services.network.service.get_current_network")
    def test_returns_200_and_valid_schema_when_not_connected(
        self, mock_get_current, client, headers_admin
    ):
        mock_get_current.return_value = CurrentNetwork(
            connected=False,
            interface="wlan0",
        )
        response = client.get("/network/current", headers=headers_admin)
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert data["ssid"] is None
        assert data["interface"] == "wlan0"
        CurrentNetwork(**data)


class TestGetListContract:
    @patch("services.network.service.list_networks")
    def test_returns_200_and_valid_schema_list(
        self, mock_list, client, headers_admin
    ):
        mock_list.return_value = [
            NetworkInfo(ssid="Net1", signal=80, security="WPA2"),
            NetworkInfo(ssid="Net2", signal=50, security="open", frequency=2437),
        ]
        response = client.get("/network/list", headers=headers_admin)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        for item in data:
            NetworkInfo(**item)

    @patch("services.network.service.list_networks")
    def test_returns_200_empty_list(self, mock_list, client, headers_admin):
        mock_list.return_value = []
        response = client.get("/network/list", headers=headers_admin)
        assert response.status_code == 200
        assert response.json() == []


class TestPostConnectContract:
    @patch("services.network.service.connect")
    def test_returns_200_and_valid_schema_on_success(
        self, mock_connect, client, headers_admin
    ):
        mock_connect.return_value = ConnectResponse(
            success=True,
            message="Connecté à MyWiFi",
            ssid="MyWiFi",
        )
        response = client.post(
            "/network/connect",
            json={"ssid": "MyWiFi", "password": "secret"},
            headers=headers_admin,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert data["ssid"] == "MyWiFi"
        ConnectResponse(**data)

    @patch("services.network.service.connect")
    def test_accepts_hidden_flag(self, mock_connect, client, headers_superadmin):
        mock_connect.return_value = ConnectResponse(
            success=True,
            message="Connecté",
            ssid="HiddenNet",
        )
        response = client.post(
            "/network/connect",
            json={"ssid": "HiddenNet", "hidden": True},
            headers=headers_superadmin,
        )
        assert response.status_code == 200
        mock_connect.assert_called_once()
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["hidden"] is True
