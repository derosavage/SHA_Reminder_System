"""
Regression tests for Kenyan phone-number normalization.

The registration schema always stored the canonical 254XXXXXXXXX form, but
the login and verify-OTP schemas did not normalize at all. A client that
sent 0712345678 therefore registered successfully but could never receive or
verify an OTP: the lookup compared the raw string against the stored
254-prefixed value and found nothing.

These tests pin the behaviour that was broken.
"""
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_phone.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./test_phone.db"
os.environ["DEBUG"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.core.database import async_session_factory, init_db, close_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, VerifyOTP
from app.utils.phone import is_valid_kenyan_phone, normalize_phone_number
from main import app


@pytest.fixture(scope="module")
def client():
    import asyncio

    asyncio.run(init_db())
    with TestClient(app) as c:
        yield c
    asyncio.run(close_db())


def clear_resend_cooldown(phone_number):
    """
    Forget the OTP that registration just sent.

    Login and resend-otp deliberately honour a 60 second cooldown, so a test
    that registers and then immediately logs in would see no new OTP even
    though the lookup worked. Expiring the stored OTP removes that wait
    without touching the behaviour under test.
    """
    import asyncio

    from sqlalchemy import select

    async def _clear():
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(
                    User.phone_number == normalize_phone_number(phone_number)
                )
            )
            user = result.scalar_one_or_none()
            assert user is not None, f"no user stored for {phone_number}"
            user.otp_expiry = None
            await session.commit()

    asyncio.run(_clear())


# --- The helper ---------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0712345678", "254712345678"),
        ("+254712345678", "254712345678"),
        ("254712345678", "254712345678"),
        ("712345678", "254712345678"),
        ("0712 345 678", "254712345678"),
        ("(0712) 345-678", "254712345678"),
        ("0799999999", "254799999999"),
    ],
)
def test_normalize_phone_number(raw, expected):
    assert normalize_phone_number(raw) == expected


def test_normalize_rejects_nonsense_without_raising():
    assert normalize_phone_number("not-a-phone") == ""
    assert normalize_phone_number("") == ""
    assert normalize_phone_number(None) == ""


def test_is_valid_kenyan_phone():
    assert is_valid_kenyan_phone("254712345678")
    assert is_valid_kenyan_phone("254119876543")
    assert not is_valid_kenyan_phone("254234567890")   # not a Kenyan prefix
    assert not is_valid_kenyan_phone("0712345678")     # not normalized
    assert not is_valid_kenyan_phone("")


# --- The schemas --------------------------------------------------------

def test_user_create_normalizes():
    assert UserCreate(national_id="123456789", phone_number="0712345678").phone_number == "254712345678"


def test_user_create_rejects_bad_number():
    with pytest.raises(ValueError):
        UserCreate(national_id="123456789", phone_number="12345")


def test_user_login_normalizes():
    assert UserLogin(phone_number="0712345678").phone_number == "254712345678"


def test_verify_otp_normalizes():
    assert VerifyOTP(phone_number="0712345678", otp_code="12345").phone_number == "254712345678"


def test_verify_otp_still_validates_the_code():
    with pytest.raises(ValueError):
        VerifyOTP(phone_number="0712345678", otp_code="123")


# --- The end-to-end behaviour that was broken ----------------------------

def _register(client, national_id, phone):
    r = client.post(
        "/api/v1/auth/register",
        json={"national_id": national_id, "phone_number": phone},
        headers={"Accept-Language": "sw"},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["debug_otp"]


def test_otp_can_be_verified_with_the_local_phone_format(client):
    """The core regression: register with 07..., verify with 07..."""
    otp = _register(client, "111111111", "0711000001")
    r = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "0711000001", "otp_code": otp},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["access_token"]


def test_otp_can_be_verified_with_the_canonical_phone_format(client):
    otp = _register(client, "222222222", "0711000002")
    r = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "254711000002", "otp_code": otp},
    )
    assert r.status_code == 200, r.text


def test_login_sends_an_otp_for_a_local_format_number(client):
    """Login used to silently find no user and send nothing at all."""
    _register(client, "333333333", "0711000003")
    clear_resend_cooldown("0711000003")
    r = client.post(
        "/api/v1/auth/login",
        json={"phone_number": "0711000003"},
        headers={"Accept-Language": "sw"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"].get("debug_otp"), r.text


def test_resend_otp_sends_for_a_local_format_number(client):
    _register(client, "444555666", "0711000004")
    clear_resend_cooldown("0711000004")
    r = client.post(
        "/api/v1/auth/resend-otp",
        json={"phone_number": "0711000004"},
        headers={"Accept-Language": "sw"},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("debug_otp"), r.text
