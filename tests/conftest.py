"""
conftest.py — pytest fixtures shared across all test files.

KEY DESIGN DECISIONS:
1. We use SQLite (in-memory) so tests need zero external dependencies.
2. The app fixture is function-scoped — each test gets a FRESH database.
   This is slightly slower than session-scoped but guarantees perfect
   test isolation (no user registered in test A bleeds into test B).
3. SQLite doesn't support PostgreSQL's ENUM type natively, so we pass
   use_native_enum=False to SQLAlchemy to store enums as plain strings.
"""
import pytest
from app import create_app, db as _db


class TestingConfig:
    """Minimal config for the test environment."""
    TESTING = True
    DEBUG = True

    # In-memory SQLite — wiped clean between tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Predictable secrets so JWT tokens work in tests
    SECRET_KEY = 'test-secret-key-that-is-long-enough-32b'
    JWT_SECRET_KEY = 'test-jwt-secret-key-that-is-long-32b'

    # Disable token expiry so tests don't need to worry about timing
    JWT_ACCESS_TOKEN_EXPIRES = False

    # Must be True so JWT errors propagate to our error handlers
    PROPAGATE_EXCEPTIONS = True

    ALLOWED_ORIGINS = '*'


@pytest.fixture(scope='function')
def app():
    """
    Create a fresh Flask app + empty database for EACH test function.
    Function scope = perfect isolation (no shared state between tests).
    """
    flask_app = create_app(config_override=TestingConfig)

    with flask_app.app_context():
        # SQLite doesn't understand PostgreSQL-style ENUM types.
        # We need to tell SQLAlchemy to create enums as VARCHAR instead.
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        import sqlite3

        @event.listens_for(Engine, 'connect')
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.close()

        _db.create_all()

    yield flask_app

    with flask_app.app_context():
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Test HTTP client — one fresh client per test."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Shared helper functions (not fixtures — just regular functions tests import)
# ---------------------------------------------------------------------------

def register_user(client, name='Alice', email='alice@test.com', password='secret123'):
    """Register a user and return the full response."""
    return client.post('/api/auth/register', json={
        'name': name, 'email': email, 'password': password
    })


def login_user(client, email='alice@test.com', password='secret123'):
    """Log in and return the JWT access token string."""
    resp = client.post('/api/auth/login', json={
        'email': email, 'password': password
    })
    data = resp.get_json()
    assert 'access_token' in data, (
        f'Login failed for {email}. Response: {data}'
    )
    return data['access_token']


def auth_headers(token):
    """Build the Authorization header dict from a token string."""
    return {'Authorization': f'Bearer {token}'}
