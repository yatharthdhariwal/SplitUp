import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file into environment variables
load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    # Flask secret key — used for session signing (not JWT)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-this-in-production')

    # Database connection — SQLite by default (zero config, no external service needed).
    # The DB file lives at <project_root>/instance/splitup.db.
    # Override with DATABASE_URL env var to use PostgreSQL or any other DB.
    _basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    _default_db = 'sqlite:///' + os.path.join(_basedir, 'instance', 'splitup.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _default_db
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # suppresses a warning we don't need

    # JWT secret key — different from SECRET_KEY intentionally
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-change-this-in-production')

    # How long a JWT token is valid before the user must log in again.
    # Default: 60 minutes. Can be overridden via .env for production.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 60))
    )

    # Tell Flask-JWT-Extended to propagate its exceptions so our
    # centralized error handlers in errors.py can catch and format them.
    # Without this, JWT errors bypass our handlers and return raw HTML.
    JWT_ERROR_MESSAGE_KEY = 'error'
    PROPAGATE_EXCEPTIONS = True


class DevelopmentConfig(Config):
    """
    Development-specific config.
    Debug mode is ON — Flask shows tracebacks and auto-reloads on code changes.
    """
    DEBUG = True


class ProductionConfig(Config):
    """
    Production-specific config.
    Debug mode is OFF — never expose tracebacks to the public internet.
    Stricter JWT expiry (15 minutes) for better security.
    """
    DEBUG = False

    # Override to shorter expiry in production — if a token is stolen,
    # it's only valid for 15 minutes instead of an hour.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', 15))
    )


# Map the FLASK_ENV environment variable to the right config class.
# Usage: set FLASK_ENV=production in your .env or hosting platform.
config_map = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
}


def get_config():
    """Return the config class matching the current FLASK_ENV (default: development)."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)