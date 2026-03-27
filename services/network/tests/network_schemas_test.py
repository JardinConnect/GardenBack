import pytest
from pydantic import ValidationError

from services.network.schemas import (
    CurrentNetwork,
    NetworkInfo,
    ConnectRequest,
    ConnectResponse,
)


class TestCurrentNetwork:
    def test_accepts_valid_connected_network(self):
        data = {
            "connected": True,
            "ssid": "MyWiFi",
            "signal": 75,
            "security": "WPA2",
            "interface": "wlan0",
            "ip_address": "192.168.1.10",
            "gateway": "192.168.1.1",
            "mac_address": "AA:BB:CC:DD:EE:FF",
        }
        obj = CurrentNetwork(**data)
        assert obj.connected is True
        assert obj.ssid == "MyWiFi"
        assert obj.signal == 75
        assert obj.interface == "wlan0"

    def test_accepts_valid_disconnected_network(self):
        data = {
            "connected": False,
            "interface": "wlan0",
        }
        obj = CurrentNetwork(**data)
        assert obj.connected is False
        assert obj.ssid is None
        assert obj.signal is None
        assert obj.interface == "wlan0"

    def test_accepts_signal_null(self):
        data = {"connected": False, "interface": "eth0", "signal": None}
        obj = CurrentNetwork(**data)
        assert obj.signal is None

    def test_accepts_signal_in_range_0_100(self):
        data = {"connected": True, "ssid": "X", "signal": 0, "interface": "wlan0"}
        obj = CurrentNetwork(**data)
        assert obj.signal == 0
        data["signal"] = 100
        obj = CurrentNetwork(**data)
        assert obj.signal == 100

    def test_rejects_missing_interface(self):
        with pytest.raises(ValidationError):
            CurrentNetwork(connected=False)

    def test_rejects_missing_connected(self):
        with pytest.raises(ValidationError):
            CurrentNetwork(interface="wlan0")

    def test_rejects_wrong_type_signal(self):
        with pytest.raises(ValidationError):
            CurrentNetwork(connected=False, interface="wlan0", signal="strong")


class TestNetworkInfo:
    def test_accepts_valid(self):
        data = {
            "ssid": "MyWiFi",
            "signal": 80,
            "security": "WPA2",
            "frequency": 2437,
            "channel": 6,
        }
        obj = NetworkInfo(**data)
        assert obj.ssid == "MyWiFi"
        assert obj.signal == 80
        assert obj.security == "WPA2"

    def test_accepts_minimal_required(self):
        data = {"ssid": "X", "signal": 0, "security": "open"}
        obj = NetworkInfo(**data)
        assert obj.frequency is None
        assert obj.channel is None

    def test_rejects_missing_ssid(self):
        with pytest.raises(ValidationError):
            NetworkInfo(signal=50, security="WPA2")

    def test_rejects_missing_signal(self):
        with pytest.raises(ValidationError):
            NetworkInfo(ssid="X", security="WPA2")

    def test_rejects_wrong_type_signal(self):
        with pytest.raises(ValidationError):
            NetworkInfo(ssid="X", signal="good", security="WPA2")


class TestConnectRequest:
    def test_accepts_ssid_only(self):
        obj = ConnectRequest(ssid="MyWiFi")
        assert obj.ssid == "MyWiFi"
        assert obj.password is None
        assert obj.hidden is False

    def test_accepts_full(self):
        obj = ConnectRequest(ssid="X", password="secret", hidden=True)
        assert obj.password == "secret"
        assert obj.hidden is True

    def test_rejects_missing_ssid(self):
        with pytest.raises(ValidationError):
            ConnectRequest(password="x")


class TestConnectResponse:
    def test_accepts_valid(self):
        obj = ConnectResponse(success=True, message="Connecté", ssid="MyWiFi")
        assert obj.success is True
        assert obj.message == "Connecté"
        assert obj.ssid == "MyWiFi"

    def test_rejects_missing_success(self):
        with pytest.raises(ValidationError):
            ConnectResponse(message="OK")

    def test_rejects_missing_message(self):
        with pytest.raises(ValidationError):
            ConnectResponse(success=True)
