"""
SMS Service
Handles sending SMS messages via Africa's Talking API for reminders and OTP.
"""

from typing import Optional, List
from loguru import logger
import httpx

from app.core.config import settings
from app.core.i18n import DEFAULT_LANGUAGE, coerce_language, translate


class SMSService:
    """Service for sending SMS messages via Africa's Talking."""

    BASE_URL = "https://api.africastalking.com/version1/messaging"

    @staticmethod
    async def send_sms(
        to: str,
        message: str,
        sender_id: Optional[str] = None,
    ) -> bool:
        """
        Send an SMS message via Africa's Talking.

        Args:
            to: Recipient phone number (254 format)
            message: Message content
            sender_id: Optional sender ID (default from settings)

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.AT_API_KEY or settings.AT_USERNAME == "sandbox":
            logger.warning(
                "SMS not sent: Africa's Talking not configured "
                "(use sandbox credentials for testing)"
            )
            return False

        headers = {
            "apiKey": settings.AT_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        # Africa's Talking expects E.164 (+254...); omit "from" unless a sender
        # ID is registered, since an empty value is rejected.
        payload = {
            "username": settings.AT_USERNAME,
            "to": to if to.startswith("+") else f"+{to}",
            "message": message,
        }
        sender = sender_id or settings.AT_SENDER_ID
        if sender:
            payload["from"] = sender

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    SMSService.BASE_URL,
                    data=payload,
                    headers=headers,
                    timeout=15.0,
                )
                response.raise_for_status()
                result = response.json()
                recipient = (
                    result.get("SMSMessageData", {}).get("Recipients") or [{}]
                )[0]
                status = recipient.get("status", "Unknown")
                # Never log the body: OTP messages contain the code.
                logger.info(
                    f"SMS to {to}: status={status}, length={len(message)}"
                )
                # statusCode 100=Processed, 101=Sent, 102=Queued
                return recipient.get("statusCode") in (100, 101, 102) or status in (
                    "Success",
                    "Sent",
                    "Submitted",
                )
            except Exception as e:
                logger.error(f"Failed to send SMS to {to}: {e}")
                return False

    @staticmethod
    async def send_bulk_sms(
        recipients: List[str],
        message: str,
        sender_id: Optional[str] = None,
    ) -> bool:
        """
        Send bulk SMS to multiple recipients.

        Args:
            recipients: List of phone numbers (254 format)
            message: Message content
            sender_id: Optional sender ID

        Returns:
            True if all sent successfully
        """
        success = True
        for recipient in recipients:
            result = await SMSService.send_sms(recipient, message, sender_id)
            if not result:
                success = False
        return success

    @staticmethod
    async def send_otp(
        phone_number: str,
        otp: str,
        language: str = DEFAULT_LANGUAGE,
    ) -> bool:
        """Send OTP verification code via SMS, in the user's language."""
        message = translate(
            "otp_sms",
            language,
            otp=otp,
            minutes=settings.OTP_EXPIRY_MINUTES,
        )
        result = await SMSService.send_sms(phone_number, message)
        if not result:
            logger.warning(f"OTP SMS was not delivered to {phone_number}")
        return result

    @staticmethod
    async def send_payment_reminder(
        phone_number: str,
        name: str,
        amount: float,
        due_date: str,
        account_ref: str,
        language: str = DEFAULT_LANGUAGE,
    ) -> bool:
        """Send payment reminder SMS in the given language."""
        message = translate(
            "payment_reminder_sms",
            coerce_language(language, fallback=DEFAULT_LANGUAGE),
            name=name,
            amount=amount,
            due_date=due_date,
            account_ref=account_ref,
        )
        return await SMSService.send_sms(phone_number, message)