# SHA Reminder & Penalty Estimation System

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
SHA_Reminder_System/
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

# Run migrations (when available)
alembic upgrade head
```

### 4. Start Development Server

```bash
python main.py
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

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
Penalty = Σ(monthly_contribution × 0.02 × months_late)
Rate: 2% per month (from SHA Tariff Registry)
```

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

- Kenyan Data Protection Act 2019 compliant
- Immutable audit trail for all transactions
- Encrypted data storage at rest
- Role-based access control
- User consent for data collection
- Account deletion with data anonymization

## 📱 Mobile App (Coming Soon)

Flutter mobile app will provide:
- Offline penalty calculator
- M-Pesa deep linking
- Swahili + English interface
- Local SQLite database
- Background sync

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
- Email: support@sha-reminder.ke
- Phone: +254 700 000 000

---

*Built for Kenyan SHA contributors. Malipo yako, haki yako.*