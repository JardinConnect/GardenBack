"""Tests du flux SSE des événements d'alerte (broadcast + générateur)."""

import asyncio
import json
import threading
import uuid

from services.alerts import service
from services.alerts.event_broadcast import notify_alert_event
from services.async_loop import set_app_loop


def test_alert_events_stream_receives_notify():
    async def _run():
        set_app_loop(asyncio.get_running_loop())
        chunks: list[dict] = []

        async def consume():
            async for item in service.alert_events_stream():
                chunks.append(item)
                if item.get("event") == "alert_event":
                    return

        task = asyncio.create_task(consume())
        for _ in range(100):
            await asyncio.sleep(0.01)
            if chunks:
                break

        payload = {
            "id": str(uuid.uuid4()),
            "alertId": str(uuid.uuid4()),
            "alertTitle": "Test SSE",
            "cellId": str(uuid.uuid4()),
            "cellName": "Cellule",
            "cellLocation": "Zone > Cellule",
            "sensorType": "air_temperature",
            "severity": "warning",
            "value": 42.0,
            "thresholdMin": 0.0,
            "thresholdMax": 40.0,
            "timestamp": "2026-01-01T12:00:00+00:00",
            "isArchived": False,
        }
        notify_alert_event(payload)

        await asyncio.wait_for(task, timeout=3.0)

        assert any(
            c.get("event") == "status" and json.loads(c["data"])["step"] == "connected"
            for c in chunks
        )
        alert_chunks = [c for c in chunks if c.get("event") == "alert_event"]
        assert len(alert_chunks) == 1
        body = json.loads(alert_chunks[0]["data"])
        assert body["step"] == "new_alert_event"
        assert body["alertEvent"] == payload

    asyncio.run(_run())


def test_alert_events_stream_receives_notify_from_worker_thread():
    """notify_alert_event depuis un thread sans boucle asyncio (comme paho-mqtt)."""

    async def _run():
        set_app_loop(asyncio.get_running_loop())
        chunks: list[dict] = []

        async def consume():
            async for item in service.alert_events_stream():
                chunks.append(item)
                if item.get("event") == "alert_event":
                    return

        task = asyncio.create_task(consume())
        for _ in range(100):
            await asyncio.sleep(0.01)
            if chunks:
                break

        payload = {
            "id": str(uuid.uuid4()),
            "alertId": str(uuid.uuid4()),
            "alertTitle": "Test SSE thread",
            "cellId": str(uuid.uuid4()),
            "cellName": "Cellule",
            "cellLocation": "Zone > Cellule",
            "sensorType": "air_temperature",
            "severity": "warning",
            "value": 42.0,
            "thresholdMin": 0.0,
            "thresholdMax": 40.0,
            "timestamp": "2026-01-01T12:00:00+00:00",
            "isArchived": False,
        }

        def worker():
            notify_alert_event(payload)

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=5.0)
        assert not t.is_alive(), "Le thread worker MQTT simulé n'a pas terminé."

        await asyncio.wait_for(task, timeout=5.0)

        alert_chunks = [c for c in chunks if c.get("event") == "alert_event"]
        assert len(alert_chunks) == 1
        body = json.loads(alert_chunks[0]["data"])
        assert body["step"] == "new_alert_event"
        assert body["alertEvent"] == payload

    asyncio.run(_run())
