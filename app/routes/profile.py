import os
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app import db
from app.models import User

profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route('', methods=['GET'])
@jwt_required()
def get_profile():
    """Return the current user's profile info."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'profile_picture': user.profile_picture,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }), 200


@profile_bp.route('', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update the current user's name. Email cannot be changed."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Name cannot be empty'}), 400

    if len(name) > 100:
        return jsonify({'error': 'Name cannot exceed 100 characters'}), 400

    user.name = name
    db.session.commit()

    return jsonify({
        'message': 'Profile updated successfully',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'profile_picture': user.profile_picture,
        }
    }), 200


@profile_bp.route('/picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    """Upload a profile picture for the current user."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use PNG, JPG, GIF, or WebP'}), 400

    # Create unique filename: user_<id>_<original_name>
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"user_{user.id}.{ext}")

    upload_dir = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'avatars')
    )
    os.makedirs(upload_dir, exist_ok=True)

    # Delete old profile picture if it exists
    if user.profile_picture:
        old_path = os.path.join(upload_dir, user.profile_picture)
        if os.path.isfile(old_path):
            os.remove(old_path)

    file.save(os.path.join(upload_dir, filename))
    user.profile_picture = filename
    db.session.commit()

    return jsonify({
        'message': 'Profile picture updated',
        'profile_picture': filename,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'profile_picture': user.profile_picture,
        }
    }), 200


@profile_bp.route('/picture', methods=['DELETE'])
@jwt_required()
def delete_profile_picture():
    """Remove the current user's profile picture."""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.profile_picture:
        upload_dir = current_app.config.get(
            'UPLOAD_FOLDER',
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'avatars')
        )
        old_path = os.path.join(upload_dir, user.profile_picture)
        if os.path.isfile(old_path):
            os.remove(old_path)
        user.profile_picture = None
        db.session.commit()

    return jsonify({'message': 'Profile picture removed'}), 200
