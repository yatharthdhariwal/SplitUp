"""
Tests for settlement endpoints:
  POST /api/groups/<id>/settlements
  GET  /api/groups/<id>/settlements
"""
from decimal import Decimal
from tests.conftest import register_user, login_user, auth_headers


def setup_group_with_expense(client):
    """
    Helper: Alice + Bob in a group, Alice paid Rs.100 equal split.
    Bob owes Alice Rs.50.
    Returns (alice_token, bob_token, group_id, alice_id).
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

    # Alice pays Rs.100, split equally → Bob owes Rs.50
    client.post(f'/api/groups/{group_id}/expenses',
                json={'description': 'Hotel', 'amount': 100, 'split_type': 'equal'},
                headers=auth_headers(alice_token))

    # Get Alice's user_id dynamically from the balance response
    bal = client.get(f'/api/groups/{group_id}/balances',
                     headers=auth_headers(alice_token)).get_json()['balances']
    alice_id = next(b['user_id'] for b in bal if b['name'] == 'Alice')

    return alice_token, bob_token, group_id, alice_id


class TestRecordSettlement:
    def test_record_settlement_success(self, client):
        """Bob records paying Alice Rs.50 — returns 201."""
        alice_token, bob_token, group_id, alice_id = setup_group_with_expense(client)

        resp = client.post(f'/api/groups/{group_id}/settlements',
                           json={'paid_to': alice_id, 'amount': 50, 'note': 'UPI'},
                           headers=auth_headers(bob_token))
        assert resp.status_code == 201
        data = resp.get_json()['settlement']
        assert data['amount'] == '50.00'
        assert data['note'] == 'UPI'
        assert data['paid_by']['name'] == 'Bob'
        assert data['paid_to']['name'] == 'Alice'

    def test_settlement_updates_balance_to_zero(self, client):
        """After Bob fully settles, everyone's balance should be 0."""
        alice_token, bob_token, group_id, alice_id = setup_group_with_expense(client)

        # Bob pays Alice the full Rs.50 he owes
        client.post(f'/api/groups/{group_id}/settlements',
                    json={'paid_to': alice_id, 'amount': 50},
                    headers=auth_headers(bob_token))

        resp = client.get(f'/api/groups/{group_id}/balances',
                          headers=auth_headers(alice_token))
        balances = {b['name']: b['status'] for b in resp.get_json()['balances']}
        assert balances['Alice'] == 'settled'
        assert balances['Bob']   == 'settled'

    def test_simplified_debts_empty_after_settlement(self, client):
        """After full settlement, simplified-debts returns 0 transactions."""
        alice_token, bob_token, group_id, alice_id = setup_group_with_expense(client)

        client.post(f'/api/groups/{group_id}/settlements',
                    json={'paid_to': alice_id, 'amount': 50},
                    headers=auth_headers(bob_token))

        resp = client.get(f'/api/groups/{group_id}/simplified-debts',
                          headers=auth_headers(alice_token))
        assert len(resp.get_json()['transactions']) == 0

    def test_partial_settlement(self, client):
        """Partial payment reduces — but does not eliminate — the debt."""
        alice_token, bob_token, group_id, alice_id = setup_group_with_expense(client)

        # Bob only pays Rs.20 of the Rs.50 he owes
        client.post(f'/api/groups/{group_id}/settlements',
                    json={'paid_to': alice_id, 'amount': 20},
                    headers=auth_headers(bob_token))

        resp = client.get(f'/api/groups/{group_id}/balances',
                          headers=auth_headers(alice_token))
        balances = {b['name']: Decimal(b['balance'])
                    for b in resp.get_json()['balances']}
        assert balances['Alice'] == Decimal('30.00')   # still owed Rs.30
        assert balances['Bob']   == Decimal('-30.00')  # still owes Rs.30

    def test_cannot_pay_yourself(self, client):
        """A user cannot record a settlement to themselves — returns 400."""
        alice_token, _, group_id, alice_id = setup_group_with_expense(client)

        resp = client.post(f'/api/groups/{group_id}/settlements',
                           json={'paid_to': alice_id, 'amount': 50},
                           headers=auth_headers(alice_token))  # Alice paying Alice
        assert resp.status_code == 400

    def test_settlement_missing_amount(self, client):
        _, bob_token, group_id, alice_id = setup_group_with_expense(client)
        resp = client.post(f'/api/groups/{group_id}/settlements',
                           json={'paid_to': alice_id},
                           headers=auth_headers(bob_token))
        assert resp.status_code == 400

    def test_settlement_negative_amount(self, client):
        _, bob_token, group_id, alice_id = setup_group_with_expense(client)
        resp = client.post(f'/api/groups/{group_id}/settlements',
                           json={'paid_to': alice_id, 'amount': -50},
                           headers=auth_headers(bob_token))
        assert resp.status_code == 400

    def test_creditor_can_record_settlement_on_behalf_of_debtor(self, client):
        """Alice (creditor) records that Bob (debtor) paid her Rs.50 — settles both to 0."""
        alice_token, bob_token, group_id, alice_id = setup_group_with_expense(client)

        # Get Bob's ID
        bal = client.get(f'/api/groups/{group_id}/balances',
                         headers=auth_headers(alice_token)).get_json()['balances']
        bob_id = next(b['user_id'] for b in bal if b['name'] == 'Bob')

        # Alice records that Bob paid Alice
        resp = client.post(f'/api/groups/{group_id}/settlements',
                           json={'paid_by': bob_id, 'paid_to': alice_id, 'amount': 50, 'note': 'Cash received'},
                           headers=auth_headers(alice_token))
        assert resp.status_code == 201
        data = resp.get_json()['settlement']
        assert data['paid_by']['name'] == 'Bob'
        assert data['paid_to']['name'] == 'Alice'

        # Check balances are settled (0)
        bal_resp = client.get(f'/api/groups/{group_id}/balances',
                              headers=auth_headers(alice_token))
        balances = {b['name']: b['status'] for b in bal_resp.get_json()['balances']}
        assert balances['Alice'] == 'settled'
        assert balances['Bob']   == 'settled'

    def test_non_member_cannot_settle(self, client):
        """A user outside the group gets 403."""
        _, _, group_id, alice_id = setup_group_with_expense(client)
        register_user(client, name='Eve', email='eve@test.com', password='evepass')
        eve_token = login_user(client, email='eve@test.com', password='evepass')

        resp = client.post(f'/api/groups/{group_id}/settlements',
                           json={'paid_to': alice_id, 'amount': 50},
                           headers=auth_headers(eve_token))
        assert resp.status_code == 403


class TestListSettlements:
    def test_list_settlements(self, client):
        """Settlement history is returned in reverse chronological order."""
        alice_token, bob_token, group_id, alice_id = setup_group_with_expense(client)

        client.post(f'/api/groups/{group_id}/settlements',
                    json={'paid_to': alice_id, 'amount': 25, 'note': 'First'},
                    headers=auth_headers(bob_token))
        client.post(f'/api/groups/{group_id}/settlements',
                    json={'paid_to': alice_id, 'amount': 25, 'note': 'Second'},
                    headers=auth_headers(bob_token))

        resp = client.get(f'/api/groups/{group_id}/settlements',
                          headers=auth_headers(alice_token))
        assert resp.status_code == 200
        settlements = resp.get_json()['settlements']
        assert len(settlements) == 2
        # Most recent first
        assert settlements[0]['note'] == 'Second'
        assert settlements[1]['note'] == 'First'

    def test_list_settlements_requires_auth(self, client):
        resp = client.get('/api/groups/1/settlements')
        assert resp.status_code == 401
