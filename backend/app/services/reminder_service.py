"""
Reminder Service
Handles scheduling and sending payment reminders via SMS.
Works with Celery for background task processing.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from app.core.config import settings
from app.models.reminder import ReminderLog, ReminderType, ReminderChannel
from app.models.user import User
from app.services.sms_service import SMSService
from app.utils.time import utcnow


class ReminderService:
    """Service for scheduling and sending payment reminders."""

    @staticmethod
    def get_upcoming_payment_date() -> str:
        """Get the next payment due date string."""
        now = utcnow()
        if now.day <= settings.SHA_PAYMENT_DEADLINE_DAY:
            # This month's deadline is today or still ahead
            return f"{now.year}-{now.month:02d}-{settings.SHA_PAYMENT_DEADLINE_DAY:02d}"
        else:
            # Next month's deadline
            next_month = now.month + 1 if now.month < 12 else 1
            next_year = now.year if now.month < 12 else now.year + 1
            return (
                f"{next_year}-{next_month:02d}-"
                f"{settings.SHA_PAYMENT_DEADLINE_DAY:02d}"
            )

    @staticmethod
    async def create_and_send_reminder(
        db: AsyncSession,
        user: User,
        reminder_type: str = "payment_due",
        custom_message: Optional[str] = None,
        custom_message_sw: Optional[str] = None,
    ) -> Optional[ReminderLog]:
        """
        Create a reminder log entry and send SMS.

        Args:
            db: Database session
            user: The user to remind
            reminder_type: Type of reminder
            custom_message: Custom English message
            custom_message_sw: Custom Swahili message

        Returns:
            ReminderLog if created, None otherwise
        """
        due_date = ReminderService.get_upcoming_payment_date()
        recipient = user.phone_number
        lang = user.preferred_language

        # Generate message based on type
        if custom_message:
            message_en = custom_message
            message_sw = custom_message_sw or custom_message
        elif reminder_type == "payment_due":
            message_en = (
                f"Dear {user.full_name or 'Customer'}, your SHA payment of "
                f"KES {user.contribution_amount:.0f} is due on {due_date}. "
                f"Pay via M-Pesa Paybill {settings.MPESA_PAYBILL}, "
                f"Account {user.national_id}. "
                f"Avoid 2%/month penalty."
            )
            message_sw = (
                f"Mpendwa {user.full_name or 'Mteja'}, malipo yako ya SHA ya "
                f"KES {user.contribution_amount:.0f} yanatarajiwa {due_date}. "
                f"Lipa kwa M-Pesa Paybill {settings.MPESA_PAYBILL}, "
                f"Namba {user.national_id}. "
                f"Kuepuka adhabu ya 2%/mwezi."
            )
        elif reminder_type == "payment_overdue":
            message_en = (
                f"Dear {user.full_name or 'Customer'}, your SHA payment "
                f"is OVERDUE. Pay KES {user.contribution_amount:.0f} now via "
                f"M-Pesa Paybill {settings.MPESA_PAYBILL}, "
                f"Account {user.national_id} to maintain eligibility."
            )
            message_sw = (
                f"Mpendwa {user.full_name or 'Mteja'}, malipo yako ya SHA "
                f"YAMECHELEWA. Lipa KES {user.contribution_amount:.0f} sasa "
                f"kwa M-Pesa Paybill {settings.MPESA_PAYBILL}, "
                f"Namba {user.national_id}."
            )
        else:
            message_en = custom_message or "SHA payment reminder"
            message_sw = custom_message_sw or "Kikumbusho cha malipo ya SHA"

        # Create reminder log
        reminder = ReminderLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            reminder_type=ReminderType(reminder_type),
            channel=ReminderChannel.SMS,
            recipient=recipient,
            message=message_en,
            message_sw=message_sw,
            status="pending",
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)

        # Send SMS
        sms_sent = await SMSService.send_sms(
            recipient,
            message_sw if lang == "sw" else message_en,
        )

        # Update status
        reminder.status = "sent" if sms_sent else "failed"
        reminder.sent_at = utcnow() if sms_sent else None
        await db.commit()
        await db.refresh(reminder)

        logger.info(
            f"Reminder {'sent' if sms_sent else 'failed'}: "
            f"{reminder_type} -> {recipient}"
        )
        return reminder

    @staticmethod
    async def send_bulk_reminders(
        db: AsyncSession,
        user_ids: List[str],
        reminder_type: str = "payment_due",
    ) -> int:
        """
        Send reminders to multiple users.

        Args:
            db: Database session
            user_ids: List of user UUIDs
            reminder_type: Type of reminder

        Returns:
            Number of reminders sent successfully
        """
        sent_count = 0
        for user_id in user_ids:
            query = select(User).where(User.id == user_id)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            if user:
                reminder = await ReminderService.create_and_send_reminder(
                    db, user, reminder_type
                )
                if reminder and reminder.status == "sent":
                    sent_count += 1
        logger.info(f"Bulk reminders: {sent_count}/{len(user_ids)} sent")
        return sent_count

    @staticmethod
    async def get_user_reminders(
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[ReminderLog], int]:
        """Get reminder history for a user."""
        count_query = select(func.count()).select_from(ReminderLog).where(
            ReminderLog.user_id == user_id
        )
        total = (await db.execute(count_query)).scalar_one()

        query = (
            select(ReminderLog)
            .where(ReminderLog.user_id == user_id)
            .order_by(ReminderLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        reminders = result.scalars().all()
        return list(reminders), total