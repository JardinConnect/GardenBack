import subprocess
from typing import List

from services.network.schemas import CurrentNetwork, NetworkInfo
from services.network.providers.base import NetworkProvider
from services.network.errors import NetworkUnavailableError, ConnectFailedError

NMCLI_TIMEOUT = 15


def _run_nmcli(*args: str) -> str:
    try:
        r = subprocess.run(
            ["nmcli", *args],
            capture_output=True,
            text=True,
            timeout=NMCLI_TIMEOUT,
        )
        if r.returncode != 0:
            raise NetworkUnavailableError(r.stderr or f"nmcli exit {r.returncode}")
        return r.stdout
    except FileNotFoundError:
        raise NetworkUnavailableError("nmcli not found (NetworkManager required)")
    except subprocess.TimeoutExpired:
        raise NetworkUnavailableError("nmcli timeout")


def _split_nmcli_line(line: str, max_fields: int) -> List[str]:
    parts = []
    rest = line
    while rest and len(parts) < max_fields:
        if rest.startswith("'") and "'" in rest[1:]:
            end = rest.index("'", 1)
            parts.append(rest[1:end].replace("''", "'"))
            rest = rest[end + 1 :].lstrip(":")
        else:
            if ":" in rest:
                val, _, rest = rest.partition(":")
                parts.append(val.strip())
            else:
                parts.append(rest.strip())
                break
    return parts


def _parse_dev_blocks(stdout: str) -> List[dict]:
    blocks: List[dict] = []
    current: dict = {}
    for line in stdout.strip().split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "GENERAL.DEVICE":
            if current:
                blocks.append(current)
            current = {"interface": value}
        elif key.startswith("IP4.ADDRESS") and "ip_address" not in current:
            current["ip_address"] = value.split("/")[0] if value else None
        elif key == "IP4.GATEWAY":
            current["gateway"] = value or None
        elif key == "GENERAL.TYPE":
            current["type"] = value
        elif key == "GENERAL.HWADDRESS":
            current["mac_address"] = value or None
    if current:
        blocks.append(current)
    return blocks


def _best_device_block(blocks: List[dict]) -> dict:
    for b in blocks:
        if b.get("type") == "wifi" and b.get("ip_address"):
            return b
    for b in blocks:
        if b.get("ip_address"):
            return b
    return blocks[0] if blocks else {"interface": "unknown"}


def _get_connected_wifi() -> tuple[str | None, int | None, str | None]:
    stdout = _run_nmcli("-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list")
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = _split_nmcli_line(line, 4)
        if len(parts) < 2:
            continue
        in_use, ssid = parts[0], parts[1]
        signal = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
        security = parts[3] if len(parts) > 3 else None
        if in_use == "*":
            return (ssid or None, signal, security)
    return (None, None, None)


class LinuxNmcliProvider(NetworkProvider):
    def get_current_network(self) -> CurrentNetwork:
        try:
            dev_stdout = _run_nmcli("-t", "dev", "show")
            blocks = _parse_dev_blocks(dev_stdout)
            dev = _best_device_block(blocks)
            interface = dev.get("interface", "unknown")
            wifi_ssid, signal, security = _get_connected_wifi()
            connected = bool(wifi_ssid)
            return CurrentNetwork(
                connected=connected,
                ssid=wifi_ssid,
                signal=signal,
                security=security,
                interface=interface,
                ip_address=dev.get("ip_address"),
                gateway=dev.get("gateway"),
                mac_address=dev.get("mac_address"),
            )
        except NetworkUnavailableError:
            return CurrentNetwork(
                connected=False,
                interface="unknown",
            )

    def list_networks(self) -> List[NetworkInfo]:
        stdout = _run_nmcli("-t", "-f", "SSID,SIGNAL,SECURITY,CHAN,FREQ", "device", "wifi", "list")
        seen: set[str] = set()
        result: List[NetworkInfo] = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = _split_nmcli_line(line, 5)
            ssid = (parts[0] or "").strip()
            if ssid in seen:
                continue
            seen.add(ssid)
            signal = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            security = (parts[2] or "unknown").strip()
            channel = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
            frequency = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
            result.append(
                NetworkInfo(
                    ssid=ssid,
                    signal=signal,
                    security=security,
                    channel=channel,
                    frequency=frequency,
                )
            )
        return result

    def connect(self, ssid: str, password: str | None = None, hidden: bool = False) -> tuple[bool, str]:
        args = ["device", "wifi", "connect", ssid]
        if hidden:
            args.extend(["hidden", "yes"])
        if password:
            args.extend(["password", password])
        try:
            _run_nmcli(*args)
            return (True, f"Connecté à {ssid}")
        except NetworkUnavailableError as e:
            raise ConnectFailedError(e.message)
