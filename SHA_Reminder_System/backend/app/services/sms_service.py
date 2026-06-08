"""
SMS Service
Handles sending SMS messages via Africa's Talking API for reminders and OTP.
"""

from typing import Optional, List
from loguru import logger
import httpx

from app.core.config import settings


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

        payload = {
            "username": settings.AT_USERNAME,
            "to": to,
            "message": message,
            "from": sender_id or settings.AT_SENDER_ID,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    SMSService.BASE_URL,
                    data=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()
                status = result.get("SMSMessageData", {}).get("Recipients", [{}])[0].get(
                    "status", "Unknown"
                )
                logger.info(
                    f"SMS sent to {to}: status={status}, "
                    f"message='{message[:50]}...'"
                )
                return status in ("Success", "Submitted")
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
    async def send_otp(phone_number: str, otp: str) -> bool:
        """Send OTP verification code via SMS."""
        message = (
            f"Your SHA Reminder System OTP is: {otp}. "
            f"Valid for {settings.OTP_EXPIRY_MINUTES} minutes. "
            f"Do not share this code."
        )
        message_sw = (
            f"Namba yako ya siri ya SHA ni: {otp}. "
            f"Inatumika kwa dakika {settings.OTP_EXPIRY_MINUTES}. "
            f"Usimwambie mtu yeyote."
        )
        # Send in English (preferred)
        result = await SMSService.send_sms(phone_number, message)
        logger.info(f"OTP sent to {phone_number}")
        return result

    @staticmethod
    async def send_payment_reminder(
        phone_number: str,
        name: str,
        amount: float,
        due_date: str,
        account_ref: str,
        language: str = "sw",
    ) -> bool:
        """Send payment reminder SMS."""
        if language == "sw":
            message = (
                f"Mpendwa {name}, malipo yako ya SHA ya KES {amount} "
                f"yanatarajiwa tarehe {due_date}. Lipa kwa M-Pesa "
                f"Paybill 200222, Namba {account_ref}. "
                f"Ili kuepuka adhabu ya 2%/mwezi, lipa kabla ya tarehe 9."
            )
        else:
            message = (
                f"Dear {name}, your SHA payment of KES {amount} "
                f"is due on {due_date}. Pay via M-Pesa Paybill 200222, "
                f"Account {account_ref}. "
                f"Avoid 2%/month penalty - pay before the 9th."
            )
        return await SMSService.send_sms(phone_number, message)