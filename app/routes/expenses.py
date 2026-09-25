from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, ROUND_DOWN
from collections import defaultdict
from app import db
from app.models import Group, GroupMember, Expense, ExpenseSplit, User

expenses_bp = Blueprint('expenses', __name__, url_prefix='/api/groups')


# ---------------------------------------------------------------------------
# POST /api/groups/<group_id>/expenses  — Add a new expense to a group
# ---------------------------------------------------------------------------
#
# Why is this inside /api/groups/<id>/expenses instead of /api/expenses?
# Because an expense always belongs to a group. Nesting the URL this way
# makes the relationship obvious and the API more RESTful.
#
@expenses_bp.route('/<int:group_id>/expenses', methods=['POST'])
@jwt_required()
def add_expense(group_id):
    user_id = int(get_jwt_identity())  # convert string → int (JWT stores as string)
    data = request.get_json()

    # --- 1. Validate required fields ---
    description = data.get('description', '').strip()
    amount_raw   = data.get('amount')
    split_type   = data.get('split_type', 'equal')

    if not description:
        return jsonify({'error': 'description is required'}), 400
    if amount_raw is None:
        return jsonify({'error': 'amount is required'}), 400
    if split_type not in ('equal', 'exact', 'percentage'):
        return jsonify({'error': 'split_type must be equal, exact, or percentage'}), 400

    # Convert amount to Decimal for precise arithmetic (never use float for money!)
    try:
        amount = Decimal(str(amount_raw)).quantize(Decimal('0.01'))
    except Exception:
        return jsonify({'error': 'amount must be a valid number'}), 400

    if amount <= 0:
        return jsonify({'error': 'amount must be greater than 0'}), 400

    # --- 2. Check the group exists ---
    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    # --- 3. Check that the logged-in user is a member of this group ---
    caller_membership = GroupMember.query.filter_by(
        group_id=group_id, user_id=user_id
    ).first()
    if not caller_membership:
        return jsonify({'error': 'You are not a member of this group'}), 403

    # Validate paid_by if provided (defaults to caller)
    paid_by_raw = data.get('paid_by')
    if paid_by_raw is not None:
        try:
            payer_id = int(paid_by_raw)
        except (ValueError, TypeError):
            return jsonify({'error': 'paid_by must be a valid integer user id'}), 400
        if not GroupMember.query.filter_by(group_id=group_id, user_id=payer_id).first():
            return jsonify({'error': 'The payer (paid_by) is not a member of this group'}), 400
    else:
        payer_id = user_id

    # --- 4. Get all group members ---
    memberships = GroupMember.query.filter_by(group_id=group_id).all()
    member_ids = [m.user_id for m in memberships]

    # --- 5. Calculate each person's share based on split_type ---

    if split_type == 'equal':
        # Optional subset of members to split among
        split_members = data.get('split_members') or data.get('members')
        if split_members and isinstance(split_members, list) and len(split_members) > 0:
            target_member_ids = [int(uid) for uid in split_members if int(uid) in member_ids]
        else:
            target_member_ids = member_ids

        n = len(target_member_ids)
        if n == 0:
            return jsonify({'error': 'At least one group member must be included in the split'}), 400

        total_paisa = int(amount * 100)       # e.g. ₹100.00 → 10000
        base_paisa  = total_paisa // n         # e.g. 10000 // 3 = 3333
        remainder   = total_paisa % n          # e.g. 10000 % 3  = 1

        splits_data = []
        for i, uid in enumerate(target_member_ids):
            # The first `remainder` people get 1 extra paisa
            share_paisa = base_paisa + (1 if i < remainder else 0)
            share_amount = Decimal(share_paisa) / Decimal(100)
            splits_data.append({'user_id': uid, 'amount_owed': share_amount})

    elif split_type == 'exact':
        # EXACT SPLIT — the caller specifies each person's exact share.
        # Request body must include: "splits": [{"user_id": 1, "amount": 50}, ...]
        splits_input = data.get('splits', [])
        if not splits_input:
            return jsonify({'error': 'splits array is required for exact split'}), 400

        # Validate that the splits cover exactly the right people and amount
        splits_data = []
        total_specified = Decimal('0')
        for s in splits_input:
            uid = s.get('user_id')
            amt = s.get('amount')
            if uid not in member_ids:
                return jsonify({'error': f'user_id {uid} is not a member of this group'}), 400
            try:
                share = Decimal(str(amt)).quantize(Decimal('0.01'))
            except Exception:
                return jsonify({'error': f'Invalid amount for user {uid}'}), 400
            total_specified += share
            splits_data.append({'user_id': uid, 'amount_owed': share})

        # The specified amounts must add up to the total (within 1 paisa tolerance)
        if abs(total_specified - amount) > Decimal('0.01'):
            return jsonify({
                'error': f'Split amounts ({total_specified}) must add up to total ({amount})'
            }), 400

    elif split_type == 'percentage':
        # PERCENTAGE SPLIT — the caller specifies each person's % share.
        # Request body must include: "splits": [{"user_id": 1, "percentage": 50}, ...]
        # Percentages must sum to 100.
        splits_input = data.get('splits', [])
        if not splits_input:
            return jsonify({'error': 'splits array is required for percentage split'}), 400

        splits_data = []
        total_pct = Decimal('0')

        # First pass: collect and validate all percentages
        entries = []
        for s in splits_input:
            uid = s.get('user_id')
            pct = s.get('percentage')
            if uid not in member_ids:
                return jsonify({'error': f'user_id {uid} is not a member of this group'}), 400
            try:
                pct_val = Decimal(str(pct))
            except Exception:
                return jsonify({'error': f'Invalid percentage for user {uid}'}), 400
            total_pct += pct_val
            entries.append((uid, pct_val))

        if abs(total_pct - Decimal('100')) > Decimal('0.01'):
            return jsonify({'error': f'Percentages must sum to 100, got {total_pct}'}), 400

        # Second pass: convert % to actual amounts using paisa arithmetic
        # (same remainder trick as equal split to avoid rounding errors)
        total_paisa = int(amount * 100)
        assigned_paisa = 0
        for i, (uid, pct_val) in enumerate(entries):
            if i < len(entries) - 1:
                # Normal case: compute this person's share
                share_paisa = int((pct_val / Decimal('100')) * total_paisa)
            else:
                # Last person absorbs whatever is left — guarantees total is exact
                share_paisa = total_paisa - assigned_paisa
            assigned_paisa += share_paisa
            share_amount = Decimal(share_paisa) / Decimal(100)
            splits_data.append({'user_id': uid, 'amount_owed': share_amount})

    # --- 6. Save everything to the database ---
    # We create the Expense first, then attach the splits.
    # db.session.flush() gets the expense.id before commit so we can use it.
    expense = Expense(
        group_id=group_id,
        paid_by=payer_id,
        description=description,
        amount=amount,
        split_type=split_type
    )
    db.session.add(expense)
    db.session.flush()  # assigns expense.id without committing yet

    for s in splits_data:
        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=s['user_id'],
            amount_owed=s['amount_owed']
        )
        db.session.add(split)

    db.session.commit()

    # --- 7. Build a nice response ---
    return jsonify({
        'message': 'Expense added successfully',
        'expense': {
            'id': expense.id,
            'description': expense.description,
            'amount': str(expense.amount),  # str() to preserve exact decimal representation
            'split_type': expense.split_type,
            'paid_by': expense.paid_by,
            'splits': [
                {
                    'user_id': s['user_id'],
                    'amount_owed': str(s['amount_owed'])
                }
                for s in splits_data
            ]
        }
    }), 201


