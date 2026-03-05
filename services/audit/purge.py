import asyncio
from datetime import datetime, timedelta, UTC
from typing import Optional

from db.database import SessionLocal
from settings import settings

from .repository import delete_logs_older_than


async def _run_purge_loop() -> None:
    if settings.ACTION_LOGS_RETENTION_DAYS is None:
        return
    while True:
        db = SessionLocal()
        try:
            cutoff = datetime.now(UTC) - timedelta(days=settings.ACTION_LOGS_RETENTION_DAYS)
            deleted = await asyncio.to_thread(delete_logs_older_than, db, cutoff)
            if deleted:
                print(f"[AUDIT] Purge: {deleted} log(s) supprimé(s).")
        finally:
            db.close()
        await asyncio.sleep(86400)


def create_purge_task() -> Optional[asyncio.Task]:
    if settings.ACTION_LOGS_RETENTION_DAYS is None:
        return None
    return asyncio.create_task(_run_purge_loop())


async def cancel_purge_task(task: Optional[asyncio.Task]) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
