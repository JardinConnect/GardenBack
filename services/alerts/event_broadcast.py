"""
Diffusion in-process des nouveaux AlertEvent vers les clients SSE.

Le handler MQTT (thread paho) appelle notify_alert_event ; les générateurs
SSE s'abonnent via subscribe / unsubscribe. Les mises en file sont planifiées
sur la boucle asyncio principale (call_soon_threadsafe), comme pour pending_acks.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Optional, Set

MAX_SSE_SUBSCRIBERS = 64
ALERT_EVENT_QUEUE_MAXSIZE = 32

_lock = threading.Lock()
_subscribers: Set[asyncio.Queue] = set()


def _put_payload(queue: asyncio.Queue, payload: Dict[str, Any]) -> None:
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass


def subscribe() -> Optional[asyncio.Queue]:
    """Enregistre une file pour ce client. Retourne None si la capacité est atteinte."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=ALERT_EVENT_QUEUE_MAXSIZE)
    with _lock:
        if len(_subscribers) >= MAX_SSE_SUBSCRIBERS:
            return None
        _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    with _lock:
        _subscribers.discard(queue)


def notify_alert_event(payload: Dict[str, Any]) -> None:
    """
    Diffuse un événement à tous les abonnés. Appelable depuis un thread non-asyncio.
    Les erreurs sont ignorées pour ne pas casser le flux MQTT.
    """
    with _lock:
        targets: List[asyncio.Queue] = list(_subscribers)
    if not targets:
        return
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    frozen = dict(payload)
    for q in targets:
        try:
            loop.call_soon_threadsafe(_put_payload, q, frozen)
        except RuntimeError:
            pass
