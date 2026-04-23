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

from services.async_loop import get_app_loop

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
        subscriber_count = len(targets)
    if not targets:
        print("[SSE][broadcast] notify_alert_event: aucun abonné actif, événement ignoré.")
        return
    loop = get_app_loop()
    if loop is None:
        print(
            "[SSE][broadcast] notify_alert_event: boucle application non enregistrée "
            f"(abonnés={subscriber_count}), événement ignoré."
        )
        return
    if loop.is_closed():
        print(
            "[SSE][broadcast] notify_alert_event: boucle application fermée "
            f"(abonnés={subscriber_count}), événement ignoré."
        )
        return
    frozen = dict(payload)
    scheduled = 0
    for q in targets:
        try:
            loop.call_soon_threadsafe(_put_payload, q, frozen)
            scheduled += 1
        except RuntimeError as exc:
            print(f"[SSE][broadcast] notify_alert_event: call_soon_threadsafe échoué: {exc}")
    print(
        f"[SSE][broadcast] notify_alert_event: {scheduled}/{subscriber_count} "
        f"files planifiées sur la boucle application."
    )
