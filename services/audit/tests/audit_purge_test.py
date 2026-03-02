import asyncio
from unittest.mock import patch

import pytest

from services.audit.purge import create_purge_task, cancel_purge_task


def test_create_purge_task_returns_none_when_retention_not_set():
    with patch("services.audit.purge.settings") as mock_settings:
        mock_settings.ACTION_LOGS_RETENTION_DAYS = None
        result = create_purge_task()
        assert result is None


def test_cancel_purge_task_none_does_not_raise():
    async def _run():
        await cancel_purge_task(None)

    asyncio.run(_run())


def test_create_purge_task_returns_task_when_retention_set():
    async def _run():
        with patch("services.audit.purge.settings") as mock_settings:
            mock_settings.ACTION_LOGS_RETENTION_DAYS = 90
            task = create_purge_task()
            assert task is not None
            await cancel_purge_task(task)

    asyncio.run(_run())


def test_cancel_purge_task_cancels_and_handles_cancelled_error():
    async def _run():
        with patch("services.audit.purge.settings") as mock_settings:
            mock_settings.ACTION_LOGS_RETENTION_DAYS = 90
            task = create_purge_task()
            assert task is not None
            await cancel_purge_task(task)
            assert task.cancelled()

    asyncio.run(_run())
