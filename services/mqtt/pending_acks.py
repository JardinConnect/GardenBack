"""
Registre des acquittements en attente.

Permet au générateur SSE (côté HTTP) d'attendre qu'un handler MQTT
résolve un asyncio.Event lorsqu'un message d'ack arrive sur le broker.

Usage :
    # Côté SSE (dans le service alert)
    ack_id = create_pending_ack()
    ...
    result = await wait_for_ack(ack_id, timeout=15)

    # Côté handler MQTT (dans handlers.py)
    resolve_ack(ack_id, payload_dict)
"""

import asyncio
from typing import Any, Dict, Optional

from services.async_loop import get_app_loop


_pending: Dict[str, Dict[str, Any]] = {}
# Structure : { ack_id: { "event": asyncio.Event, "result": dict | None } }


def create_pending_ack(ack_id: str) -> None:
    """Crée une entrée en attente pour un ack_id donné."""
    _pending[ack_id] = {
        "event": asyncio.Event(),
        "result": None,
    }


def resolve_ack(ack_id: str, result: dict) -> bool:
    """
    Résout un ack en attente. Appelé depuis un handler MQTT (thread paho).

    Comme paho tourne dans un thread séparé, on utilise call_soon_threadsafe
    pour signaler l'Event dans la boucle asyncio principale.
    """
    entry = _pending.get(ack_id)
    if entry is None:
        return False

    entry["result"] = result

    loop = get_app_loop()
    if loop is not None and not loop.is_closed():
        try:
            loop.call_soon_threadsafe(entry["event"].set)
        except RuntimeError as exc:
            print(f"[pending_acks] resolve_ack: call_soon_threadsafe échoué ({exc}), set direct.")
            entry["event"].set()
    else:
        print(
            "[pending_acks] resolve_ack: boucle application absente ou fermée, "
            "set direct sur l'Event (hors boucle)."
        )
        entry["event"].set()

    return True


async def wait_for_ack(ack_id: str, timeout: float = 15.0) -> Optional[dict]:
    """
    Attend l'ack correspondant à ack_id avec un timeout.

    Retourne le dict résultat ou None si timeout dépassé.
    Nettoie l'entrée dans tous les cas.
    """
    entry = _pending.get(ack_id)
    if entry is None:
        return None

    try:
        await asyncio.wait_for(entry["event"].wait(), timeout=timeout)
        return entry["result"]
    except asyncio.TimeoutError:
        return None
    finally:
        cancel_pending_ack(ack_id) # S'assure que l'entrée est toujours nettoyée


def cancel_pending_ack(ack_id: str) -> None:
    """Supprime une entrée en attente (nettoyage en cas d'erreur)."""
    _pending.pop(ack_id, None)
