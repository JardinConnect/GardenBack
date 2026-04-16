import asyncio

import pytest

from services.sse.manager import SSEConnectionLimitError, SSEConnectionManager


class TestSSEConnectionManager:
    def test_register_raises_when_at_capacity(self):
        async def _run() -> None:
            manager = SSEConnectionManager(1)
            await manager.register()
            with pytest.raises(SSEConnectionLimitError):
                await manager.register()

        asyncio.run(_run())

    def test_unregister_is_idempotent(self):
        async def _run() -> None:
            manager = SSEConnectionManager(10)
            q = await manager.register()
            await manager.unregister(q)
            await manager.unregister(q)

        asyncio.run(_run())