# ---------------------------------------------------------------------------
# GET /api/groups/<group_id>/expenses  — List all expenses in a group
# ---------------------------------------------------------------------------
@expenses_bp.route('/<int:group_id>/expenses', methods=['GET'])
@jwt_required()
def list_expenses(group_id):
    user_id = int(get_jwt_identity())

    # Only group members can see the expenses
    membership = GroupMember.query.filter_by(
        group_id=group_id, user_id=user_id
    ).first()
    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 403

    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.created_at.desc()).all()

    result = []
    for exp in expenses:
        result.append({
            'id': exp.id,
            'description': exp.description,
            'amount': str(exp.amount),
            'split_type': exp.split_type,
            'paid_by': {
                'id': exp.payer.id,
                'name': exp.payer.name
            },
            'splits': [
                {
                    'user_id': s.user_id,
                    'name': s.user.name,
                    'amount_owed': str(s.amount_owed)
                }
                for s in exp.splits
            ],
            'created_at': exp.created_at.isoformat()
        })

    return jsonify({'expenses': result}), 200


# ---------------------------------------------------------------------------
# SHARED HELPER: compute_net_balances(group_id)
# ---------------------------------------------------------------------------
#
# This function is used by BOTH /balances and /simplified-debts.
# Extracting it avoids copy-pasting the same logic — this is called
# the DRY principle: "Don't Repeat Yourself."
#
# It now also factors in SETTLEMENTS:
#   When Bob pays Alice ₹100 as a settlement:
#     Bob's net goes UP by 100   (he owes less)
#     Alice's net goes DOWN by 100 (she is owed less)
#
# Formula per user:
#   net = Σ(expenses paid by user)
#       - Σ(split amounts owed by user)
#       + Σ(settlements sent by user as paid_by)   ← repayments Bob made
#       - Σ(settlements received by user as paid_to) ← repayments Alice received
#
def compute_net_balances(group_id):
    """
    Returns (net_balance dict, member_ids list, user_map dict).
    net_balance[user_id] = Decimal net amount (+ = owed, - = owes).
    Accounts for both expenses/splits AND settlements.
    """
    from app.models import Settlement  # local import to avoid circular dependency

    memberships = GroupMember.query.filter_by(group_id=group_id).all()
    member_ids  = [m.user_id for m in memberships]

    net_balance = defaultdict(lambda: Decimal('0'))

    # --- Factor in expenses ---
    expenses = Expense.query.filter_by(group_id=group_id).all()
    for exp in expenses:
        net_balance[exp.paid_by] += Decimal(str(exp.amount))
        for split in exp.splits:
            net_balance[split.user_id] -= Decimal(str(split.amount_owed))

    # --- Factor in settlements ---
    # A settlement reduces the debt of the payer and the credit of the receiver
    settlements = Settlement.query.filter_by(group_id=group_id).all()
    for s in settlements:
        net_balance[s.paid_by] += Decimal(str(s.amount))  # debtor paid → owes less
        net_balance[s.paid_to] -= Decimal(str(s.amount))  # creditor received → owed less

    user_map = {u.id: u for u in User.query.filter(User.id.in_(member_ids)).all()}

    return net_balance, member_ids, user_map


