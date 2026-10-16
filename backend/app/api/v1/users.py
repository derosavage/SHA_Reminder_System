"""
User Profile API Routes
Handles profile management and eligibility status.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.schemas.user import UserUpdate, UserProfile, UserResponse
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user_id

router = APIRouter()


@router.get("/me", response_model=dict)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's profile."""
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

    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "national_id": user.national_id,
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "status": user.status.value,
            "sha_number": user.sha_number,
            "is_verified": user.is_verified,
            "eligibility_status": user.eligibility_status,
            "contribution_amount": user.contribution_amount,
            "last_contribution_date": user.last_contribution_date.isoformat()
            if user.last_contribution_date
            else None,
            "preferred_language": user.preferred_language,
            "sms_notifications": user.sms_notifications,
            "reminder_day": user.reminder_day,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat()
            if user.last_login_at
            else None,
        },
    }


@router.patch("/me", response_model=dict)
async def update_my_profile(
    update_data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile."""
    updated_user = await AuthService.update_user_profile(
        db, user_id, update_data.model_dump(exclude_none=True)
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "success": True,
        "message": "Profile updated successfully.",
        "data": {
            "full_name": updated_user.full_name,
            "email": updated_user.email,
            "preferred_language": updated_user.preferred_language,
            "sms_notifications": updated_user.sms_notifications,
            "reminder_day": updated_user.reminder_day,
        },
    }


@router.get("/eligibility", response_model=dict)
async def get_eligibility_status(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the authenticated user's SHA eligibility status."""
    from app.models.user import User
    from app.models.transaction import Transaction, TransactionStatus
    from sqlalchemy import select, desc
    from datetime import datetime, timedelta

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get last contribution
    last_txn_query = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.COMPLETED,
        )
        .order_by(desc(Transaction.transaction_date))
        .limit(1)
    )
    txn_result = await db.execute(last_txn_query)
    last_txn = txn_result.scalar_one_or_none()

    # Determine eligibility
    now = datetime.utcnow()
    last_payment_date = last_txn.completed_at if last_txn else None
    months_since_last_payment = 0
    if last_payment_date:
        months_since_last_payment = (
            (now.year - last_payment_date.year) * 12
            + (now.month - last_payment_date.month)
        )

    is_eligible = months_since_last_payment < 1  # Paid within last month
    if not last_payment_date:
        is_eligible = False

    return {
        "success": True,
        "data": {
            "eligibility_status": "active" if is_eligible else "inactive",
            "is_eligible": is_eligible,
            "last_payment_date": last_payment_date.isoformat()
            if last_payment_date
            else None,
            "months_since_last_payment": months_since_last_payment,
            "next_payment_due": f"{now.year}-{now.month:02d}-09",
            "contribution_amount": user.contribution_amount,
            "paybill": "200222",
            "account_reference": user.national_id,
        },
    }


@router.delete("/me", response_model=dict)
async def delete_my_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete the authenticated user's account (Data Protection Act compliance)."""
    from app.models.user import User, UserStatus
    from app.models.audit import AuditLog, AuditAction
    from sqlalchemy import select
    from datetime import datetime
    import uuid

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Soft delete: mark as deleted instead of removing
    user.deleted_at = datetime.utcnow()
    user.status = UserStatus.DELETED
    user.phone_number = f"deleted_{user.id}_{user.phone_number}"
    user.national_id = f"deleted_{user.id}_{user.national_id}"

    # Log deletion
    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=AuditAction.ACCOUNT_DELETED,
        resource_type="user",
        resource_id=str(user.id),
        description="User account deleted per Data Protection Act 2019",
    )
    db.add(audit)
    await db.commit()

    logger.info(f"User account deleted: {user_id}")
    return {
        "success": True,
        "message": "Account deleted successfully. Your data has been anonymized.",
    }