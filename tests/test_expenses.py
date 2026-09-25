"""
Tests for expense and balance endpoints:
  POST /api/groups/<id>/expenses
  GET  /api/groups/<id>/expenses
  GET  /api/groups/<id>/balances
  GET  /api/groups/<id>/simplified-debts
"""
from decimal import Decimal
from tests.conftest import register_user, login_user, auth_headers


def setup_group_with_two_members(client):
    """
    Helper: creates Alice + Bob, a group, adds Bob.
    Returns (alice_token, bob_token, group_id).
    """
    register_user(client, name='Alice', email='alice@test.com', password='alicepass')
    register_user(client, name='Bob',   email='bob@test.com',   password='bobpass')

    alice_token = login_user(client, email='alice@test.com', password='alicepass')
    bob_token   = login_user(client, email='bob@test.com',   password='bobpass')

    resp = client.post('/api/groups', json={'name': 'Trip'},
                       headers=auth_headers(alice_token))
    group_id = resp.get_json()['group']['id']

    client.post(f'/api/groups/{group_id}/members',
                json={'email': 'bob@test.com'},
                headers=auth_headers(alice_token))

    return alice_token, bob_token, group_id


class TestAddExpense:
    def test_equal_split_success(self, client):
        """Equal split: Rs.100 / 2 = Rs.50 each."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'Hotel', 'amount': 100, 'split_type': 'equal'},
                           headers=auth_headers(alice_token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['expense']['amount'] == '100.00'
        splits = data['expense']['splits']
        assert len(splits) == 2
        # All shares must sum to the total
        total = sum(Decimal(s['amount_owed']) for s in splits)
        assert total == Decimal('100.00')

    def test_equal_split_remainder(self, client):
        """
        Rs.100 / 3 people — the remainder 1 paisa goes to the first person.
        Verifies: 33.34 + 33.33 + 33.33 = 100.00 exactly.
        """
        register_user(client, name='Alice',   email='alice@test.com',   password='alicepass')
        register_user(client, name='Bob',     email='bob@test.com',     password='bobpass')
        register_user(client, name='Charlie', email='charlie@test.com', password='charliepass')

        alice_token = login_user(client, email='alice@test.com', password='alicepass')

        resp = client.post('/api/groups', json={'name': 'Trip3'},
                           headers=auth_headers(alice_token))
        group_id = resp.get_json()['group']['id']

        client.post(f'/api/groups/{group_id}/members',
                    json={'email': 'bob@test.com'}, headers=auth_headers(alice_token))
        client.post(f'/api/groups/{group_id}/members',
                    json={'email': 'charlie@test.com'}, headers=auth_headers(alice_token))

        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'Dinner', 'amount': 100, 'split_type': 'equal'},
                           headers=auth_headers(alice_token))
        assert resp.status_code == 201
        splits = resp.get_json()['expense']['splits']
        total = sum(Decimal(s['amount_owed']) for s in splits)
        assert total == Decimal('100.00')  # no paisa lost!

    def test_exact_split_success(self, client):
        """Exact split: manually specified amounts must match total."""
        alice_token, _, group_id = setup_group_with_two_members(client)

        # Get member IDs dynamically — don't hardcode (SQLite resets per test)
        bal_resp = client.get(f'/api/groups/{group_id}/balances',
                              headers=auth_headers(alice_token))
        members = bal_resp.get_json()['balances']
        uid1, uid2 = members[0]['user_id'], members[1]['user_id']

        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={
                               'description': 'Cab',
                               'amount': 90,
                               'split_type': 'exact',
                               'splits': [
                                   {'user_id': uid1, 'amount': 60},
                                   {'user_id': uid2, 'amount': 30},
                               ]
                           },
                           headers=auth_headers(alice_token))
        assert resp.status_code == 201
        splits = resp.get_json()['expense']['splits']
        total = sum(Decimal(s['amount_owed']) for s in splits)
        assert total == Decimal('90.00')

    def test_exact_split_wrong_total(self, client):
        """If exact split amounts don't add up to total, return 400."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        bal_resp = client.get(f'/api/groups/{group_id}/balances',
                              headers=auth_headers(alice_token))
        members = bal_resp.get_json()['balances']
        uid1, uid2 = members[0]['user_id'], members[1]['user_id']

        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={
                               'description': 'Cab',
                               'amount': 100,
                               'split_type': 'exact',
                               'splits': [
                                   {'user_id': uid1, 'amount': 40},
                                   {'user_id': uid2, 'amount': 40},  # total = 80 ≠ 100
                               ]
                           },
                           headers=auth_headers(alice_token))
        assert resp.status_code == 400

    def test_percentage_split_success(self, client):
        """Percentage split: 60% + 40% of Rs.200."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        bal_resp = client.get(f'/api/groups/{group_id}/balances',
                              headers=auth_headers(alice_token))
        members = bal_resp.get_json()['balances']
        uid1, uid2 = members[0]['user_id'], members[1]['user_id']

        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={
                               'description': 'Grocery',
                               'amount': 200,
                               'split_type': 'percentage',
                               'splits': [
                                   {'user_id': uid1, 'percentage': 60},
                                   {'user_id': uid2, 'percentage': 40},
                               ]
                           },
                           headers=auth_headers(alice_token))
        assert resp.status_code == 201
        splits = resp.get_json()['expense']['splits']
        total = sum(Decimal(s['amount_owed']) for s in splits)
        assert total == Decimal('200.00')

    def test_percentage_must_sum_to_100(self, client):
        """Percentages not summing to 100 return 400."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        bal_resp = client.get(f'/api/groups/{group_id}/balances',
                              headers=auth_headers(alice_token))
        members = bal_resp.get_json()['balances']
        uid1, uid2 = members[0]['user_id'], members[1]['user_id']

        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={
                               'description': 'Grocery',
                               'amount': 200,
                               'split_type': 'percentage',
                               'splits': [
                                   {'user_id': uid1, 'percentage': 60},
                                   {'user_id': uid2, 'percentage': 30},  # 90 ≠ 100
                               ]
                           },
                           headers=auth_headers(alice_token))
        assert resp.status_code == 400

    def test_invalid_split_type(self, client):
        alice_token, _, group_id = setup_group_with_two_members(client)
        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'X', 'amount': 50, 'split_type': 'random'},
                           headers=auth_headers(alice_token))
        assert resp.status_code == 400

    def test_negative_amount(self, client):
        alice_token, _, group_id = setup_group_with_two_members(client)
        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'X', 'amount': -50, 'split_type': 'equal'},
                           headers=auth_headers(alice_token))
        assert resp.status_code == 400

    def test_non_member_cannot_add_expense(self, client):
        """A user not in the group gets 403."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        # Register a third user who's NOT in the group
        register_user(client, name='Eve', email='eve@test.com', password='evepass')
        eve_token = login_user(client, email='eve@test.com', password='evepass')

        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'X', 'amount': 50, 'split_type': 'equal'},
                           headers=auth_headers(eve_token))
        assert resp.status_code == 403


class TestBalances:
    def test_balance_after_expense(self, client):
        """
        Alice pays Rs.100, split equally with Bob.
        Alice should have +50 (owed), Bob -50 (owes).
        """
        alice_token, _, group_id = setup_group_with_two_members(client)
        client.post(f'/api/groups/{group_id}/expenses',
                    json={'description': 'Hotel', 'amount': 100, 'split_type': 'equal'},
                    headers=auth_headers(alice_token))

        resp = client.get(f'/api/groups/{group_id}/balances',
                          headers=auth_headers(alice_token))
        assert resp.status_code == 200
        balances = {b['name']: Decimal(b['balance'])
                    for b in resp.get_json()['balances']}
        assert balances['Alice'] == Decimal('50.00')
        assert balances['Bob']   == Decimal('-50.00')

    def test_balances_sum_to_zero(self, client):
        """All balances in a group must always sum to zero (money is conserved)."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        client.post(f'/api/groups/{group_id}/expenses',
                    json={'description': 'X', 'amount': 77, 'split_type': 'equal'},
                    headers=auth_headers(alice_token))

        resp = client.get(f'/api/groups/{group_id}/balances',
                          headers=auth_headers(alice_token))
        total = sum(Decimal(b['balance']) for b in resp.get_json()['balances'])
        assert total == Decimal('0.00')

    def test_simplified_debts(self, client):
        """After one expense, simplified debts should show 1 transaction."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        client.post(f'/api/groups/{group_id}/expenses',
                    json={'description': 'Lunch', 'amount': 100, 'split_type': 'equal'},
                    headers=auth_headers(alice_token))

        resp = client.get(f'/api/groups/{group_id}/simplified-debts',
                          headers=auth_headers(alice_token))
        assert resp.status_code == 200
        txns = resp.get_json()['transactions']
        assert len(txns) == 1
        assert txns[0]['amount'] == '50.00'


class TestEditExpense:
    def test_edit_expense_success(self, client):
        """Updating an expense recalculates splits and balances accurately."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'Dinner', 'amount': 100, 'split_type': 'equal'},
                           headers=auth_headers(alice_token))
        assert resp.status_code == 201
        exp_id = resp.get_json()['expense']['id']

        # Edit to 200
        edit_resp = client.put(f'/api/groups/{group_id}/expenses/{exp_id}',
                               json={'description': 'Fancy Dinner', 'amount': 200, 'split_type': 'equal'},
                               headers=auth_headers(alice_token))
        assert edit_resp.status_code == 200
        data = edit_resp.get_json()['expense']
        assert data['description'] == 'Fancy Dinner'
        assert data['amount'] == '200.00'

        # Check balances
        bal_resp = client.get(f'/api/groups/{group_id}/balances', headers=auth_headers(alice_token))
        balances = {b['name']: Decimal(b['balance']) for b in bal_resp.get_json()['balances']}
        assert balances['Alice'] == Decimal('100.00')
        assert balances['Bob'] == Decimal('-100.00')

    def test_edit_expense_exact_split(self, client):
        """Updating an expense to exact splits."""
        alice_token, _, group_id = setup_group_with_two_members(client)
        # Register Eve to have user IDs
        alice_id = 1
        bob_id = 2
        resp = client.post(f'/api/groups/{group_id}/expenses',
                           json={'description': 'Cab', 'amount': 100, 'split_type': 'equal'},
                           headers=auth_headers(alice_token))
        exp_id = resp.get_json()['expense']['id']

        edit_resp = client.put(f'/api/groups/{group_id}/expenses/{exp_id}',
                               json={
                                   'description': 'Cab',
                                   'amount': 100,
                                   'split_type': 'exact',
                                   'splits': [
                                       {'user_id': alice_id, 'amount': 30},
                                       {'user_id': bob_id, 'amount': 70}
                                   ]
                               },
                               headers=auth_headers(alice_token))
        assert edit_resp.status_code == 200
        bal_resp = client.get(f'/api/groups/{group_id}/balances', headers=auth_headers(alice_token))
        balances = {b['name']: Decimal(b['balance']) for b in bal_resp.get_json()['balances']}
        assert balances['Alice'] == Decimal('70.00')
        assert balances['Bob'] == Decimal('-70.00')

