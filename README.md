# sha-pay

**Kikumbusho cha malipo ya SHA na makadirio ya adhabu.**
*SHA payment reminders and penalty estimation — in Kiswahili and English.*

A digital platform that helps Kenyan citizens manage their Social Health Authority (SHA) contributions efficiently. The system provides contribution tracking, penalty estimation, eligibility monitoring, automated SMS reminders, payment guidance, and customer management dashboards.

The product is available in **Kiswahili (`sw`, default)** and **English (`en`)** across the web app, the API responses, the OTP SMS, and the reminder SMS.

---

## 🚀 Features

### P0 - Launch Features
- **Bilingual UI (Kiswahili / English)** - Switch language in-app, persisted per user
- **OTP Signup & Login** - Phone + National ID registration, 5-digit OTP verification via SMS
- **Penalty Calculator** - Works offline + online
- **M-Pesa Paybill Display** - Show 200222 + National ID
- **Eligibility Status** - Active or Inactive based on payments
- **Payment Confirmation** - Store transactions locally
- **User Dashboard** - Track contributions and history
- **Installable PWA** - Add-to-home-screen, works offline

### P1 - Should Have
- Payment history tracking
- Due date reminders (Celery beat schedule + SMS)
- Share paybill via WhatsApp/SMS
- SMS reminders via Africa's Talking
- Payment guidance and instructions

### P2 - Post-Launch
- Push notifications (Firebase)
- WhatsApp reminders (Business API)
- Agent dashboard for cyber cafés
- SACCO/hospital dashboards
- Blockchain audit trail

## 📋 Prerequisites

- **Backend**: Python 3.10+, PostgreSQL 14+, Redis 6+
- **Mobile**: Flutter 3.x SDK, Dart 3.x
- **Accounts**: Safaricom Daraja API, Africa's Talking SMS

## 🏗 Project Structure

```
sha-pay/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # REST API routes
│   │   ├── core/              # Config, database, celery, i18n
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── utils/             # Dependencies, helpers
│   ├── tasks/                  # Celery tasks (reminders)
│   ├── tests/                 # Test suite
│   ├── migrations/            # Alembic migrations
│   ├── main.py                # App entry point
│   └── requirements.txt       # Python dependencies
├── frontend/                   # PWA (index.html, sw.js, manifest, icons)
├── mobile/                     # Flutter Mobile App
├── branding/                   # Logo source; scripts/make_brand_assets.py rebuilds icons
├── scripts/                    # Local test + deployment scripts
├── render.yaml                 # Render blueprint (API + worker + scheduler + Redis)
├── docker-compose.yml          # Full local stack (Postgres + Redis + API + Celery)
└── README.md
```

## 🔧 Backend Setup

### 1. Clone & Setup Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials and API keys
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb shapay_db

# Apply schema migrations (Alembic; see backend/migrations/)
alembic upgrade head
```

`init_db()` also runs `create_all` on startup, which is enough for a fresh local
SQLite database but cannot alter existing tables — use migrations for changes.

### 4. Start Development Server

```bash
DEBUG=true python main.py
# API available at http://localhost:8000
# The interactive API docs are disabled (docs_url=None in main.py).
```

With `DEBUG=true`, `/auth/login` and `/auth/register` return the OTP in the
response body when no SMS provider is configured, so local testing works without
Africa's Talking credentials. Never run a deployment with `DEBUG=true`.

### 5. Start Celery Workers (for reminders)

```bash
# Terminal 1: Celery worker
celery -A app.core.celery_config worker -l info -Q reminders,payments

# Terminal 2: Celery beat (scheduled tasks)
celery -A app.core.celery_config beat -l info
```

Beat is what actually **triggers** the reminders; the worker executes them. Both
are needed, and both need the Redis broker.

### 6. Everything at once (Docker)

```bash
docker compose up -d
```

Starts Postgres, Redis, the API, the Celery worker and the Celery beat scheduler.

## 🌐 Language Support (Kiswahili / English)

| Layer | How the language is chosen |
|---|---|
| Web app | Toggle in the header; persisted in `localStorage`; defaults to Kiswahili |
| API responses | `lang` query param → `Accept-Language` header → the user's `preferred_language` → `sw` |
| OTP SMS | The user's stored `preferred_language` (falls back to the request language) |
| Reminder SMS | The user's stored `preferred_language` |
| Flutter app | Language toggle in-app, persisted locally; also sent as `preferred_language` on signup |

Supported codes are `sw` (Kiswahili) and `en` (English). Anything else falls back to `sw`.

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register with phone, National ID & language |
| `POST` | `/api/v1/auth/verify-otp` | Verify phone with OTP |
| `POST` | `/api/v1/auth/resend-otp` | Resend the OTP |
| `POST` | `/api/v1/auth/login` | Login (sends OTP) |
| `GET` | `/api/v1/users/me` | Get user profile |
| `GET` | `/api/v1/users/eligibility` | Get SHA eligibility |
| `PATCH` | `/api/v1/users/me` | Update profile (incl. `preferred_language`) |
| `DELETE` | `/api/v1/users/me` | Delete account (GDPR) |
| `POST` | `/api/v1/penalty/calculate` | Calculate penalty |
| `GET` | `/api/v1/penalty/history` | Penalty calculation history |
| `GET` | `/api/v1/penalty/formula` | Get penalty formula |
| `POST` | `/api/v1/payments/stk-push` | Initiate M-Pesa payment |
| `POST` | `/api/v1/payments/callback` | M-Pesa callback |
| `GET` | `/api/v1/payments/history` | Payment history |
| `GET` | `/api/v1/payments/paybill` | Paybill info |
| `POST` | `/api/v1/reminders/send` | Send reminder |
| `GET` | `/api/v1/reminders/history` | Reminder history |

### 🔐 OTP Signup & Login

```
POST /api/v1/auth/register   {national_id, phone_number, full_name?, preferred_language?}
  → SMS with a 5-digit OTP
