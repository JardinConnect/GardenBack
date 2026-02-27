from unittest.mock import patch

from services.network.schemas import CurrentNetwork, NetworkInfo, ConnectResponse


class TestGetCurrentNetworkAccessibleWithoutAuth:
    @patch("services.network.service.get_current_network")
    def test_returns_200_without_authorization_header(self, mock_get_current, client):
        mock_get_current.return_value = CurrentNetwork(
            connected=False,
            interface="wlan0",
        )
        response = client.get("/network/current")
        assert response.status_code == 200


class TestGetListAccessibleWithoutAuth:
    @patch("services.network.service.list_networks")
    def test_returns_200_without_authorization_header(self, mock_list, client):
        mock_list.return_value = []
        response = client.get("/network/list")
        assert response.status_code == 200


class TestPostConnectAccessibleWithoutAuth:
    @patch("services.network.service.connect")
    def test_returns_200_without_authorization_header(self, mock_connect, client):
        mock_connect.return_value = ConnectResponse(
            success=True,
            message="Connecté",
            ssid="TestNet",
        )
        response = client.post(
            "/network/connect",
            json={"ssid": "TestNetwork"},
        )
        assert response.status_code == 200
