from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal
from app import db
from app.models import Group, GroupMember, Settlement, User

settlements_bp = Blueprint('settlements', __name__, url_prefix='/api/groups')


# ---------------------------------------------------------------------------
# POST /api/groups/<group_id>/settlements  — Record a repayment
# ---------------------------------------------------------------------------
#
# CONCEPT:
# When Bob actually pays Alice back ₹173.33 (via UPI, cash, etc.),
# we record it here. This reduces Bob's debt and Alice's credit.
#
# Who calls this? The PAYER (Bob) calls this endpoint to log that he paid.
# But in practice, either party could record it — it's an admin action.
# For now, any group member can record a settlement (we can lock this
# down later to only the payer or group admin).
#
# Request body:
#   {
#     "paid_to":  2,           ← user_id of the person receiving money
#     "amount":   173.33,
#     "note":     "UPI 9876543210"   (optional)
#   }
#
@settlements_bp.route('/<int:group_id>/settlements', methods=['POST'])
@jwt_required()
def record_settlement(group_id):
    user_id = int(get_jwt_identity())  # the logged-in user = the payer

    # --- 1. Auth: caller must be a group member ---
    if not GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first():
        return jsonify({'error': 'You are not a member of this group'}), 403

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    data = request.get_json()

    # --- 2. Validate input ---
    paid_by_raw = data.get('paid_by')
    paid_to_raw = data.get('paid_to')
    amount_raw  = data.get('amount')
    note        = (data.get('note') or '').strip() or None  # None if empty/null

    if paid_to_raw is None:
        return jsonify({'error': 'paid_to (user_id) is required'}), 400
    if amount_raw is None:
        return jsonify({'error': 'amount is required'}), 400

    try:
        paid_to_id = int(paid_to_raw)
    except (ValueError, TypeError):
        return jsonify({'error': 'paid_to must be a valid integer user id'}), 400

    if paid_by_raw is not None:
        try:
            paid_by_id = int(paid_by_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'paid_by must be a valid integer user id'}), 400
    else:
        paid_by_id = user_id

    # Payer and receiver cannot be the same person
    if paid_to_id == paid_by_id:
        return jsonify({'error': 'Payer and recipient cannot be the same user'}), 400

    try:
        amount = Decimal(str(amount_raw)).quantize(Decimal('0.01'))
    except Exception:
        return jsonify({'error': 'amount must be a valid number'}), 400

    if amount <= 0:
        return jsonify({'error': 'amount must be greater than 0'}), 400

    # --- 3. Check that both payer and recipient are group members ---
    if not GroupMember.query.filter_by(group_id=group_id, user_id=paid_by_id).first():
        return jsonify({'error': 'The payer (paid_by) is not a member of this group'}), 400

    if not GroupMember.query.filter_by(group_id=group_id, user_id=paid_to_id).first():
        return jsonify({'error': 'The recipient (paid_to) is not a member of this group'}), 400

    payer = db.session.get(User, paid_by_id)
    recipient = db.session.get(User, paid_to_id)
    if not payer or not recipient:
        return jsonify({'error': 'User not found'}), 404

    # --- 4. Save the settlement ---
    settlement = Settlement(
        group_id=group_id,
        paid_by=paid_by_id,
        paid_to=paid_to_id,
        amount=amount,
        note=note
    )
    db.session.add(settlement)
    db.session.commit()

    return jsonify({
        'message': f'Settlement recorded: {payer.name} paid {recipient.name} ₹{amount}',
        'settlement': {
            'id':       settlement.id,
            'paid_by':  {'id': paid_by_id, 'name': payer.name},
            'paid_to':  {'id': paid_to_id, 'name': recipient.name},
            'amount':   str(settlement.amount),
            'note':     settlement.note,
            'created_at': settlement.created_at.isoformat()
        }
    }), 201


# ---------------------------------------------------------------------------
# GET /api/groups/<group_id>/settlements  — List all settlements in a group
# ---------------------------------------------------------------------------
#
# Returns a chronological log of all repayments in this group.
# Useful as a payment history / audit trail.
#
@settlements_bp.route('/<int:group_id>/settlements', methods=['GET'])
@jwt_required()
def list_settlements(group_id):
    user_id = int(get_jwt_identity())

    if not GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first():
        return jsonify({'error': 'You are not a member of this group'}), 403

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    settlements = Settlement.query.filter_by(group_id=group_id)\
        .order_by(Settlement.created_at.desc()).all()

    result = []
    for s in settlements:
        result.append({
            'id':       s.id,
            'paid_by':  {'id': s.paid_by, 'name': s.sender.name},
            'paid_to':  {'id': s.paid_to, 'name': s.receiver.name},
            'amount':   str(s.amount),
            'note':     s.note,
            'created_at': s.created_at.isoformat()
        })

    return jsonify({
        'group_id':    group_id,
        'group_name':  group.name,
        'settlements': result
    }), 200
