"""Route GET /stream (Server-Sent Events, alertes)."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from db.models import User
from services.auth.dependencies import get_current_user
from services.sse.events import HeartbeatPayload
from services.sse.manager import SSEConnectionLimitError, SSEConnectionManager
from settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _clamp_heartbeat_seconds(value: float) -> float:
    return max(15.0, min(30.0, value))


def _format_sse_chunk(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


async def _sse_event_generator(
    manager: SSEConnectionManager,
    heartbeat_seconds: float,
) -> AsyncIterator[str]:
    try:
        queue = await manager.register()
    except SSEConnectionLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de connexions SSE simultanées.",
        )

    heartbeat_interval = _clamp_heartbeat_seconds(heartbeat_seconds)
    ping_payload = HeartbeatPayload().model_dump_json()
    yield _format_sse_chunk("ping", ping_payload)

    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                yield message
            except asyncio.TimeoutError:
                yield _format_sse_chunk("ping", ping_payload)
    except asyncio.CancelledError:
        logger.debug("SSE: flux annulé pour un client")
        raise
    finally:
        await manager.unregister(queue)


@router.get(
    "/stream",
    summary="Flux SSE (alertes)",
    response_class=StreamingResponse,
)
async def sse_alert_stream(
    request: Request,
    _: User = Depends(get_current_user),
) -> StreamingResponse:
    manager: SSEConnectionManager = request.app.state.sse_manager
    heartbeat = settings.SSE_HEARTBEAT_INTERVAL_SECONDS

    return StreamingResponse(
        _sse_event_generator(manager, heartbeat),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
