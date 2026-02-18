from abc import ABC, abstractmethod
from typing import List

from services.network.schemas import CurrentNetwork, NetworkInfo


class NetworkProvider(ABC):
    @abstractmethod
    def get_current_network(self) -> CurrentNetwork:
        pass

    @abstractmethod
    def list_networks(self) -> List[NetworkInfo]:
        pass

    @abstractmethod
    def connect(self, ssid: str, password: str | None = None, hidden: bool = False) -> tuple[bool, str]:
        pass
