import os
from dotenv import load_dotenv

# Load variables from .env file into the environment
load_dotenv()

class Config:
    # Secret key used by Flask for sessions/security (not the same as JWT secret)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-this')

    # Database connection string - we'll fill this in .env shortly
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # disables a feature we don't need, saves memory

    # JWT (login token) configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-change-this')