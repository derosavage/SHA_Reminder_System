"""
M-Pesa Daraja API Integration Service
Handles STK Push initiation and callback processing for SHA payments.
"""

import uuid
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.config import settings
from app.models.transaction import Transaction, TransactionStatus, TransactionType


class MpesaService:
    """Service for M-Pesa Daraja API integration."""

    BASE_URLS = {
        "sandbox": "https://sandbox.safaricom.co.ke",
        "production": "https://api.safaricom.co.ke",
    }

    @property
    def base_url(self) -> str:
        return self.BASE_URLS.get(
            settings.MPESA_ENVIRONMENT, self.BASE_URLS["sandbox"]
        )

    async def _get_oauth_token(self) -> Optional[str]:
        """
        Get OAuth token from Safaricom API.
        """
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        auth = base64.b64encode(
            f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
        ).decode()

        headers = {"Authorization": f"Basic {auth}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info("M-Pesa OAuth token obtained successfully")
                return data.get("access_token")
            except Exception as e:
                logger.error(f"Failed to get M-Pesa OAuth token: {e}")
                return None

    async def stk_push(
        self,
        phone_number: str,
        amount: float,
        account_reference: str,
        transaction_desc: str = "SHA Payment",
    ) -> Optional[Dict[str, Any]]:
        """
        Initiate an M-Pesa STK Push payment request.

        Args:
            phone_number: Customer phone (254 format)
            amount: Amount to charge in KES
            account_reference: National ID or SHA number
            transaction_desc: Description of transaction

        Returns:
            Response from Safaricom API
        """
        token = await self._get_oauth_token()
        if not token:
            logger.error("Cannot initiate STK Push without OAuth token")
            return None

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{settings.MPESA_BUSINESS_SHORTCODE}{settings.MPESA_PASSKEY}"
            f"{timestamp}".encode()
        ).decode()

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": settings.MPESA_BUSINESS_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": settings.MPESA_BUSINESS_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                logger.info(
                    f"M-Pesa STK Push sent: {result.get('MerchantRequestID')}"
                )
                return result
            except Exception as e:
                logger.error(f"STK Push failed: {e}")
                return None

    async def query_status(
        self,
        checkout_request_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Query the status of an STK Push transaction.

        Args:
            checkout_request_id: The CheckoutRequestID from STK Push response

        Returns:
            Transaction status from Safaricom
        """
        token = await self._get_oauth_token()
        if not token:
            return None

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{settings.MPESA_BUSINESS_SHORTCODE}{settings.MPESA_PASSKEY}"
            f"{timestamp}".encode()
        ).decode()

        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": settings.MPESA_BUSINESS_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Status query failed: {e}")
                return None

    @staticmethod
    async def process_callback(
        db: AsyncSession,
        callback_data: Dict[str, Any],
    ) -> Optional[Transaction]:
        """
        Process M-Pesa payment callback.

        Updates transaction status and user's last contribution date.

        Args:
            db: Database session
            callback_data: The callback data from Safaricom

        Returns:
            Updated Transaction or None
        """
        try:
            stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_description = stk_callback.get("ResultDesc")

            # Find the transaction
            from sqlalchemy import select
            query = select(Transaction).where(
                Transaction.checkout_request_id == checkout_request_id
            )
            result = await db.execute(query)
            transaction = result.scalar_one_or_none()

            if not transaction:
                logger.error(f"Transaction not found: {checkout_request_id}")
                return None

            if result_code == 0:
                # Success - extract payment details
                callback_metadata = stk_callback.get("CallbackMetadata", {}).get(
                    "Item", []
                )
                metadata = {}
                for item in callback_metadata:
                    metadata[item.get("Name")] = item.get("Value")

                transaction.status = TransactionStatus.COMPLETED
                transaction.mpesa_receipt_number = metadata.get(
                    "MpesaReceiptNumber"
                )
                transaction.completed_at = datetime.utcnow()
                transaction.result_code = result_code
                transaction.result_description = result_description

                # Update the user's last contribution date for eligibility tracking
                from app.models.user import User
                user_query = select(User).where(User.id == transaction.user_id)
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()
                if user:
                    user.last_contribution_date = transaction.completed_at
                    user.eligibility_status = "active"
                    logger.info(
                        f"Updated user {user.id} last contribution date to "
                        f"{transaction.completed_at.isoformat()}"
                    )

                logger.info(
                    f"Payment completed: {metadata.get('MpesaReceiptNumber')}, "
                    f"KES {metadata.get('Amount')}"
                )
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.result_code = result_code
                transaction.result_description = result_description
                transaction.failure_reason = result_description

                logger.warning(
                    f"Payment failed: {checkout_request_id}, "
                    f"code={result_code}: {result_description}"
                )

            await db.commit()
            await db.refresh(transaction)
            return transaction

        except Exception as e:
            logger.error(f"Callback processing error: {e}")
            await db.rollback()
            return None