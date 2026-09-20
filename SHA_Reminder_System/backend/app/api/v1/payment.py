"""
M-Pesa Payment API Routes
Handles STK Push initiation and payment history.
"""

import secrets as secrets_module

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from loguru import logger

from app.core.config import settings
from app.core.database import get_db
from app.schemas.transaction import (
    MpesaSTKPushRequest,
    TransactionResponse,
    TransactionCreate,
)
from app.services.mpesa_service import MpesaService
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user_id, get_optional_user_id

router = APIRouter()
mpesa_service = MpesaService()


@router.post("/stk-push", response_model=dict)
async def initiate_stk_push(
    request: MpesaSTKPushRequest,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate M-Pesa STK Push payment to Paybill 200222.
    Sends a payment request to the user's phone.
    """
    result = await mpesa_service.stk_push(
        phone_number=request.phone_number,
        amount=request.amount,
        account_reference=request.account_reference,
        transaction_desc=request.transaction_desc,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to initiate M-Pesa payment. Please try again.",
        )

    # Save transaction to database if authenticated
    if user_id and result.get("MerchantRequestID"):
        from app.models.transaction import Transaction, TransactionType, TransactionStatus
        import uuid
        from datetime import datetime

        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            transaction_type=TransactionType.MPESA,
            status=TransactionStatus.PENDING,
            amount=request.amount,
            phone_number=request.phone_number,
            paybill_number="200222",
            account_reference=request.account_reference,
            merchant_request_id=result.get("MerchantRequestID"),
            checkout_request_id=result.get("CheckoutRequestID"),
            transaction_date=datetime.utcnow(),
        )
        db.add(transaction)
        await db.commit()
        logger.info(f"Transaction saved: {transaction.id}")

    return {
        "success": True,
        "message": "M-Pesa payment request sent. Check your phone for STK Push prompt.",
        "data": {
            "merchant_request_id": result.get("MerchantRequestID"),
            "checkout_request_id": result.get("CheckoutRequestID"),
            "response_code": result.get("ResponseCode"),
            "response_description": result.get("ResponseDescription"),
            "paybill": "200222",
            "amount": request.amount,
        },
    }


@router.post("/callback", response_model=dict)
async def mpesa_callback(
    callback_data: dict,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    M-Pesa callback endpoint.
    Safaricom sends payment confirmation here after STK Push.

    Daraja does not sign its callbacks, so we authenticate the caller via a
    shared secret (MPESA_CALLBACK_TOKEN) embedded in the callback URL we
    hand to Safaricom during STK Push. Without this, anyone who guesses a
    valid CheckoutRequestID could POST a fake "success" callback and mark a
    transaction (and the user's SHA eligibility) as paid for free.
    """
    if settings.MPESA_CALLBACK_TOKEN:
        if not token or not secrets_module.compare_digest(
            token, settings.MPESA_CALLBACK_TOKEN
        ):
            logger.warning("M-Pesa callback rejected: invalid or missing token")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid callback token",
            )
    else:
        logger.warning(
            "M-Pesa callback accepted WITHOUT verification: "
            "MPESA_CALLBACK_TOKEN is not configured"
        )

    logger.info(f"M-Pesa callback received: {callback_data}")

    transaction = await MpesaService.process_callback(db, callback_data)

    if not transaction:
        logger.warning("Callback processing returned no transaction")
        return {"ResultCode": 1, "ResultDesc": "Transaction not found"}

    logger.info(
        f"Callback processed: {transaction.mpesa_receipt_number or 'failed'}"
    )
    return {"ResultCode": 0, "ResultDesc": "Success"}


@router.get("/history", response_model=dict)
async def get_payment_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get payment history for the authenticated user."""
    from sqlalchemy import select, desc
    from app.models.transaction import Transaction

    # Count
    count_query = select(Transaction).where(Transaction.user_id == user_id)
    total = len((await db.execute(count_query)).scalars().all())

    # Paginated results
    query = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.transaction_date))
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    result = await db.execute(query)
    transactions = result.scalars().all()

    return {
        "success": True,
        "data": {
            "transactions": [
                {
                    "id": str(t.id),
                    "amount": t.amount,
                    "status": t.status.value,
                    "mpesa_receipt": t.mpesa_receipt_number,
                    "paybill": t.paybill_number,
                    "account_ref": t.account_reference,
                    "phone": t.phone_number,
                    "date": t.transaction_date.isoformat(),
                }
                for t in transactions
            ],
            "total_count": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/paybill", response_model=dict)
async def get_paybill_info():
    """Get SHA official M-Pesa paybill details for payment."""
    return {
        "success": True,
        "data": {
            "paybill": "200222",
            "account_format": "Your National ID Number",
            "minimum_amount": 300.0,
            "currency": "KES",
            "instructions": {
                "en": (
                    "1. Go to M-Pesa on your phone\n"
                    "2. Select 'Lipa na M-Pesa'\n"
                    "3. Select 'Paybill'\n"
                    "4. Enter Business Number: 200222\n"
                    "5. Enter Account: Your National ID Number\n"
                    "6. Enter Amount (minimum KES 300)\n"
                    "7. Enter your M-Pesa PIN\n"
                    "8. Confirm and send"
                ),
                "sw": (
                    "1. Nenda kwa M-Pesa kwenye simu yako\n"
                    "2. Chagua 'Lipa na M-Pesa'\n"
                    "3. Chagua 'Paybill'\n"
                    "4. Weka Namba ya Biashara: 200222\n"
                    "5. Weka Akaunti: Namba yako ya Kitambulisho\n"
                    "6. Weka Kiasi (kiwango cha chini KES 300)\n"
                    "7. Weka PIN yako ya M-Pesa\n"
                    "8. Thibitisha na tuma"
                ),
            },
        },
    }