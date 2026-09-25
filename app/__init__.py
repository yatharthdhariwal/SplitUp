import os
from flask import Flask, request as flask_request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# These are created here at module level (not inside create_app) so that
# models and routes can import them directly: `from app import db`
db      = SQLAlchemy()
migrate = Migrate()
jwt     = JWTManager()


def create_app(config_override=None):
    """
    Application factory — creates and configures the Flask app.

    WHY a factory function?
    It lets us create multiple instances of the app with different configs,
    which is essential for testing (test config) vs. production (prod config).

    Args:
        config_override: pass a config object directly (used by tests)
    """
    app = Flask(__name__)

    # Load config — tests can pass their own config object to override
    if config_override:
        app.config.from_object(config_override)
    else:
        from app.config import get_config
        app.config.from_object(get_config())

    # Initialize extensions — each extension binds itself to this app instance
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data.get("sub")
        if not identity:
            return None
        from app.models import User
        try:
            user = db.session.get(User, int(identity))
        except (ValueError, TypeError):
            return None
        if not user:
            return None
        token_email = jwt_data.get("email")
        if token_email and user.email.lower() != token_email.lower():
            return None
        return user

    @jwt.user_lookup_error_loader
    def user_lookup_error_callback(_jwt_header, jwt_data):
        from flask import jsonify
        return jsonify({'error': 'User session is invalid. Please sign in again.', 'code': 'USER_NOT_FOUND'}), 401


    # CORS — Cross-Origin Resource Sharing
    # WHY: When the frontend (e.g. React on localhost:3000) calls this API
    # (localhost:5000), the browser blocks it by default as a "cross-origin"
    # request. CORS headers tell the browser it's allowed.
    # ALLOWED_ORIGINS in .env controls which domains can call this API.
    # Default "*" means any origin — fine for development, lock it down in prod.
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*')
    CORS(app, resources={r'/api/*': {'origins': allowed_origins}})

    # Register centralized error handlers (all JSON, consistent shape)
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # Import models so Alembic/Flask-Migrate can detect them for migrations
    with app.app_context():
        from app.models import User, Group, GroupMember, Expense, ExpenseSplit, Settlement  # noqa: F401

    # Register blueprints — each blueprint is a group of related routes
    from app.routes import auth_bp
    from app.routes.groups import groups_bp
    from app.routes.expenses import expenses_bp
    from app.routes.settlements import settlements_bp
    from app.routes.profile import profile_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(settlements_bp)
    app.register_blueprint(profile_bp)

    # Configure uploads directory for profile pictures
    uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads', 'avatars'))
    os.makedirs(uploads_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = uploads_dir

    # Serve frontend static files
    from flask import send_from_directory
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'index.html')

    # Serve uploaded avatar images
    @app.route('/uploads/avatars/<path:filename>')
    def serve_avatar(filename):
        return send_from_directory(uploads_dir, filename)

    @app.route('/<path:filename>')
    def serve_static(filename):
        if filename.startswith('api/'):
            from flask import jsonify
            return jsonify({'error': 'Not found', 'code': 'NOT_FOUND'}), 404
        target_path = os.path.join(frontend_dir, filename)
        if os.path.isfile(target_path):
            return send_from_directory(frontend_dir, filename)
        return send_from_directory(frontend_dir, 'index.html')

    # Prevent browser caching of API responses so balances always reflect
    # the latest state after settlements
    @app.after_request
    def add_no_cache_headers(response):
        if flask_request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    return app