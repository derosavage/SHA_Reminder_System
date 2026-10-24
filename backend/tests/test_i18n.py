"""
Bilingual API Tests
Verifies the Kiswahili / English (sw / en) message handling of the API and
the language aware OTP signup flow.
Uses its own SQLite database file so it cannot collide with the other test
modules.
Run: python -m pytest tests/test_i18n.py -v
"""

import os

# Set before importing the app modules so the engine is created against this
# database (other test modules point it at their own file).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_i18n.db"
# DEBUG (not ALLOW_INSECURE_DEFAULTS) is what exposes debug_otp in responses.
os.environ["DEBUG"] = "true"

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core import database as database_module
from app.core.config import settings
from app.core.database import init_db
from app.core.i18n import (
    DEFAULT_LANGUAGE,
    MESSAGES,
    SUPPORTED_LANGUAGES,
    coerce_language,
    resolve_language,
    translate,
)
from app.models.user import User
from app.services.sms_service import SMSService
from app.utils import rate_limit as rl
from main import app

DB_URL = "sqlite+aiosqlite:///./test_i18n.db"


@pytest.fixture(scope="module")
def client():
    """
    Test client bound to a dedicated database file.

    The other test modules set DATABASE_URL before the app is imported, so
    the engine they created already points at their file. Bind this module to
    its own engine to keep the two databases apart.
    """
    for db_file in ("test_i18n.db", "test_i18n.db-journal"):
        try:
            os.remove(db_file)
        except FileNotFoundError:
            pass

    engine = create_async_engine(
        DB_URL, connect_args={"check_same_thread": False}
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    original_engine = database_module.engine
    original_factory = database_module.async_session_factory
    database_module.engine = engine
    database_module.async_session_factory = session_factory

    try:
        asyncio.run(init_db())
        with TestClient(app) as c:
            yield c
    finally:
        database_module.engine = original_engine
        database_module.async_session_factory = original_factory


@pytest.fixture(autouse=True)
def reset_limits():
    """The rate limiter is process wide: keep every test independent."""
    rl._hits.clear()


def _register(client, national_id, phone, **extra):
    """Register a user and return the parsed response body."""
    payload = {"national_id": national_id, "phone_number": phone}
    payload.update(extra)
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


async def _stored_language(phone_number):
    """Read the language actually stored on the user row."""
    async with database_module.async_session_factory() as db:
        user = (
            await db.execute(
                select(User).where(User.phone_number == phone_number)
            )
        ).scalar_one()
        return user.preferred_language


def _errors_by_field(response_json):
    """Map the validation errors of a 422 body to their field name."""
    return {error["loc"][-1]: error["msg"] for error in response_json["detail"]}


def test_supported_languages_are_declared():
    """The catalogue advertises Kiswahili first, English second."""
    assert DEFAULT_LANGUAGE == "sw"
    assert SUPPORTED_LANGUAGES == ("sw", "en")
    assert MESSAGES


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, "sw"),
        ("en", "en"),
        ("en-KE,en;q=0.9,sw;q=0.8", "en"),
        ("fr", "sw"),
        ("sw", "sw"),
    ],
)
def test_resolve_language(header, expected):
    """Accept-Language is parsed with its q-values; unsupported falls back."""
    assert resolve_language(header) == expected


def test_coerce_language_accepts_region_tags():
    """Region tags and casing are coerced to a supported code."""
    assert coerce_language("EN") == "en"
    assert coerce_language("en-KE") == "en"
    assert coerce_language("sw_KE") == "sw"
    assert coerce_language("fr") == "sw"
    assert coerce_language(None) == "sw"


def test_missing_key_falls_back_without_raising():
    """An unknown key returns the key itself and never raises."""
    assert translate("this_key_does_not_exist") == "this_key_does_not_exist"
    assert translate("this_key_does_not_exist", "en") == "this_key_does_not_exist"
    # A known key with an unfilled placeholder must not raise either.
    assert "{otp}" in translate("otp_sms", "en")


def test_translate_formats_placeholders():
    """Placeholders are filled in with str.format()."""
    message = translate("otp_sms", "en", otp="12345", minutes=5)
    assert "12345" in message
    assert "5 minutes" in message
    assert "Do not share this code." in message


