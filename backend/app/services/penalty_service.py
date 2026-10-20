"""
Penalty Calculator Service
Core business logic for SHA penalty estimation.
Works offline-capable for mobile clients.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from loguru import logger

from app.core.config import settings
from app.models.penalty import PenaltyCalculation
from app.utils.time import utcnow
from app.schemas.penalty import (
    PenaltyCalculateRequest,
    PenaltyCalculateResponse,
    MonthBreakdown,
)


class PenaltyService:
    """Service for calculating SHA contribution penalties."""

    PENALTY_RATE = settings.SHA_LATE_PENALTY_RATE  # 2% per month
    MIN_CONTRIBUTION = settings.SHA_MINIMUM_CONTRIBUTION  # KES 300
    MAX_MONTHS = settings.SHA_MAX_PENALTY_MONTHS  # 12 months

    @staticmethod
    def calculate_penalty(
        missed_months: int,
        monthly_contribution: float = 300.0,
    ) -> dict:
        """
        Calculate penalty for missed SHA contributions.

        Formula:
        - Base contribution owed: missed_months × monthly_contribution
        - Penalty: monthly_contribution × 0.02 per missed month (simple, not
          compounding, capped at SHA_MAX_PENALTY_MONTHS)
        - Total penalty: monthly_contribution × 0.02 × months

        This matches the SHA Tariff Registry: 2% penalty per month late.

        Args:
            missed_months: Number of months payment was missed
            monthly_contribution: Monthly SHA contribution amount (default 300 KES)

        Returns:
            Dict with calculation results and per-month breakdown

        Raises:
            ValueError: If missed_months is less than 1
        """
        if missed_months < 1:
            raise ValueError("Missed months must be at least 1")

        # Cap months to avoid astronomical penalties
        months = min(missed_months, PenaltyService.MAX_MONTHS)
        rate = PenaltyService.PENALTY_RATE

        total_contributions = months * monthly_contribution
        total_penalty = 0.0
        breakdown = []

        # Calculate cumulative penalty: each month adds penalty for all missed months
        for i in range(1, months + 1):
            # Month X penalty = monthly_contribution × 0.02 for being 1 month late
            # But since we missed `i` months total, penalty stacks
            month_penalty = monthly_contribution * rate
            running_total = (monthly_contribution * i) + (sum(
                monthly_contribution * rate for _ in range(i)
            ))

            breakdown.append({
                "month_number": i,
                "month_name": f"Mwezi {i}",  # Swahili: "Month {i}"
                "contribution_due": round(monthly_contribution, 2),
                "penalty_applied": round(month_penalty, 2),
                "running_total": round(running_total, 2),
            })

            total_penalty += month_penalty

        total_amount_due = total_contributions + total_penalty

        return {
            "missed_months": months,
            "monthly_contribution": monthly_contribution,
            "total_contributions_due": round(total_contributions, 2),
            "penalty_amount": round(total_penalty, 2),
            "penalty_rate_applied": rate,
            "total_amount_due": round(total_amount_due, 2),
            "months_breakdown": breakdown,
            "formula_reference": (
                "Penalty = monthly_contribution × 0.02 × min(months_late, 12) "
                "per the SHA Tariff Registry. Rate: 2% per month late, simple."
            ),
        }

    @staticmethod
    async def save_calculation(
        db: AsyncSession,
        user_id: str,
        missed_months: int,
        monthly_contribution: float,
        calculation_result: dict,
        is_offline: bool = False,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> PenaltyCalculation:
        """
        Save a penalty calculation to the database for audit trail.
        """
        calc = PenaltyCalculation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            missed_months=missed_months,
            monthly_contribution=monthly_contribution,
            months_considered=min(missed_months, settings.SHA_MAX_PENALTY_MONTHS),
            total_contributions_due=calculation_result["total_contributions_due"],
            penalty_amount=calculation_result["penalty_amount"],
            penalty_rate_applied=calculation_result["penalty_rate_applied"],
            total_amount_due=calculation_result["total_amount_due"],
            calculation_breakdown=calculation_result.get("months_breakdown"),
            calculation_date=utcnow(),
            is_offline=utcnow() if is_offline else None,
            device_id=device_id,
            ip_address=ip_address,
        )
        db.add(calc)
        await db.commit()
        await db.refresh(calc)
        logger.info(
            f"Penalty calculation saved: {calc.id}, "
            f"user={user_id}, penalty={calc.penalty_amount} KES"
        )
        return calc

    @staticmethod
    async def get_user_calculations(
        db: AsyncSession,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[List[PenaltyCalculation], int]:
        """
        Get penalty calculation history for a user.
        Returns (calculations, total_count).
        """
        # Get total count (COUNT(*), not a full row fetch)
        count_query = select(func.count()).select_from(PenaltyCalculation).where(
            PenaltyCalculation.user_id == user_id
        )
        total_count = (await db.execute(count_query)).scalar_one()

        # Get paginated results
        query = (
            select(PenaltyCalculation)
            .where(PenaltyCalculation.user_id == user_id)
            .order_by(desc(PenaltyCalculation.calculation_date))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        calculations = result.scalars().all()

        return list(calculations), total_count

    @staticmethod
    async def get_calculation_by_id(
        db: AsyncSession, calculation_id: str
    ) -> Optional[PenaltyCalculation]:
        """Get a specific penalty calculation by ID."""
        query = select(PenaltyCalculation).where(
            PenaltyCalculation.id == calculation_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()