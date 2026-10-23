"""
End-to-end smoke test for the sha-pay OTP signup/login flow and the
Kiswahili/English language resolution.

Run from the backend directory:
    python smoke_otp_i18n.py

This exercises the real ASGI app over HTTP (TestClient), so it covers
routing, validation, the auth service, the i18n layer and the SMS
plumbing together.
"""
import os
import sys

# Must be set before importing app modules.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./smoke_otp_i18n.db"
os.environ["DATABASE_URL_SYNC"] = "sqlite:///./smoke_otp_i18n.db"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "smoke-test-secret-key-not-for-production"

import asyncio  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import init_db, close_db, engine, Base  # noqa: E402
from app.utils import rate_limit as rate_limit_module  # noqa: E402
from main import app  # noqa: E402

PHONE_LOCAL = "0712345678"          # local Kenyan format, as a user types it
PHONE_E164 = "254712345678"         # canonical format
NID = "123456789"

results = []


def reset_rate_limits():
    """Clear the in-memory limiter so the smoke test is not throttled."""
    rate_limit_module._hits.clear()


async def fresh_schema():
    """Drop and recreate every table so each run starts from nothing."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def check(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f"  -> {detail}" if detail and not condition else ""))


def h(lang):
    return {"Accept-Language": lang}


def run():
    asyncio.run(fresh_schema())
    reset_rate_limits()

    from app.core.celery_config import celery_app

    app.state.celery_app = celery_app

    with TestClient(app) as client:
        # ---------- 1. Register in Kiswahili, using the LOCAL phone format ----------
        r = client.post(
            "/api/v1/auth/register",
            json={
                "national_id": NID,
                "phone_number": PHONE_LOCAL,
                "full_name": "Amina Test",
                "preferred_language": "sw",
            },
            headers=h("sw"),
        )
        check("register returns 200", r.status_code == 200, r.text[:300])
        body = r.json()
        check("register reports success", body.get("success") is True, r.text[:300])
        check("register echoes language=sw", body.get("language") == "sw", r.text[:300])
        msg_sw = body.get("message", "")
        check(
            "register message is Kiswahili",
            "usajili" in msg_sw.lower() or "umesajiliwa" in msg_sw.lower(),
            msg_sw,
        )
        check(
            "phone is stored canonically as 254XXXXXXXXX",
            body.get("data", {}).get("phone_number") == PHONE_E164,
            r.text[:300],
        )
        otp = body.get("data", {}).get("debug_otp")
        check("register exposes debug_otp (DEBUG=true)", bool(otp), r.text[:300])
        check("OTP is 5 digits", otp is not None and len(str(otp)) == 5, str(otp))

        # ---------- 2. Register in English ----------
        r2 = client.post(
            "/api/v1/auth/register",
            json={
                "national_id": "987654321",
                "phone_number": "0722000111",
                "preferred_language": "en",
            },
            headers=h("en"),
        )
        b2 = r2.json()
        check("english register echoes language=en", b2.get("language") == "en", r2.text[:300])
        check(
            "english register message is English",
            "successful" in b2.get("message", "").lower(),
            b2.get("message", ""),
        )

        # ---------- 3. Duplicate registration ----------
        r3 = client.post(
            "/api/v1/auth/register",
            json={"national_id": NID, "phone_number": PHONE_LOCAL},
            headers=h("sw"),
        )
        check("duplicate register is rejected", r3.status_code in (400, 409), f"{r3.status_code} {r3.text[:200]}")
        check(
            "duplicate message is localized",
            "tayari kuna" in r3.text.lower() or "already exists" in r3.text.lower(),
            r3.text[:200],
        )

        # ---------- 4. Verify the OTP, still using the LOCAL phone format ----------
        # This is the regression guard: before the phone-normalization fix the
        # stored value was 254... while the lookup used the raw 0712345678,
        # so a local-format client could never verify.
        r4 = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": PHONE_LOCAL, "otp_code": otp},
            headers=h("sw"),
        )
        check("verify-otp with local phone format returns 200", r4.status_code == 200, r4.text[:300])
        b4 = r4.json()
        check("verify-otp returns an access token", bool(b4.get("data", {}).get("access_token")), r4.text[:300])
        check("verify-otp echoes language=sw", b4.get("language") == "sw", r4.text[:300])
        check(
            "verify-otp message is Kiswahili",
            "thibitishwa" in b4.get("message", "").lower(),
            b4.get("message", ""),
        )
        token = b4.get("data", {}).get("access_token")

        # ---------- 5. Verify with the canonical format also works ----------
        # Re-register a second user so this needs a fresh OTP.
        r5a = client.post(
            "/api/v1/auth/register",
            json={"national_id": "111222333", "phone_number": "0733445566"},
            headers=h("sw"),
        )
        otp5 = r5a.json().get("data", {}).get("debug_otp")
        r5 = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": "254733445566", "otp_code": otp5},
            headers=h("sw"),
        )
        check("verify-otp with canonical phone format returns 200", r5.status_code == 200, r5.text[:300])

        # ---------- 6. Wrong OTP is rejected ----------
        # A fresh user, so the OTP is still active and the error is
        # specifically "invalid OTP" rather than "no active OTP".
        r6a = client.post(
            "/api/v1/auth/register",
            json={"national_id": "444555666", "phone_number": "0755667788"},
            headers=h("en"),
        )
        r6 = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": "0755667788", "otp_code": "00000"},
            headers=h("en"),
        )
        check("wrong OTP is rejected", r6.status_code in (400, 401), f"{r6.status_code} {r6.text[:200]}")
        check("wrong OTP message is English", "invalid" in r6.text.lower(), r6.text[:200])
        r6b = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": "0755667788", "otp_code": "00000"},
            headers=h("sw"),
        )
        check(
            "wrong OTP message is Kiswahili",
            "si sahihi" in r6b.text.lower(),
            r6b.text[:200],
        )

        # ---------- 7. Authenticated profile ----------
        h_en = {**h("en"), "Authorization": f"Bearer {token}"}
        h_sw = {**h("sw"), "Authorization": f"Bearer {token}"}
        r7 = client.get("/api/v1/users/me", headers=h_en)
        check("GET /users/me works with a token", r7.status_code == 200, r7.text[:300])
        check(
            "stored preferred_language is 'sw' (register payload wins)",
            r7.json().get("data", {}).get("preferred_language") == "sw",
            r7.text[:300],
        )
        r7b = client.get("/api/v1/users/me", headers=h_sw)
        check("GET /users/me works in Kiswahili too", r7b.status_code == 200, r7b.text[:300])
        # PATCH /users/me is the endpoint that carries a localized message.
        r7c = client.patch(
            "/api/v1/users/me",
            json={"full_name": "Amina Test"},
            headers=h_sw,
        )
        check(
            "PATCH /users/me returns a Kiswahili message",
            "umesasishwa" in r7c.json().get("message", "").lower(),
            r7c.json().get("message", ""),
        )
        r7d = client.patch(
            "/api/v1/users/me",
            json={"full_name": "Amina Test"},
            headers=h_en,
        )
        check(
            "PATCH /users/me returns an English message",
            "updated" in r7d.json().get("message", "").lower(),
            r7d.json().get("message", ""),
        )

        # ---------- 8. Login sends an OTP (local phone format) ----------
        reset_rate_limits()
        r8 = client.post(
            "/api/v1/auth/login",
            json={"phone_number": PHONE_LOCAL, "preferred_language": "sw"},
            headers=h("sw"),
        )
        check("login returns 200", r8.status_code == 200, r8.text[:300])
        b8 = r8.json()
        check("login echoes language=sw", b8.get("language") == "sw", r8.text[:300])
        login_otp = b8.get("data", {}).get("debug_otp")
        check(
            "login sends an OTP for a local-format number",
            bool(login_otp) and len(str(login_otp)) == 5,
            r8.text[:300],
        )

        # ---------- 9. The login OTP actually verifies ----------
        r9 = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": PHONE_LOCAL, "otp_code": login_otp},
            headers=h("sw"),
        )
        check("login OTP verifies successfully", r9.status_code == 200, r9.text[:300])

        # ---------- 10. No user enumeration ----------
        reset_rate_limits()
        r10 = client.post(
            "/api/v1/auth/login",
            json={"phone_number": "0799999999"},
            headers=h("sw"),
        )
        b10 = r10.json()
        check(
            "login for an unknown number is indistinguishable (same wording)",
            b10.get("message") == b8.get("message"),
            f"known={b8.get('message')!r} unknown={b10.get('message')!r}",
        )
        check(
            "login for an unknown number does not leak an OTP",
            not b10.get("data", {}).get("debug_otp"),
            r10.text[:300],
        )
        r10b = client.post(
            "/api/v1/auth/login",
            json={"phone_number": "0799999998"},
            headers=h("en"),
        )
        check(
            "unknown-number English login stays generic",
            "if the number is registered" in r10b.json().get("message", "").lower(),
            r10b.json().get("message", ""),
        )

        # ---------- 11. Resend OTP ----------
        reset_rate_limits()
        r11 = client.post(
            "/api/v1/auth/resend-otp",
            json={"phone_number": PHONE_LOCAL},
            headers=h("sw"),
        )
        check("resend-otp returns 200", r11.status_code == 200, r11.text[:300])
        check(
            "resend message is Kiswahili and generic",
            "kama namba imeandikishwa" in r11.json().get("message", "").lower(),
            r11.json().get("message", ""),
        )

        # ---------- 12. `?lang=` query override ----------
        reset_rate_limits()
        r12 = client.post(
            "/api/v1/auth/login?lang=en",
            json={"phone_number": "0799999997"},
            headers=h("sw"),
        )
        check("?lang=en overrides the Accept-Language header", r12.json().get("language") == "en", r12.text[:300])

        # ---------- 13. Unauthenticated STK push stays protected ----------
        r13 = client.post(
            "/api/v1/payments/stk-push",
            json={"phone_number": PHONE_LOCAL, "amount": 300},
        )
        check("STK push without auth is rejected", r13.status_code in (401, 403), f"{r13.status_code} {r13.text[:200]}")

        # ---------- 14. Penalty calculation ----------
        r14 = client.post(
            "/api/v1/penalty/calculate",
            json={"missed_months": 3, "monthly_contribution": 300},
            headers=h("sw"),
        )
        check("penalty calculate returns 200", r14.status_code == 200, r14.text[:300])
        d14 = r14.json().get("data", {})
        check("contributions due is 900", d14.get("total_contributions_due") == 900, r14.text[:300])
        check("penalty is 18 for 3 months @ 300", d14.get("penalty_amount") == 18, r14.text[:300])
        check("total due is 918", d14.get("total_amount_due") == 918, r14.text[:300])
        check(
            "penalty message is Kiswahili",
            "adhabu" in r14.json().get("message", "").lower(),
            r14.json().get("message", ""),
        )

        # ---------- 15. Health ----------
        r15 = client.get("/api/v1/health")
        check("health is healthy", r15.json().get("status") == "healthy", r15.text[:200])
        check("health service name is sha-pay", r15.json().get("service") == "sha-pay", r15.text[:200])

    asyncio.run(close_db())

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 64)
    print(f"SMOKE RESULT: {passed}/{total} checks passed")
    if passed != total:
        print("\nFailures:")
        for label, ok, detail in results:
            if not ok:
                print(f"  - {label}: {detail}")
    print("=" * 64)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run())
