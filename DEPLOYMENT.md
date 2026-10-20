# sha-pay Deployment Notes

Last updated: 2026-10-20

## Live (test) deployment

| Piece | Where | Notes |
|---|---|---|
| API + PWA | Render free web service `sha-reminder-api` | https://sha-reminder-api.onrender.com |
| Frontend (optional CDN) | Vercel, root dir `frontend` | `frontend/vercel.json` proxies `/api/*` to the Render URL |

The FastAPI backend serves the PWA itself (`/`, `/manifest.webmanifest`, `/sw.js`, `/icons/*`), so Vercel is optional.

## Repo layout

```
backend/    FastAPI app (main.py, app/, tests/)
frontend/   PWA (index.html, sw.js, manifest, icons, vercel.json)
mobile/     Flutter app (not part of the web deploy)
branding/   Logo source; scripts/make_brand_assets.py rebuilds icons from it
render.yaml Render blueprint (rootDir: backend)
```

## Render

Config lives in `render.yaml`:

- Python 3.11.9 (`PYTHON_VERSION`), build `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/v1/health`

First deploy: dashboard.render.com -> **New -> Blueprint** -> pick the repo (`main`) -> **Apply**.
Redeploy: service -> **Manual Deploy -> Deploy latest commit**.

### Environment variables

| Variable | Set by | Purpose |
|---|---|---|
| `SECRET_KEY` | Render (generated) | JWT signing + OTP hashing |
| `MPESA_CALLBACK_SECRET` | Render (generated) | Shared secret Safaricom echoes as `?token=` on the callback |
| `DEBUG` | blueprint | **Must stay `false`.** With `DEBUG=true` and no SMS provider, `/auth/login` returns the OTP in the response body, which lets anyone sign in as any registered phone number. |
| `ALLOW_INSECURE_DEFAULTS` | not set | Escape hatch for a throwaway instance: lets the API start without `SECRET_KEY`. It no longer exposes OTPs. Do not set it on this service. |
| `MPESA_ENVIRONMENT` | blueprint | `sandbox` or `production` |
| `MPESA_CALLBACK_URL` | **manual** | `https://sha-reminder-api.onrender.com/api/v1/payments/callback?token=<MPESA_CALLBACK_SECRET value>` |
| `MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_PASSKEY` | **manual** | Daraja credentials (STK push returns 502 without them) |
| `MPESA_BUSINESS_SHORTCODE` | manual (optional) | Defaults to `174379` (sandbox) |
| `AT_API_KEY`, `AT_USERNAME`, `AT_SENDER_ID` | **manual** | Africa's Talking SMS (`AT_USERNAME=sandbox` = SMS disabled) |
| `DATABASE_URL` | **manual** | Neon connection string (see below). Unset = SQLite |

Never commit real keys. Set them in the Render dashboard only.

### Free-tier limits

- Sleeps after ~15 min idle; first request takes ~50 s. This can make M-Pesa callbacks time out.
- Local disk is ephemeral: with SQLite, **all data is wiped on every restart or deploy**.

## Database (Neon Postgres, free)

1. Create a project at neon.tech and copy the connection string.
2. Paste it into `DATABASE_URL` on Render as-is. The backend converts
   `postgresql://` / `sslmode=require` to the asyncpg form and handles the `-pooler` host.
3. Redeploy. Tables are created on startup.

## Going from test to real use

1. Set `AT_API_KEY` / `AT_USERNAME` / `AT_SENDER_ID` so OTPs go out by SMS.
   **Until this is done nobody can log in to the test deploy** — the API no
   longer returns the OTP in the response (see `DEBUG` above).
2. Confirm `DEBUG=false` and that `ALLOW_INSECURE_DEFAULTS` is not set.
3. Daraja production credentials, `MPESA_ENVIRONMENT=production`.
4. Persistent database (Neon) instead of SQLite.
5. Run the schema migrations (see below).
6. Consider Cloud Run instead of Render free to avoid cold starts on callbacks. `backend/Dockerfile` builds from the **repository root** (it needs `backend/` and `frontend/`): `docker build -f backend/Dockerfile .`

## Database migrations

The schema is owned by Alembic (`backend/alembic.ini`, `backend/migrations/`).
`init_db()` still runs `create_all` on startup for zero-install local dev, but it
cannot alter an existing table, so real schema changes go through migrations.

```bash
cd backend
alembic upgrade head                              # apply
alembic revision --autogenerate -m "what changed" # after editing a model
alembic stamp head                                # adopt a create_all database as current
```

`0001_baseline` adopts the original `create_all` schema and is a no-op on a
database that already has the tables. `0002_money_numeric` converts the money
columns to `numeric(12,2)` on PostgreSQL (skipped on SQLite, where tables are
created fresh from the models).

## What was verified on the live test deploy (2026-10-17)

- `/api/v1/health` healthy; PWA, manifest, service worker and icons served with correct types.
- Register -> OTP verify works; OTP is single-use.
- Unauthenticated STK push -> 403; forged M-Pesa callback -> 403.
- STK push to someone else's phone -> 403; to own phone -> 502 (Daraja credentials not set yet).
- Penalty calculator: 3 months @ KES 300 -> KES 18 penalty, KES 918 due.

## Security behaviour to know

- OTP: 5 digits, 5 wrong attempts burns it and locks the account 15 min, 60 s resend cooldown.
- OTPs are only ever returned in a response body when `DEBUG=true` (local dev). The deployed service runs `DEBUG=false`.
- Per-IP/per-phone rate limits are in-memory (per process), so they are approximate once more than one instance is running. A shared store (Redis) is required before horizontal scaling.
- Login/resend return the same response for unknown numbers, numbers inside the cooldown, and locked accounts (no user enumeration).
- STK push requires a verified login and can only prompt the caller's own number; the minimum amount is KES 300.
- A token is rejected once the account is deleted or suspended, not just when it expires.
- The PWA service worker does not cache `/api/` responses at all: the Cache API keys on URL only, so caching them served one account's data to the next login on a shared device.
- Access tokens last 120 minutes; the PWA re-opens the login modal on 401.

## Known open items

- **The live test deploy cannot log anyone in until SMS is configured.** That is deliberate: the OTP-in-response shortcut was removed because it allowed account takeover. Add Africa's Talking credentials to restore login.
- Mobile (Flutter) app is untouched by recent changes: it expects 6-digit OTPs (backend sends 5),
  `login_screen.dart` has a `letterSpacing` compile error, and `app.dart` never routes to the login screen.
- Vercel deploy not yet verified.

## Local development

```bash
cd backend
pip install -r requirements.txt
DEBUG=true python -m uvicorn main:app --port 8000   # dev mode: OTP shown in responses
python -m pytest tests -q                           # 26 tests
```
