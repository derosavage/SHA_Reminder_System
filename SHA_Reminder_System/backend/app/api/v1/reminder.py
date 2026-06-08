"""
Reminder API Routes
Handles scheduling and managing payment reminders.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.schemas.reminder import ReminderScheduleRequest
from app.services.reminder_service import ReminderService
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user_id

router = APIRouter()


@router.post("/send", response_model=dict)
async def send_reminder(
    request: ReminderScheduleRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a payment reminder to the authenticated user."""
    from app.models.user import User
    from sqlalchemy import select

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    reminder = await ReminderService.create_and_send_reminder(
        db=db,
        user=user,
        reminder_type=request.reminder_type,
        custom_message=request.custom_message,
        custom_message_sw=request.custom_message_sw,
    )

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reminder",
        )

    return {
        "success": True,
        "message": "Reminder sent successfully.",
        "data": {
            "reminder_id": str(reminder.id),
            "type": reminder.reminder_type.value,
            "channel": reminder.channel.value,
            "recipient": reminder.recipient,
            "status": reminder.status,
            "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
        },
    }


@router.get("/history", response_model=dict)
async def get_reminder_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get reminder history for the authenticated user."""
    reminders, total = await ReminderService.get_user_reminders(
        db, user_id, limit=page_size, offset=(page - 1) * page_size
    )

    return {
        "success": True,
        "data": {
            "reminders": [
                {
                    "id": str(r.id),
                    "type": r.reminder_type.value,
                    "channel": r.channel.value,
                    "message": r.message,
                    "status": r.status,
                    "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reminders
            ],
            "total_count": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/settings", response_model=dict)
async def get_reminder_settings(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's reminder settings."""
    from app.models.user import User
    from sqlalchemy import select

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "data": {
            "sms_notifications": user.sms_notifications,
            "push_notifications": user.push_notifications,
            "reminder_day": user.reminder_day,
            "preferred_language": user.preferred_language,
            "payment_deadline_day": 9,
        },
    }