# sha-pay

A digital platform that helps Kenyan citizens manage their Social Health Authority (SHA) contributions efficiently. The system provides contribution tracking, penalty estimation, eligibility monitoring, automated SMS reminders, payment guidance, and customer management dashboards.

## 🚀 Features

### P0 - Launch Features
- **Phone Registration** - OTP verification via SMS
- **Penalty Calculator** - Works offline + online
- **M-Pesa Paybill Display** - Show 200222 + National ID
- **Eligibility Status** - Active or Inactive based on payments
- **Payment Confirmation** - Store transactions locally
- **User Dashboard** - Track contributions and history

### P1 - Should Have
- Payment history tracking
- Due date reminders (local notifications)
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
│   │   ├── core/              # Config, database, celery
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   └── utils/             # Dependencies, helpers
│   ├── tests/                 # Test suite
│   ├── migrations/            # Alembic migrations
│   ├── main.py                # App entry point
│   └── requirements.txt       # Python dependencies
├── mobile/                    # Flutter Mobile App
│   └── (coming soon)
├── docs/                      # Documentation
├── scripts/                   # Deployment scripts
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
createdb sha_db

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

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register with phone & ID |
| `POST` | `/api/v1/auth/verify-otp` | Verify phone with OTP |
| `POST` | `/api/v1/auth/login` | Login (sends OTP) |
| `GET` | `/api/v1/users/me` | Get user profile |
| `GET` | `/api/v1/users/eligibility` | Get SHA eligibility |
| `PATCH` | `/api/v1/users/me` | Update profile |
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

A Flutter app exists under `mobile/` but is **not usable yet** and is not part of
the web deploy: it expects 6-digit OTPs (the API issues 5), `login_screen.dart`
has a `letterSpacing` compile error, and `app.dart` never routes to the login
screen. The PWA in `frontend/` is the supported client.

## 🚢 Deployment

### Backend (VPS)
```bash
# Using Docker (recommended)
docker-compose up -d

# Or manual deployment
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Requirements
- 2GB RAM minimum
- Ubuntu 20.04+ or Debian 11+
- Nginx as reverse proxy
- Let's Encrypt SSL certificate

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