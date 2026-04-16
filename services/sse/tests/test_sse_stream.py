import asyncio
import uuid
from datetime import UTC, datetime

from db.models import AlertEvent, SeverityEnum
from services.sse.events import AlertEventNotification
from services.sse.manager import SSEConnectionManager


class TestSSEStreamAuth:
    def test_stream_returns_401_without_bearer(self, client):
        assert client.get("/api/sse/stream").status_code == 401


class TestSSEBroadcastAlertEvent:
    def test_broadcast_typed_delivers_alert_event_sse(self) -> None:
        async def _run() -> None:
            manager = SSEConnectionManager(10)
            queue = await manager.register()
            event = AlertEvent(
                id=uuid.uuid4(),
                alert_id=uuid.uuid4(),
                alert_title="Test",
                cell_id=uuid.uuid4(),
                cell_name="C1",
                cell_location="/a/b",
                sensor_type="air_temperature",
                severity=SeverityEnum.CRITICAL,
                value=42.0,
                threshold_min=0.0,
                threshold_max=100.0,
                timestamp=datetime.now(UTC),
                is_archived=False,
            )
            payload = AlertEventNotification.from_db(event)
            await manager.broadcast_typed("alert_event", payload)
            msg = await asyncio.wait_for(queue.get(), timeout=2.0)
            assert msg.startswith("event: alert_event\n")
            assert "alertId" in msg
            await manager.unregister(queue)

        asyncio.run(_run())
