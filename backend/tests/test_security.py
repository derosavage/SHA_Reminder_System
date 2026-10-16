"""Security regression tests: returning-user login, OTP brute force, callback forgery, STK abuse."""

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_security.db"
os.environ["ALLOW_INSECURE_DEFAULTS"] = "true"
os.environ["MPESA_CALLBACK_SECRET"] = "s3cret-token"

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import init_db, close_db
from app.utils import rate_limit as rl
from main import app

settings.MPESA_CALLBACK_SECRET = "s3cret-token"


@pytest.fixture(scope="module")
def client():
    for f in ("test_security.db", "test_security.db-journal"):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    asyncio.run(init_db())
    with TestClient(app) as c:
        yield c
    asyncio.run(close_db())


@pytest.fixture(autouse=True)
def reset_limits():
    rl._hits.clear()


def _register(client, nid, phone):
    r = client.post("/api/v1/auth/register", json={"national_id": nid, "phone_number": phone})
    assert r.status_code == 200, r.text
    return r.json()["data"]["debug_otp"], "254" + phone[1:]


def _force_resend_allowed(phone):
    """Skip the 60s resend cooldown by back-dating the OTP expiry."""
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.user import User

    async def run():
        async with async_session_factory() as db:
            u = (await db.execute(select(User).where(User.phone_number == phone))).scalar_one()
            if u.otp_expiry:
                u.otp_expiry = datetime.utcnow() - timedelta(minutes=10)
            u.locked_until = None
            await db.commit()

    asyncio.run(run())


def test_returning_user_can_log_in(client):
    otp, phone = _register(client, "11111111", "0711111111")
    assert client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp_code": otp}).status_code == 200

    _force_resend_allowed(phone)
    login = client.post("/api/v1/auth/login", json={"phone_number": phone})
    assert login.status_code == 200
    new_otp = login.json()["data"]["debug_otp"]

    v = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp_code": new_otp})
    assert v.status_code == 200
    assert v.json()["data"]["access_token"]

    # OTP is single-use
    again = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp_code": new_otp})
    assert again.status_code == 400


def test_login_does_not_reveal_unknown_numbers(client):
    r = client.post("/api/v1/auth/login", json={"phone_number": "254799999999"})
    assert r.status_code == 200
    assert "debug_otp" not in r.json()["data"]


def test_otp_brute_force_locks_out(client):
    otp, phone = _register(client, "22222222", "0722222222")
    wrong = "00000" if otp != "00000" else "11111"
    for _ in range(5):
        assert client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp_code": wrong}).status_code == 400
    # Even the correct code no longer works: OTP burned and account locked.
    r = client.post("/api/v1/auth/verify-otp", json={"phone_number": phone, "otp_code": otp})
    assert r.status_code == 400


def test_otp_resend_cooldown(client):
    _, phone = _register(client, "33333333", "0733333333")
    r = client.post("/api/v1/auth/resend-otp", json={"phone_number": phone})
    assert r.status_code == 400  # just registered -> must wait


def test_callback_rejects_forgery(client):
    body = {"Body": {"stkCallback": {"CheckoutRequestID": "x", "ResultCode": 0}}}
    assert client.post("/api/v1/payments/callback", json=body).status_code == 403
    assert client.post("/api/v1/payments/callback?token=wrong", json=body).status_code == 403
    ok = client.post("/api/v1/payments/callback?token=s3cret-token", json=body)
    assert ok.status_code == 200  # authorised (transaction simply not found)


def _login_headers(client, nid, phone):
    otp, intl = _register(client, nid, phone)
    v = client.post("/api/v1/auth/verify-otp", json={"phone_number": intl, "otp_code": otp})
    assert v.status_code == 200
    return {"Authorization": f"Bearer {v.json()['data']['access_token']}"}, intl


def _fake_stk(monkeypatch):
    from app.api.v1 import payment

    async def fake(**kwargs):
        import uuid

        return {"MerchantRequestID": uuid.uuid4().hex, "CheckoutRequestID": uuid.uuid4().hex, "ResponseCode": "0"}

    monkeypatch.setattr(payment.mpesa_service, "stk_push", lambda **kw: fake(**kw))


def test_stk_push_requires_login(client, monkeypatch):
    _fake_stk(monkeypatch)
    r = client.post("/api/v1/payments/stk-push", json={"phone_number": "0712345678", "amount": 300})
    assert r.status_code in (401, 403)


def test_stk_push_only_to_own_phone(client, monkeypatch):
    _fake_stk(monkeypatch)
    headers, intl = _login_headers(client, "44444444", "0744444444")
    other = client.post(
        "/api/v1/payments/stk-push", headers=headers,
        json={"phone_number": "0799999999", "amount": 300},
    )
    assert other.status_code == 403
    own = client.post(
        "/api/v1/payments/stk-push", headers=headers,
        json={"phone_number": "0744444444", "amount": 300},
    )
    assert own.status_code == 200


def test_stk_push_rate_limited_per_phone(client, monkeypatch):
    _fake_stk(monkeypatch)
    headers, _ = _login_headers(client, "55555555", "0755555555")
    payload = {"phone_number": "0755555555", "amount": 300}
    codes = [client.post("/api/v1/payments/stk-push", json=payload, headers=headers).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 429