# ---------------------------------------------------------------------------
# GET /api/groups/<group_id>/balances  — Net balance per member
# ---------------------------------------------------------------------------
#
# net > 0  → you are owed money  (status: "owed")
# net < 0  → you owe money       (status: "owes")
# net = 0  → you're settled      (status: "settled")
#
@expenses_bp.route('/<int:group_id>/balances', methods=['GET'])
@jwt_required()
def get_balances(group_id):
    user_id = int(get_jwt_identity())

    if not GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first():
        return jsonify({'error': 'You are not a member of this group'}), 403

    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    # Use shared helper — includes settlements automatically
    net_balance, member_ids, user_map = compute_net_balances(group_id)

    balances = []
    for uid in member_ids:
        bal = net_balance[uid].quantize(Decimal('0.01'))
        balances.append({
            'user_id': uid,
            'name':    user_map[uid].name,
            'balance': str(bal),
            'status':  'owed' if bal > 0 else ('owes' if bal < 0 else 'settled')
        })

    return jsonify({
        'group_id':   group_id,
        'group_name': group.name,
        'balances':   balances
    }), 200


# ---------------------------------------------------------------------------
# GET /api/groups/<group_id>/simplified-debts  — Who pays whom to settle up
# ---------------------------------------------------------------------------
#
# Uses the greedy algorithm to minimise transaction count.
# See inline comments for a step-by-step explanation.
#
@expenses_bp.route('/<int:group_id>/simplified-debts', methods=['GET'])
@jwt_required()
def get_simplified_debts(group_id):
    user_id = int(get_jwt_identity())

    if not GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first():
        return jsonify({'error': 'You are not a member of this group'}), 403

    group = Group.query.get(group_id)
    if not group:
        return jsonify({'error': 'Group not found'}), 404

    # Use shared helper — includes settlements automatically
    net_balance, member_ids, user_map = compute_net_balances(group_id)

    creditors = []
    debtors   = []
    for uid in member_ids:
        bal = net_balance[uid].quantize(Decimal('0.01'))
        if bal > 0:
            creditors.append([bal, uid])
        elif bal < 0:
            debtors.append([abs(bal), uid])

    creditors.sort(reverse=True)
    debtors.sort(reverse=True)

    transactions = []
    i, j = 0, 0

    while i < len(creditors) and j < len(debtors):
        credit_amt, creditor_id = creditors[i]
        debt_amt,   debtor_id   = debtors[j]

        payment = min(credit_amt, debt_amt)

        transactions.append({
            'from':   {'id': debtor_id,   'name': user_map[debtor_id].name},
            'to':     {'id': creditor_id, 'name': user_map[creditor_id].name},
            'amount': str(payment.quantize(Decimal('0.01')))
        })

        creditors[i][0] -= payment
        debtors[j][0]   -= payment

        if creditors[i][0] == 0:
            i += 1
        if debtors[j][0] == 0:
            j += 1

    return jsonify({
        'group_id':     group_id,
        'group_name':   group.name,
        'transactions': transactions,
        'message':      f'{len(transactions)} payment(s) needed to settle this group'
    }), 200

