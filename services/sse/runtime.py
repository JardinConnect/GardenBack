"""Point d’entrée synchrone pour planifier des broadcasts sur la boucle asyncio."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from db.models import AlertEvent

if TYPE_CHECKING:
    from services.sse.manager import SSEConnectionManager

logger = logging.getLogger(__name__)

_loop: Optional[asyncio.AbstractEventLoop] = None
_manager: Optional["SSEConnectionManager"] = None


def configure_sse_runtime(
    loop: asyncio.AbstractEventLoop,
    manager: "SSEConnectionManager",
) -> None:
    global _loop, _manager
    _loop = loop
    _manager = manager


def clear_sse_runtime() -> None:
    global _loop, _manager
    _loop = None
    _manager = None


def notify_alert_event_if_configured(event: AlertEvent) -> None:
    if _manager is None or _loop is None:
        return

    from services.sse.events import AlertEventNotification

    try:
        payload = AlertEventNotification.from_db(event)
    except Exception:
        logger.exception("SSE: construction AlertEventNotification impossible")
        return

    mgr = _manager

    async def _broadcast() -> None:
        await mgr.broadcast_typed("alert_event", payload)

    try:
        future = asyncio.run_coroutine_threadsafe(_broadcast(), _loop)
    except RuntimeError:
        logger.exception("SSE: impossible de planifier le broadcast (boucle indisponible)")
        return

    def _log_failure(fut) -> None:
        exc = fut.exception()
        if exc is not None:
            logger.error("SSE: échec broadcast alert_event: %s", exc)

    future.add_done_callback(_log_failure)
