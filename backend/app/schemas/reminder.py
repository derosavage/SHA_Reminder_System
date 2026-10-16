"""
Pydantic schemas for Reminder operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ReminderScheduleRequest(BaseModel):
    """Schema for scheduling a reminder."""
    reminder_type: str = Field(
        ..., pattern="^(payment_due|payment_overdue|penalty_warning|eligibility_alert|general)$"
    )
    channel: str = Field("sms", pattern="^(sms|push|whatsapp)$")
    schedule_for: Optional[datetime] = None
    custom_message: Optional[str] = None
    custom_message_sw: Optional[str] = None


class ReminderLogResponse(BaseModel):
    """Schema for reminder log API response."""
    id: str
    user_id: str
    reminder_type: str
    channel: str
    recipient: str
    message: str
    message_sw: Optional[str]
    status: str
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    scheduled_for: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderTemplate(BaseModel):
    """Schema for reminder message templates (English + Swahili)."""
    payment_due: dict = {
        "en": "Dear {name}, your SHA payment of KES {amount} is due on {date}. "
              "Pay via M-Pesa Paybill 200222, Account {id}. "
              "To avoid penalties of 2%/month, pay before the 9th.",
        "sw": "Mpendwa {name}, malipo yako ya SHA ya KES {amount} yanatarajiwa "
              "tarehe {date}. Lipa kwa M-Pesa Paybill 200222, Namba {id}. "
              "Ili kuepuka adhabu ya 2%/mwezi, lipa kabla ya tarehe 9."
    }
    penalty_warning: dict = {
        "en": "Dear {name}, you have missed {months} SHA payment(s). "
              "Penalty of KES {penalty} has accrued. Pay now via M-Pesa "
              "Paybill 200222, Account {id} to maintain eligibility.",
        "sw": "Mpendwa {name}, umekosa malipo {months} ya SHA. "
              "Adhabu ya KES {penalty} imejilimbikiza. Lipa sasa kwa M-Pesa "
              "Paybill 200222, Namba {id} ili kudumisha haki yako."
    }