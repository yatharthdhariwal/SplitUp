from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Group, GroupMember, User

groups_bp = Blueprint('groups', __name__, url_prefix='/api/groups')


@groups_bp.route('', methods=['POST'])
@jwt_required()
def create_group():
    user_id = get_jwt_identity()
    data = request.get_json()

    name = data.get('name')
    if not name:
        return jsonify({'error': 'Group name is required'}), 400

    # Create the group
    new_group = Group(name=name, created_by=user_id)
    db.session.add(new_group)
    db.session.flush()  # lets us get new_group.id before committing

    # Automatically add the creator as the first member
    membership = GroupMember(group_id=new_group.id, user_id=user_id)
    db.session.add(membership)

    db.session.commit()

    return jsonify({
        'message': 'Group created successfully',
        'group': {
            'id': new_group.id,
            'name': new_group.name,
            'created_by': new_group.created_by
        }
    }), 201


@groups_bp.route('/<int:group_id>/members', methods=['POST'])
@jwt_required()
def add_member(group_id):
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'email is required'}), 400

    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    user_to_add = User.query.filter_by(email=email).first()
    if not user_to_add:
        return jsonify({'error': 'No user found with that email'}), 404

    # Check if already a member
    existing = GroupMember.query.filter_by(group_id=group_id, user_id=user_to_add.id).first()
    if existing:
        return jsonify({'error': 'User is already a member of this group'}), 409

    new_member = GroupMember(group_id=group_id, user_id=user_to_add.id)
    db.session.add(new_member)
    db.session.commit()

    return jsonify({
        'message': f'{user_to_add.name} added to group',
        'group_id': group_id,
        'user_id': user_to_add.id
    }), 201


@groups_bp.route('', methods=['GET'])
@jwt_required()
def list_my_groups():
    user_id = get_jwt_identity()

    # Find all group_members rows for this user, then get their groups
    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    groups = [
        {'id': m.group.id, 'name': m.group.name}
        for m in memberships
    ]

    return jsonify({'groups': groups}), 200