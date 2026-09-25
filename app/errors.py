from flask import jsonify
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended.exceptions import (
    NoAuthorizationError,
    InvalidHeaderError,
    WrongTokenError,
    RevokedTokenError,
    FreshTokenRequired,
    UserLookupError,
)
from jwt.exceptions import ExpiredSignatureError, DecodeError


def register_error_handlers(app):
    """
    Attach all JSON error handlers to the Flask app in one place.

    WHY centralize this?
    Without this, Flask returns HTML error pages by default (e.g. a 404
    gives you a big HTML page). Since this is a JSON API, every error
    response — including built-in Flask/JWT errors — should return JSON
    in the same consistent shape:
        { "error": "Human-readable message", "code": "SNAKE_CASE_CODE" }

    That consistent shape makes it much easier to build a frontend later
    — you always know exactly what field to read.
    """

    # -----------------------------------------------------------------------
    # Standard HTTP errors
    # -----------------------------------------------------------------------

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': str(e.description), 'code': 'BAD_REQUEST'}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Authentication required', 'code': 'UNAUTHORIZED'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'You do not have permission to do this', 'code': 'FORBIDDEN'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'The requested resource was not found', 'code': 'NOT_FOUND'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'HTTP method not allowed on this endpoint', 'code': 'METHOD_NOT_ALLOWED'}), 405

    @app.errorhandler(409)
    def conflict(e):
        return jsonify({'error': str(e.description), 'code': 'CONFLICT'}), 409

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({'error': str(e.description), 'code': 'UNPROCESSABLE'}), 422

    @app.errorhandler(500)
    def internal_error(e):
        # Don't expose internal details to the client — just log it
        app.logger.error(f'Internal Server Error: {e}')
        return jsonify({'error': 'An unexpected server error occurred', 'code': 'INTERNAL_ERROR'}), 500

    # -----------------------------------------------------------------------
    # Database errors
    # -----------------------------------------------------------------------

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        """
        Catches database constraint violations automatically.
        e.g. trying to insert a duplicate email (UNIQUE constraint) raises
        IntegrityError from SQLAlchemy — we catch it here instead of
        crashing with a 500.
        """
        from app import db
        db.session.rollback()  # must rollback or the session stays broken

        # Parse the DB error to give a helpful message
        error_msg = str(e.orig).lower()
        if 'unique' in error_msg or 'duplicate' in error_msg:
            return jsonify({
                'error': 'A record with this value already exists',
                'code': 'DUPLICATE_ENTRY'
            }), 409
        return jsonify({
            'error': 'Database constraint violation',
            'code': 'DB_CONSTRAINT_ERROR'
        }), 400

    # -----------------------------------------------------------------------
    # JWT / Authentication errors
    # Each JWT failure has its own exception type — we map them to clear
    # messages so the frontend can handle them properly (e.g. redirect to login)
    # -----------------------------------------------------------------------

    @app.errorhandler(NoAuthorizationError)
    def handle_missing_token(e):
        return jsonify({'error': 'Authorization token is missing', 'code': 'TOKEN_MISSING'}), 401

    @app.errorhandler(InvalidHeaderError)
    def handle_invalid_header(e):
        return jsonify({'error': 'Authorization header is malformed', 'code': 'TOKEN_INVALID'}), 401

    @app.errorhandler(WrongTokenError)
    def handle_wrong_token(e):
        return jsonify({'error': 'Wrong token type provided', 'code': 'TOKEN_WRONG_TYPE'}), 401

    @app.errorhandler(RevokedTokenError)
    def handle_revoked_token(e):
        return jsonify({'error': 'Token has been revoked', 'code': 'TOKEN_REVOKED'}), 401

    @app.errorhandler(FreshTokenRequired)
    def handle_fresh_token_required(e):
        return jsonify({'error': 'A fresh login is required', 'code': 'FRESH_TOKEN_REQUIRED'}), 401

    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token(e):
        return jsonify({'error': 'Token has expired — please log in again', 'code': 'TOKEN_EXPIRED'}), 401

    @app.errorhandler(DecodeError)
    def handle_decode_error(e):
        return jsonify({'error': 'Token is invalid or corrupted', 'code': 'TOKEN_INVALID'}), 401
