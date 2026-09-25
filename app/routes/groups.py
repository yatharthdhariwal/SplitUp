from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Group, GroupMember, User
from app.utils import hash_password

groups_bp = Blueprint('groups', __name__, url_prefix='/api/groups')


@groups_bp.route('', methods=['POST'])
@jwt_required()
def create_group():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    name = data.get('name', '').strip()
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
            'created_by': new_group.created_by,
            'member_count': 1
        }
    }), 201


@groups_bp.route('/<int:group_id>/members', methods=['POST'])
@jwt_required()
def add_member(group_id):
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()
    name = (data.get('name') or '').strip()

    if not email and not name:
        return jsonify({'error': 'email is required'}), 400

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    # Find existing user by email or name (case-insensitive)
    user_to_add = None
    if email:
        user_to_add = User.query.filter(db.func.lower(User.email) == email.lower()).first()
    elif name:
        user_to_add = User.query.filter(db.func.lower(User.name) == name.lower()).first()

    if not user_to_add:
        # Check if auto-create is requested (or if name is provided)
        auto_create = data.get('auto_create', False)
        if auto_create or name:
            member_name = name if name else email.split('@')[0].capitalize()
            member_email = email.lower() if email else f"{member_name.lower().replace(' ', '')}@settleup.local"
            
            # Check if auto-generated email happens to exist
            existing = User.query.filter(db.func.lower(User.email) == member_email.lower()).first()
            if existing:
                user_to_add = existing
            else:
                user_to_add = User(
                    name=member_name,
                    email=member_email,
                    password_hash=hash_password('password123')
                )
                db.session.add(user_to_add)
                db.session.flush()
        else:
            return jsonify({'error': 'No user found with that email'}), 404

    # Check if already a member
    existing_membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_to_add.id).first()
    if existing_membership:
        return jsonify({'error': 'User is already a member of this group'}), 409

    new_member = GroupMember(group_id=group_id, user_id=user_to_add.id)
    db.session.add(new_member)
    db.session.commit()

    return jsonify({
        'message': f'{user_to_add.name} added to group',
        'group_id': group_id,
        'user_id': user_to_add.id,
        'user': {
            'id': user_to_add.id,
            'name': user_to_add.name,
            'email': user_to_add.email
        }
    }), 201


@groups_bp.route('/<int:group_id>/members', methods=['GET'])
@jwt_required()
def get_group_members(group_id):
    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    memberships = GroupMember.query.filter_by(group_id=group_id).all()
    return jsonify({
        'group_id': group_id,
        'members': [
            {
                'id': m.user.id,
                'name': m.user.name,
                'email': m.user.email,
                'joined_at': m.joined_at.isoformat() if m.joined_at else None
            }
            for m in memberships
        ]
    }), 200


@groups_bp.route('', methods=['GET'])
@jwt_required()
def list_my_groups():
    user_id = int(get_jwt_identity())

    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    groups = []
    for m in memberships:
        g = m.group
        member_count = GroupMember.query.filter_by(group_id=g.id).count()
        groups.append({
            'id': g.id,
            'name': g.name,
            'created_by': g.created_by,
            'member_count': member_count
        })

    return jsonify({'groups': groups}), 200


@groups_bp.route('/<int:group_id>', methods=['GET'])
@jwt_required()
def get_group(group_id):
    user_id = int(get_jwt_identity())
    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 403

    return jsonify({
        'group': {
            'id': group.id,
            'name': group.name,
            'created_by': group.created_by,
            'created_at': group.created_at.isoformat() if group.created_at else None
        }
    }), 200


@groups_bp.route('/<int:group_id>', methods=['DELETE'])
@jwt_required()
def delete_group(group_id):
    user_id = int(get_jwt_identity())
    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    if group.created_by != user_id:
        return jsonify({'error': 'Only the creator of this group can delete it'}), 403

    from app.models import Settlement, Expense, ExpenseSplit
    # Clean up settlements
    Settlement.query.filter_by(group_id=group_id).delete()
    # Clean up expenses and splits
    expenses = Expense.query.filter_by(group_id=group_id).all()
    for exp in expenses:
        ExpenseSplit.query.filter_by(expense_id=exp.id).delete()
        db.session.delete(exp)
    # Clean up memberships
    GroupMember.query.filter_by(group_id=group_id).delete()
    # Delete the group itself
    db.session.delete(group)
    db.session.commit()

    return jsonify({'message': 'Group deleted successfully'}), 200


@groups_bp.route('/<int:group_id>/leave', methods=['POST'])
@jwt_required()
def leave_group(group_id):
    from decimal import Decimal
    user_id = int(get_jwt_identity())
    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first()
    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 400

    from app.routes.expenses import compute_net_balances
    net_balance, _, _ = compute_net_balances(group_id)
    my_balance = net_balance[user_id].quantize(Decimal('0.01'))

    if abs(my_balance) > Decimal('0.005'):
        if my_balance < 0:
            return jsonify({
                'error': f'Cannot leave group: You still owe ₹{abs(my_balance)}. Please settle your dues first.'
            }), 400
        else:
            return jsonify({
                'error': f'Cannot leave group: You are still owed ₹{my_balance}. Please settle with other members first.'
            }), 400

    other_members = GroupMember.query.filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id != user_id
    ).order_by(GroupMember.joined_at.asc()).all()

    if group.created_by == user_id:
        if other_members:
            # Transfer group creator ownership to next joined member
            group.created_by = other_members[0].user_id
        else:
            # Last member leaving removes the group
            from app.models import Settlement, Expense, ExpenseSplit
            Settlement.query.filter_by(group_id=group_id).delete()
            expenses = Expense.query.filter_by(group_id=group_id).all()
            for exp in expenses:
                ExpenseSplit.query.filter_by(expense_id=exp.id).delete()
                db.session.delete(exp)
            db.session.delete(membership)
            db.session.delete(group)
            db.session.commit()
            return jsonify({'message': 'You left the group and the group was deleted'}), 200

    db.session.delete(membership)
    db.session.commit()

    return jsonify({'message': 'You have left the group successfully'}), 200


@groups_bp.route('/users', methods=['GET'])
@jwt_required()
def list_all_users():
    """Returns list of registered users for quick member selection/invitation."""
    current_user_id = int(get_jwt_identity())
    users = User.query.all()
    return jsonify({
        'users': [
            {'id': u.id, 'name': u.name, 'email': u.email}
            for u in users if u.id != current_user_id
        ]
    }), 200