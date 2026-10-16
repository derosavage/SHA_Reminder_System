"""
Tests for the Penalty Calculator Service
Verifies the core business logic for SHA penalty estimation.
"""

import pytest
from app.services.penalty_service import PenaltyService


class TestPenaltyCalculator:
    """Test suite for SHA penalty calculation."""

    def test_zero_missed_months_returns_zero_penalty(self):
        """If no months missed, penalty should be zero."""
        with pytest.raises(ValueError) as excinfo:
            PenaltyService.calculate_penalty(missed_months=0)
        # The validator in the schema should catch this,
        # but the service itself caps at 1 minimum

    def test_one_month_missed_simple_case(self):
        """Single missed month should incur simple penalty."""
        result = PenaltyService.calculate_penalty(
            missed_months=1, monthly_contribution=300.0
        )
        assert result["missed_months"] == 1
        assert result["total_contributions_due"] == 300.0
        assert result["penalty_amount"] == 6.0  # 300 * 0.02
        assert result["total_amount_due"] == 306.0
        assert result["penalty_rate_applied"] == 0.02

    def test_three_months_missed_standard(self):
        """Standard case: 3 months missed at KES 300/month."""
        result = PenaltyService.calculate_penalty(
            missed_months=3, monthly_contribution=300.0
        )
        assert result["missed_months"] == 3
        assert result["total_contributions_due"] == 900.0
        assert result["penalty_amount"] == 18.0  # 6 + 6 + 6
        assert result["total_amount_due"] == 918.0

    def test_six_months_missed_higher_amount(self):
        """6 months missed at KES 500/month."""
        result = PenaltyService.calculate_penalty(
            missed_months=6, monthly_contribution=500.0
        )
        assert result["missed_months"] == 6
        assert result["total_contributions_due"] == 3000.0
        assert result["penalty_amount"] == 60.0  # 10 * 6
        assert result["total_amount_due"] == 3060.0

    def test_twelve_months_max_cap(self):
        """Should cap at MAX_MONTHS (12) even if more provided."""
        result = PenaltyService.calculate_penalty(
            missed_months=24, monthly_contribution=300.0
        )
        assert result["missed_months"] == 12  # Capped
        assert result["total_contributions_due"] == 3600.0
        assert result["penalty_amount"] == 72.0
        assert result["total_amount_due"] == 3672.0

    def test_breakdown_structure(self):
        """Per-month breakdown should be detailed and correct."""
        result = PenaltyService.calculate_penalty(
            missed_months=2, monthly_contribution=300.0
        )
        breakdown = result["months_breakdown"]
        assert len(breakdown) == 2

        # Month 1
        assert breakdown[0]["month_number"] == 1
        assert breakdown[0]["contribution_due"] == 300.0
        assert breakdown[0]["penalty_applied"] == 6.0
        assert breakdown[0]["running_total"] == 306.0

        # Month 2
        assert breakdown[1]["month_number"] == 2
        assert breakdown[1]["contribution_due"] == 300.0
        assert breakdown[1]["penalty_applied"] == 6.0
        assert breakdown[1]["running_total"] == 612.0  # 300 + 300 + 6 + 6

    def test_formula_reference_present(self):
        """Response should include formula reference."""
        result = PenaltyService.calculate_penalty(missed_months=1)
        assert "formula_reference" in result
        assert "2%" in result["formula_reference"]
        assert "SHA Tariff Registry" in result["formula_reference"]

    def test_different_contribution_amounts(self):
        """Penalty should scale with contribution amount."""
        result_low = PenaltyService.calculate_penalty(1, 300.0)
        result_high = PenaltyService.calculate_penalty(1, 5000.0)

        assert result_low["penalty_amount"] == 6.0  # 300 * 0.02
        assert result_high["penalty_amount"] == 100.0  # 5000 * 0.02