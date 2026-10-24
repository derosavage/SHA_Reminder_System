"""
Penalty Calculator API Routes
Core feature: estimate penalties for missed SHA contributions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.i18n import translate
from app.schemas.penalty import (
    PenaltyCalculateRequest,
    PenaltyCalculateResponse,
    PenaltyHistoryResponse,
)
from app.services.penalty_service import PenaltyService
from app.utils.dependencies import (
    get_current_user_id,
    get_optional_user_id,
    get_request_language,
)

router = APIRouter()


@router.post("/calculate", response_model=dict)
async def calculate_penalty(
    request: PenaltyCalculateRequest,
    user_id: Optional[str] = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db),
    language: str = Depends(get_request_language),
):
    """
    Calculate penalty for missed SHA contributions.
    Works offline - can be used without authentication for quick estimation.
    """
    # Perform calculation (synchronous math, no DB needed)
    result = PenaltyService.calculate_penalty(
        missed_months=request.missed_months,
        monthly_contribution=request.monthly_contribution,
    )

    # If user is authenticated, save to database for audit trail
    if user_id:
        calc = await PenaltyService.save_calculation(
            db=db,
            user_id=user_id,
            missed_months=request.missed_months,
            monthly_contribution=request.monthly_contribution,
            calculation_result=result,
            is_offline=request.calculate_offline,
        )
        logger.info(
            f"Penalty calculated for user {user_id}: "
            f"KES {result['penalty_amount']} penalty"
        )
        return {
            "success": True,
            "message": translate("penalty_calculated", language),
            "data": {
                "calculation_id": str(calc.id),
                **result,
            },
        }

    # Anonymous calculation (no DB save)
    return {
        "success": True,
        "message": translate("penalty_calculated", language),
        "data": {
            "calculation_id": None,
            **result,
        },
    }


@router.get("/history", response_model=dict)
async def get_penalty_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    language: str = Depends(get_request_language),
):
    """Get penalty calculation history for the authenticated user."""
    offset = (page - 1) * page_size
    calculations, total = await PenaltyService.get_user_calculations(
        db, user_id, limit=page_size, offset=offset
    )

    return {
        "success": True,
        "message": translate("penalty_history_retrieved", language),
        "data": {
            "calculations": [
                {
                    "id": str(c.id),
                    "missed_months": c.missed_months,
                    "total_contributions_due": c.total_contributions_due,
                    "penalty_amount": c.penalty_amount,
                    "total_amount_due": c.total_amount_due,
                    "calculation_date": c.calculation_date.isoformat(),
                }
                for c in calculations
            ],
            "total_count": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/formula", response_model=dict)
async def get_penalty_formula(
    language: str = Depends(get_request_language),
):
    """
    Get the penalty calculation formula and official rates.
    Transparent formula as required by SHA Tariff Registry.
    """
    return {
        "success": True,
        "message": translate("penalty_formula", language),
        "data": {
            "formula": "Penalty = monthly_contribution × 0.02 × min(months_late, 12)",
            "rate": "2% per month (0.02)",
            "rate_source": "SHA Tariff Registry - Ministry of Health",
            "minimum_contribution": 300.0,
            "currency": "KES",
            "payment_deadline_day": 9,
            "official_paybill": "200222",
            "example": {
                "missed_months": 3,
                "monthly_contribution": 300,
                "total_contributions_due": 900,
                "penalty": 18.00,
                "total_due": 918.00,
            },
            "swahili_summary": (
                "Adhabu ni 2% kwa kila mwezi uliokosa malipo. "
                "Kwa mfano, ukikosa miezi 3, utalipa KES 900 + KES 18 adhabu = KES 918."
            ),
        },
    }