"""Registre des connexions SSE et diffusion des événements."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SSEConnectionLimitError(Exception):
    """Capacité SSE saturée."""


class SSEConnectionManager:
    def __init__(self, max_connections: int) -> None:
        if max_connections < 1:
            raise ValueError("max_connections doit être >= 1")
        self._max_connections = max_connections
        self._lock = asyncio.Lock()
        self._clients: List[asyncio.Queue[str]] = []

    @property
    def max_connections(self) -> int:
        return self._max_connections

    async def register(self) -> asyncio.Queue[str]:
        async with self._lock:
            if len(self._clients) >= self._max_connections:
                raise SSEConnectionLimitError()
            queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
            self._clients.append(queue)
            return queue

    async def unregister(self, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            try:
                self._clients.remove(queue)
            except ValueError:
                pass

    async def broadcast_typed(self, event_name: str, payload: BaseModel) -> None:
        try:
            data = payload.model_dump_json(by_alias=True)
        except Exception:
            logger.exception("SSE: échec sérialisation JSON pour l'événement %s", event_name)
            return

        chunk = f"event: {event_name}\ndata: {data}\n\n"
        async with self._lock:
            targets = list(self._clients)
        for q in targets:
            try:
                q.put_nowait(chunk)
            except asyncio.QueueFull:
                logger.warning("SSE: file client pleine, message ignoré")