POST /api/v1/auth/verify-otp {phone_number, otp_code}
  → {access_token, token_type, user_id, role}
```

Login is the same two-step flow without the National ID: `POST /api/v1/auth/login`
sends an OTP to the phone number, then `POST /api/v1/auth/verify-otp` exchanges it
for an access token. OTP rules: 5 digits, 5 wrong attempts burns it and locks the
account for 15 minutes, 60 s resend cooldown, single use.

## 🧮 Penalty Calculation Formula

```
Penalty = monthly_contribution × 0.02 × min(months_late, 12)
Rate: 2% per month, simple (not compounding), capped at 12 months
```

The previous wording wrapped this in a `Σ` with `months_late` inside the summand,
which reads as compounding and would give KES 36 for the example below. The
implementation and the worked example use the flat form above.

### Example
- Missed 3 months @ KES 300/month
- Contributions due: KES 900
- Penalty: KES 18
- Total due: KES 918

## 💳 M-Pesa Payment

- **Paybill**: 200222
- **Account**: Your National ID Number
- **Minimum**: KES 300
- **Deadline**: 9th of each month

## ⏰ Reminder Schedule

Celery beat (timezone `Africa/Nairobi`) fires two schedules:

| Schedule | Task | When | Who |
|---|---|---|---|
| `send-payment-reminders` | `tasks.reminder_tasks.check_and_send_reminders` | 08:00 on the 1st, 5th and 8th | All active contributors with SMS on |
| `send-overdue-reminders` | `tasks.reminder_tasks.check_overdue_payments` | 10:00 on the 10th, 15th, 20th and 25th | Contributors whose eligibility has lapsed |

## 🛡 Security & Compliance

What the code actually does today:

- OTP login (5-digit, hashed at rest, 5-attempt lockout, 60 s resend cooldown, no user enumeration)
- JWT bearer tokens (HS256, 120-minute expiry); deleted or suspended accounts are rejected immediately
- M-Pesa callbacks authenticated by a shared secret in the callback URL
- STK push restricted to the caller's own registered phone number
- Account deletion anonymizes the phone number and national ID and writes an audit record
- Per-process rate limiting on auth and STK endpoints

Known gaps relative to a production compliance posture: rate limits are in-memory
per process, the OTP hash is a salted SHA-256 (use a password-hashing KDF if this
ever stores secrets), and encryption at rest depends on the database provider
(Neon encrypts at rest; SQLite in the Render free tier does not).

## 📱 Mobile App

A Flutter app exists under `mobile/` and is being brought in line with the backend:
it now expects 5-digit OTPs (the API issues 5), routes unauthenticated users to the
login screen, and supports Kiswahili/English. The PWA in `frontend/` remains the
supported client.

## 🚢 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full runbook.

The Render blueprint (`render.yaml`) defines four services:

| Service | Type | Purpose |
|---|---|---|
| `sha-pay-api` | web | FastAPI + PWA |
| `sha-pay-worker` | worker | Executes the reminder tasks |
| `sha-pay-scheduler` | worker | Celery beat — triggers the reminders |
| `sha-pay-redis` | redis | Celery broker + result backend |

**Background workers and Redis are paid-plan (Starter+) features on Render.** On
the free tier only `sha-pay-api` runs, and the scheduled reminders will not fire
until a worker and a scheduler exist.

## 👥 Target Users

- **Primary**: Individual SHA contributors, informal sector workers
- **Secondary**: Cyber cafés, SHA agents, SACCOs, hospitals

## 💰 Revenue Model

- Monthly subscription plans
- SMS reminder service fees
- Dashboard licensing (cyber cafés, SACCOs)
- Enterprise integrations (hospitals)

## 📄 License

Proprietary - All Rights Reserved

## 🤝 Support

For API support and enterprise inquiries:

- Email: support@sha-pay.ke
- Phone: +254 700 000 000

---

*Built for Kenyan SHA contributors. Malipo yako, haki yako.*
