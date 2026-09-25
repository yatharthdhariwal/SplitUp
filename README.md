# SplitUp — Bill-Splitting App

A production-ready REST API + frontend for splitting bills among friends, built with Python + Flask. Inspired by Splitwise.

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
- 🗄️ **SQLite** — zero-config, file-based database (no external services needed)
- 🐳 **Docker** — one-command local setup
- ✅ **45 Tests** — full pytest suite

---

## Project Structure

```
SplitUp/
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
│   │   ├── settlements.py # settlements_bp → /api/groups/<id>/settlements
│   │   └── profile.py     # profile_bp → /api/profile/*
│   └── utils/
│       └── __init__.py    # hash_password(), check_password()
├── frontend/              # Static HTML/CSS/JS frontend
├── instance/              # SQLite database file (auto-created, git-ignored)
├── migrations/            # Alembic migration history
├── tests/                 # pytest suite (45 tests)
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── build.sh               # Render build script
├── render.yaml            # Render deployment blueprint
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
git clone https://github.com/yatharthdhariwal/SplitUp.git
cd SplitUp

# 2. Copy environment variables
cp .env.example .env
# Edit .env and set SECRET_KEY and JWT_SECRET_KEY to random values

# 3. Start the app (SQLite database is auto-created)
docker compose up --build

# API is now running at http://localhost:5000
```

### Option B — Manual (local Python)

```bash
# 1. Clone and enter the project
git clone https://github.com/yatharthdhariwal/SplitUp.git
cd SplitUp

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
# Edit .env — set SECRET_KEY and JWT_SECRET_KEY

# 5. Apply database migrations (SQLite DB auto-created in instance/)
flask db upgrade

# 6. Run the development server
python run.py
# API is now running at http://localhost:5000
```

---

## Running Tests

Tests use SQLite in-memory — **no setup needed**.

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
| `DATABASE_URL` | No | `sqlite:///instance/splitup.db` | Override to use PostgreSQL or another DB |
| `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` | No | `60` (dev) / `15` (prod) | Token lifetime |
| `ALLOWED_ORIGINS` | No | `*` | CORS allowed origins — lock down in production |

---

## Deploying to Render

### Option A — Blueprint (one-click)

1. Push this repo to GitHub
2. Go to [render.com/dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Click **Apply** — it creates the web service with a persistent disk for SQLite
5. Done! Your app is live.

### Option B — Manual Setup

1. Go to [render.com/dashboard](https://dashboard.render.com/) → **New** → **Web Service**
2. Connect your GitHub repo `yatharthdhariwal/SplitUp`
3. Configure:
   - **Runtime**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn --workers 2 --bind 0.0.0.0:$PORT --timeout 120 run:app`
4. Add environment variables:
   - `FLASK_ENV` = `production`
   - `FLASK_APP` = `run.py`
   - `SECRET_KEY` = *(generate with `python -c "import secrets; print(secrets.token_hex(32))"`)*
   - `JWT_SECRET_KEY` = *(generate same way)*
   - `ALLOWED_ORIGINS` = `*`
5. **Add a Disk** (Settings → Disks):
   - **Mount Path**: `/opt/render/project/src/instance`
   - **Size**: 1 GB
6. Click **Deploy**

> **Note**: The persistent disk ensures your SQLite database survives redeploys.
> Render's free tier includes one 1 GB disk at no cost.

### Verify

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
| Database | SQLite (file-based, zero config) |
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
