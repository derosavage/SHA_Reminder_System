"""Scheduled SMS reminder tasks.

Celery workers are synchronous while the services are async, so each task opens
its own session through async_session_factory and bridges with asyncio.run().

The task names here must match celery_config.beat_schedule exactly; before this
module existed the beat schedule pointed at "tasks.reminder_tasks.*" and every
scheduled run failed with NotRegistered.
"""

import asyncio
from typing import Tuple

from loguru import logger
from sqlalchemy import select

from app.core.celery_config import celery_app
from app.core.database import async_session_factory
from app.models.user import User, UserStatus
from app.services.reminder_service import ReminderService


async def _send_reminders(reminder_type: str, only_inactive: bool) -> Tuple[int, int]:
    sent = 0
    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(
                User.status == UserStatus.ACTIVE,
                User.deleted_at.is_(None),
                User.sms_notifications.is_(True),
            )
        )
        users = list(result.scalars().all())
        if only_inactive:
            users = [u for u in users if u.eligibility_status != "active"]
        for user in users:
            reminder = await ReminderService.create_and_send_reminder(
                db, user, reminder_type
            )
            if reminder and reminder.status == "sent":
                sent += 1
    return sent, len(users)


@celery_app.task(name="tasks.reminder_tasks.check_and_send_reminders")
def check_and_send_reminders() -> dict:
    """Nudge active contributors ahead of the monthly deadline."""
    sent, total = asyncio.run(_send_reminders("payment_due", only_inactive=False))
    logger.info(f"Scheduled payment reminders: {sent}/{total} sent")
    return {"sent": sent, "total": total}


@celery_app.task(name="tasks.reminder_tasks.check_overdue_payments")
def check_overdue_payments() -> dict:
    """Chase contributors whose eligibility has lapsed."""
    sent, total = asyncio.run(_send_reminders("payment_overdue", only_inactive=True))
    logger.info(f"Scheduled overdue reminders: {sent}/{total} sent")
    return {"sent": sent, "total": total}
