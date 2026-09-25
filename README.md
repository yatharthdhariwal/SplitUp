# SplitWise Clone — Bill-Splitting Backend API

A production-ready REST API for splitting bills among friends, built with Python + Flask. Inspired by Splitwise.

[![Tests](https://img.shields.io/badge/tests-45%20passed-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![Flask](https://img.shields.io/badge/flask-3.1-lightgrey)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## Features

- 🔐 **JWT Authentication** — register, login, protected routes
- 👥 **Groups** — create groups, add members
- 💸 **Expenses** — add bills with three split modes:
  - **Equal** — split evenly, remainder handled correctly (no floating-point errors)
  - **Exact** — specify each person's exact share in currency
  - **Percentage** — specify each person's percentage share (must sum to 100)
- 📊 **Balance Calculation** — see who owes whom, net per member
- 🧮 **Debt Simplification** — greedy algorithm finds minimum transactions to settle a group
- ✅ **Settlements** — record actual repayments; balances update automatically
- 🔢 **Precise Money Math** — all amounts stored as `NUMERIC(10,2)`, never `Float`
- 🐳 **Docker** — one-command local setup
- ✅ **45 Tests** — full pytest suite, runs without PostgreSQL

---

## Project Structure

```
splitwise-clone/
├── app/
│   ├── __init__.py        # App factory (create_app)
│   ├── config.py          # Dev/Prod config, reads from .env
│   ├── errors.py          # Centralized JSON error handlers
│   ├── models/
│   │   └── __init__.py    # User, Group, GroupMember, Expense, ExpenseSplit, Settlement
│   ├── routes/
│   │   ├── __init__.py    # auth_bp  → /api/auth/*
│   │   ├── groups.py      # groups_bp → /api/groups/*
│   │   ├── expenses.py    # expenses_bp → /api/groups/<id>/expenses, balances
│   │   └── settlements.py # settlements_bp → /api/groups/<id>/settlements
│   └── utils/
│       └── __init__.py    # hash_password(), check_password()
├── migrations/            # Alembic migration history
├── tests/                 # pytest suite (45 tests, uses SQLite)
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── run.py
├── .env.example
└── .gitignore
```

---

## API Reference

All endpoints return JSON. Error responses always follow:
```json
{ "error": "Human-readable message", "code": "SNAKE_CASE_CODE" }
```

### Auth — `/api/auth`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | — | Register a new user |
| POST | `/api/auth/login` | — | Login, receive JWT token |
| GET | `/api/auth/me` | ✅ JWT | Get current user info |

### Groups — `/api/groups`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/groups` | ✅ JWT | Create a group (creator auto-added as member) |
| GET | `/api/groups` | ✅ JWT | List groups the current user belongs to |
| POST | `/api/groups/<id>/members` | ✅ JWT | Add a user to the group by email |

### Expenses — `/api/groups/<id>/expenses`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/groups/<id>/expenses` | ✅ JWT | Add an expense with split logic |
| GET | `/api/groups/<id>/expenses` | ✅ JWT | List all expenses in a group |
| GET | `/api/groups/<id>/balances` | ✅ JWT | Net balance per member (settlement-aware) |
| GET | `/api/groups/<id>/simplified-debts` | ✅ JWT | Minimum payments to settle the group |

### Settlements — `/api/groups/<id>/settlements`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/groups/<id>/settlements` | ✅ JWT | Record a repayment |
| GET | `/api/groups/<id>/settlements` | ✅ JWT | List all settlements in a group |

---

## Quick Start

### Option A — Docker (recommended, zero setup)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/splitwise-clone.git
cd splitwise-clone

# 2. Copy environment variables
cp .env.example .env
# Edit .env and set SECRET_KEY and JWT_SECRET_KEY to random values

# 3. Start everything (PostgreSQL + Flask API)
docker compose up --build

# API is now running at http://localhost:5000
```

### Option B — Manual (local Python)

```bash
# 1. Clone and enter the project
git clone https://github.com/YOUR_USERNAME/splitwise-clone.git
cd splitwise-clone

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env — set DATABASE_URL to your local PostgreSQL connection string

# 5. Apply database migrations
flask db upgrade

# 6. Run the development server
python run.py
# API is now running at http://localhost:5000
```

---

## Running Tests

Tests use SQLite in-memory — **no PostgreSQL needed**.

```bash
# Activate your virtual environment first, then:
pytest tests/ -v
```

Expected output:
```
45 passed in ~50s
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `development` | `development` or `production` |
| `SECRET_KEY` | Yes | — | Flask session secret — use `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | Yes | — | JWT signing secret — generate same way |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | No | `60` (dev) / `15` (prod) | Token lifetime |
| `ALLOWED_ORIGINS` | No | `*` | CORS allowed origins — lock down in production |

---

## Deploying to Render + Neon (Free Tier)

### Step 1 — Create a Neon PostgreSQL database

1. Sign up at [neon.tech](https://neon.tech) (free tier available)
2. Create a new project
3. Copy the connection string — looks like:
   ```
   postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/splitwise_db?sslmode=require
   ```

### Step 2 — Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/splitwise-clone.git
git push -u origin main
```

### Step 3 — Deploy on Render

1. Sign up at [render.com](https://render.com) (free tier available)
2. New → **Web Service** → Connect your GitHub repo
3. Render auto-detects the `Dockerfile` — no extra config needed
4. Set environment variables in the Render dashboard:
   - `FLASK_ENV` = `production`
   - `DATABASE_URL` = *(your Neon connection string)*
   - `SECRET_KEY` = *(generate with `secrets.token_hex(32)`)*
   - `JWT_SECRET_KEY` = *(generate with `secrets.token_hex(32)`)*
   - `ALLOWED_ORIGINS` = *(your frontend domain, or `*` for now)*
5. Click **Deploy**

The `entrypoint.sh` automatically runs `flask db upgrade` on every deploy, so migrations are always applied.

### Step 4 — Verify

Hit your live Render URL:
```bash
curl https://your-app.onrender.com/api/auth/register \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@example.com","password":"test123"}'
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11 |
| Framework | Flask 3.1 (app factory pattern) |
| ORM | Flask-SQLAlchemy 3.1 |
| Migrations | Flask-Migrate / Alembic |
| Authentication | Flask-JWT-Extended |
| Password Hashing | bcrypt |
| CORS | Flask-CORS |
| Production Server | Gunicorn |
| Database (prod) | PostgreSQL (Neon free tier) |
| Database (tests) | SQLite (in-memory) |
| Testing | pytest + pytest-flask |

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest tests/ -v`
5. Commit and push: `git push origin feature/my-feature`
6. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) file for details.