def test_auth_messages_follow_accept_language(client):
    """The same auth request answers in Swahili or English per header."""
    sw = client.post(
        "/api/v1/auth/login",
        json={"phone_number": "254700000001"},
        headers={"Accept-Language": "sw"},
    )
    en = client.post(
        "/api/v1/auth/login",
        json={"phone_number": "254700000001"},
        headers={"Accept-Language": "en"},
    )

    assert sw.status_code == 200
    assert en.status_code == 200
    assert sw.json()["message"] == translate("otp_sent_for_login", "sw")
    assert en.json()["message"] == translate("otp_sent_for_login", "en")
    assert sw.json()["message"] != en.json()["message"]
    assert sw.json()["language"] == "sw"
    assert en.json()["language"] == "en"

    # Without a header the default language is used.
    default = client.post(
        "/api/v1/auth/login", json={"phone_number": "254700000001"}
    )
    assert default.status_code == 200
    assert default.json()["language"] == "sw"
    assert default.json()["message"] == translate("otp_sent_for_login", "sw")


def test_login_message_is_identical_for_known_and_unknown_numbers(client):
    """The login wording must not reveal whether a number is registered."""
    _register(client, "512345678", "0700000001")

    known = client.post("/api/v1/auth/login", json={"phone_number": "254700000001"})
    unknown = client.post(
        "/api/v1/auth/login", json={"phone_number": "254700000099"}
    )

    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    assert known.json()["message"] == translate(
        "otp_sent_for_login", DEFAULT_LANGUAGE
    )


def test_lang_query_param_overrides_accept_language(client):
    """An explicit ?lang= wins over the Accept-Language header."""
    r = client.post(
        "/api/v1/auth/resend-otp?lang=en",
        json={"phone_number": "254700000002"},
        headers={"Accept-Language": "sw"},
    )
    assert r.status_code == 200
    assert r.json()["language"] == "en"
    assert r.json()["message"] == translate("otp_resent", "en")


def test_register_honours_preferred_language(client):
    """The payload's preferred_language drives the answer and the row."""
    body = _register(client, "512345679", "0700000002", preferred_language="en")

    assert body["language"] == "en"
    assert body["message"] == translate("registration_success", "en")
    assert asyncio.run(_stored_language("254700000002")) == "en"

    otp = body["data"]["debug_otp"]
    v = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "254700000002", "otp_code": otp},
        headers={"Accept-Language": "en"},
    )
    assert v.status_code == 200
    assert v.json()["message"] == translate("phone_verified", "en")
    assert v.json()["language"] == "en"

    token = v.json()["data"]["access_token"]
    me = client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.json()["data"]["preferred_language"] == "en"


def test_register_lang_param_overrides_preferred_language(client):
    """An explicit ?lang= overrides the language stored on the user."""
    body = _register(client, "512345680", "0700000003", preferred_language="sw")
    assert body["language"] == "sw"
    assert body["message"] == translate("registration_success", "sw")
    assert asyncio.run(_stored_language("254700000003")) == "sw"

    r = client.post(
        "/api/v1/auth/register?lang=en",
        json={"national_id": "512345681", "phone_number": "0700000004"},
    )
    assert r.status_code == 200
    assert r.json()["language"] == "en"
    assert r.json()["message"] == translate("registration_success", "en")


def test_validation_errors_are_localized(client):
    """The UserCreate validation errors are answered in the caller's language."""
    en = client.post(
        "/api/v1/auth/register",
        json={"national_id": "12", "phone_number": "0700000005"},
        headers={"Accept-Language": "en"},
    )
    assert en.status_code == 422
    assert _errors_by_field(en.json())["national_id"] == translate(
        "invalid_national_id", "en"
    )

    sw = client.post(
        "/api/v1/auth/register",
        json={"national_id": "512345682", "phone_number": "12345"},
        headers={"Accept-Language": "sw"},
    )
    assert sw.status_code == 422
    assert _errors_by_field(sw.json())["phone_number"] == translate(
        "invalid_phone_number", "sw"
    )


def test_duplicate_user_error_is_localized(client):
    """A duplicate registration is reported in the caller's language."""
    _register(client, "512345683", "0700000006")

    r = client.post(
        "/api/v1/auth/register",
        json={"national_id": "512345683", "phone_number": "0700000006"},
        headers={"Accept-Language": "en"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == translate("user_already_exists", "en")


def test_otp_sms_is_localized(monkeypatch):
    """The OTP SMS is written in the user's language."""
    sent = {}

    async def fake_send_sms(to, message, sender_id=None):
        sent["message"] = message
        return True

    monkeypatch.setattr(
        SMSService, "send_sms", staticmethod(fake_send_sms)
    )

    asyncio.run(SMSService.send_otp("254700000007", "54321", language="sw"))
    assert "sha-pay" in sent["message"]
    assert "54321" in sent["message"]
    assert f"{settings.OTP_EXPIRY_MINUTES}" in sent["message"]
    assert "Usishiriki" in sent["message"]

    asyncio.run(SMSService.send_otp("254700000007", "54321", language="en"))
    assert "sha-pay" in sent["message"]
    assert "54321" in sent["message"]
    assert "Valid for" in sent["message"]
    assert "Do not share this code." in sent["message"]
