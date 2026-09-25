from app import db
from datetime import datetime, UTC


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)  # filename of uploaded avatar
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f'<User {self.email}>'


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    members = db.relationship('GroupMember', backref='group', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Group {self.name}>'


class GroupMember(db.Model):
    __tablename__ = 'group_members'

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    user = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint('group_id', 'user_id', name='unique_group_user'),
    )

    def __repr__(self):
        return f'<GroupMember user={self.user_id} group={self.group_id}>'


# --- Expense Models ---
# An Expense = one bill/payment event (e.g. "Alice paid ₹900 for hotel")
# An ExpenseSplit = each person's share of that bill

class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)

    # Which group this expense belongs to
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)

    # Who actually paid the bill (they are owed money by others)
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Human-readable label like "Hotel", "Dinner", "Cab"
    description = db.Column(db.String(255), nullable=False)

    # IMPORTANT: We use Numeric(10, 2), NOT Float.
    # Float can give results like 33.333333... which causes rounding errors.
    # Numeric stores exact decimal values (like a real calculator).
    # (10, 2) means up to 10 digits total, 2 after the decimal point — e.g. 99999999.99
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    # How should this bill be split?
    # 'equal'      — divide equally among all members
    # 'exact'      — each person's share is specified manually (in rupees)
    # 'percentage' — each person's share is specified as a % (must sum to 100)
    split_type = db.Column(
        db.Enum('equal', 'exact', 'percentage', name='split_type_enum',
                native_enum=False),   # native_enum=False = store as VARCHAR in SQLite
        nullable=False,
        default='equal'
    )

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # Relationships — makes it easy to do expense.splits or expense.payer
    splits = db.relationship('ExpenseSplit', backref='expense', cascade='all, delete-orphan')
    payer = db.relationship('User', foreign_keys=[paid_by])

    def __repr__(self):
        return f'<Expense {self.description} ₹{self.amount}>'


class ExpenseSplit(db.Model):
    __tablename__ = 'expense_splits'

    id = db.Column(db.Integer, primary_key=True)

    # Which expense this split belongs to
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)

    # Which user owes money
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Exact amount this person owes — again, Numeric not Float!
    amount_owed = db.Column(db.Numeric(10, 2), nullable=False)

    # Easy access: split.user gives the User object
    user = db.relationship('User')

    def __repr__(self):
        return f'<ExpenseSplit user={self.user_id} owes={self.amount_owed}>'


# --- Settlement Model ---
# A Settlement records a real-world repayment event.
# e.g. "Bob paid Alice ₹173.33 via UPI to settle his debt"
#
# Important distinction:
#   Expense  = someone paid a bill on behalf of the group (creates debt)
#   Settlement = someone repaid their debt (reduces debt)
#
# Both must be considered when calculating net balances.

class Settlement(db.Model):
    __tablename__ = 'settlements'

    id = db.Column(db.Integer, primary_key=True)

    # Which group this repayment belongs to
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)

    # Who sent the money (the debtor paying off their debt)
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Who received the money (the creditor being repaid)
    paid_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # How much was transferred — Numeric, never Float
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Optional note: "UPI", "Cash", "Bank transfer", etc.
    note = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))

    # Relationships for easy access: settlement.sender / settlement.receiver
    sender   = db.relationship('User', foreign_keys=[paid_by])
    receiver = db.relationship('User', foreign_keys=[paid_to])

    def __repr__(self):
        return f'<Settlement {self.paid_by}→{self.paid_to} ₹{self.amount}>'