"""
Boucle Uvicorn/FastAPI enregistrée pour le code qui tourne ailleurs (ex. handlers MQTT
sur le thread paho).
"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional

_lock = threading.Lock()
_app_loop: Optional[asyncio.AbstractEventLoop] = None


def set_app_loop(loop: asyncio.AbstractEventLoop) -> None:
    """À appeler au démarrage (lifespan), avec asyncio.get_running_loop()."""
    global _app_loop
    with _lock:
        _app_loop = loop


def get_app_loop() -> Optional[asyncio.AbstractEventLoop]:
    """Boucle enregistrée, ou None (démarrage incomplet / tests sans set_app_loop)."""
    with _lock:
        return _app_loop
