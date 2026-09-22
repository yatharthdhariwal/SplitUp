from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from app.config import Config

# These are created here but configured inside create_app()
# so they can be imported and used across the whole app
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Connect our extensions to this app instance
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    return app