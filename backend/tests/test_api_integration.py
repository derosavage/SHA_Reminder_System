"""
API Integration Tests
Verifies the full request flow: registration -> OTP verify -> profile -> penalty.
Uses a temporary SQLite database so no PostgreSQL/Redis/M-Pesa is needed.
Run: python -m pytest tests/test_api_integration.py -v
"""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_integration.db"
# DEBUG (not ALLOW_INSECURE_DEFAULTS) is what exposes debug_otp in responses.
os.environ["DEBUG"] = "true"

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.database import init_db, close_db
from main import app


@pytest.fixture(scope="module")
def client():
    # Start with a clean DB file so registrations don't collide with
    # users left over from a previous test run.
    for db_file in ("test_integration.db", "test_integration.db-journal"):
        try:
            os.remove(db_file)
        except FileNotFoundError:
            pass

    asyncio.run(init_db())
    with TestClient(app) as c:
        yield c
    asyncio.run(close_db())


def _register_and_verify(client, national_id, phone):
    """Helper: register a user, get debug OTP, verify, return auth headers."""
    r = client.post(
        "/api/v1/auth/register",
        json={"national_id": national_id, "phone_number": phone},
    )
    assert r.status_code == 200
    otp = r.json()["data"]["debug_otp"]
    v = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "254" + phone[1:], "otp_code": otp},
    )
    assert v.status_code == 200
    token = v.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoints(client):
    """Both /health and /api/v1/health must return healthy."""
    for path in ("/api/v1/health", "/health"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


def test_full_auth_flow(client):
    """Register -> debug OTP -> verify -> profile -> eligibility."""
    r = client.post(
        "/api/v1/auth/register",
        json={
            "national_id": "314159265",
            "phone_number": "0711223344",
            "full_name": "Integration Tester",
            "preferred_language": "en",
        },
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["otp_sent"] is False  # SMS not configured in tests
    assert "debug_otp" in data  # dev-only exposure enabled
    otp = data["debug_otp"]

    v = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "254711223344", "otp_code": otp},
    )
    assert v.status_code == 200
    token = v.json()["data"]["access_token"]
    assert token

    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    profile = me.json()["data"]
    assert profile["phone_number"] == "254711223344"
    assert profile["is_verified"] is True
    assert profile["status"] == "active"

    elig = client.get(
        "/api/v1/users/eligibility", headers={"Authorization": f"Bearer {token}"}
    )
    assert elig.status_code == 200
    elig_data = elig.json()["data"]
    assert elig_data["eligibility_status"] == "inactive"
    assert elig_data["paybill"] == "200222"
    assert elig_data["account_reference"] == "314159265"


def test_penalty_calculate_and_history(client):
    """Authenticated penalty calculation saves to history."""
    headers = _register_and_verify(client, "271828182", "0733445566")

    calc = client.post(
        "/api/v1/penalty/calculate",
        json={"missed_months": 3, "monthly_contribution": 300.0},
        headers=headers,
    )
    assert calc.status_code == 200
    result = calc.json()["data"]
    assert result["total_amount_due"] == 918.0
    assert result["penalty_amount"] == 18.0
    assert result["calculation_id"] is not None

    hist = client.get("/api/v1/penalty/history", headers=headers)
    assert hist.status_code == 200
    assert hist.json()["data"]["total_count"] >= 1


def test_penalty_zero_months_rejected(client):
    """missed_months < 1 must be rejected with 422."""
    r = client.post(
        "/api/v1/penalty/calculate",
        json={"missed_months": 0, "monthly_contribution": 300.0},
    )
    assert r.status_code == 422


def test_public_payment_and_formula_endpoints(client):
    """Public endpoints work without authentication."""
    r = client.get("/api/v1/payments/paybill")
    assert r.status_code == 200
    assert r.json()["data"]["paybill"] == "200222"

    r = client.get("/api/v1/penalty/formula")
    assert r.status_code == 200
    assert r.json()["data"]["rate"] == "2% per month (0.02)"


def test_invalid_otp_rejected(client):
    """Wrong OTP must return 400, not authenticate."""
    client.post(
        "/api/v1/auth/register",
        json={"national_id": "161803398", "phone_number": "0744556677"},
    )
    v = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "254744556677", "otp_code": "00000"},
    )
    assert v.status_code == 400