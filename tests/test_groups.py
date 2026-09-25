"""
Tests for group endpoints:
  POST /api/groups
  GET  /api/groups
  POST /api/groups/<id>/members
"""
from tests.conftest import register_user, login_user, auth_headers


def setup_user_and_group(client, name='Alice', email='alice@test.com'):
    """Helper: register, login, create a group. Returns (token, group_id)."""
    register_user(client, name=name, email=email)
    token = login_user(client, email=email)
    resp = client.post('/api/groups', json={'name': 'Goa Trip'},
                       headers=auth_headers(token))
    group_id = resp.get_json()['group']['id']
    return token, group_id


class TestCreateGroup:
    def test_create_group_success(self, client):
        """Creating a group returns 201 with group info."""
        register_user(client)
        token = login_user(client)
        resp = client.post('/api/groups', json={'name': 'Road Trip'},
                           headers=auth_headers(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['group']['name'] == 'Road Trip'

    def test_create_group_auto_adds_creator(self, client):
        """The creator is automatically added as a member."""
        register_user(client)
        token = login_user(client)
        client.post('/api/groups', json={'name': 'Trip'}, headers=auth_headers(token))
        resp = client.get('/api/groups', headers=auth_headers(token))
        groups = resp.get_json()['groups']
        assert len(groups) == 1
        assert groups[0]['name'] == 'Trip'

    def test_create_group_missing_name(self, client):
        """Missing group name returns 400."""
        register_user(client)
        token = login_user(client)
        resp = client.post('/api/groups', json={}, headers=auth_headers(token))
        assert resp.status_code == 400

    def test_create_group_requires_auth(self, client):
        resp = client.post('/api/groups', json={'name': 'Trip'})
        assert resp.status_code == 401


class TestListGroups:
    def test_list_groups(self, client):
        """User only sees groups they belong to."""
        register_user(client, name='Alice', email='alice@test.com')
        token = login_user(client, email='alice@test.com')

        client.post('/api/groups', json={'name': 'Group A'}, headers=auth_headers(token))
        client.post('/api/groups', json={'name': 'Group B'}, headers=auth_headers(token))

        resp = client.get('/api/groups', headers=auth_headers(token))
        assert resp.status_code == 200
        names = [g['name'] for g in resp.get_json()['groups']]
        assert 'Group A' in names
        assert 'Group B' in names

    def test_list_groups_requires_auth(self, client):
        resp = client.get('/api/groups')
        assert resp.status_code == 401


class TestAddMember:
    def test_add_member_success(self, client):
        """Adding a registered user to a group returns 201."""
        token, group_id = setup_user_and_group(client)
        # Register Bob
        register_user(client, name='Bob', email='bob@test.com', password='bobpass')

        resp = client.post(f'/api/groups/{group_id}/members',
                           json={'email': 'bob@test.com'},
                           headers=auth_headers(token))
        assert resp.status_code == 201

    def test_add_member_duplicate(self, client):
        """Adding an already-existing member returns 409."""
        token, group_id = setup_user_and_group(client)
        register_user(client, name='Bob', email='bob@test.com', password='bobpass')

        client.post(f'/api/groups/{group_id}/members',
                    json={'email': 'bob@test.com'}, headers=auth_headers(token))
        resp = client.post(f'/api/groups/{group_id}/members',
                           json={'email': 'bob@test.com'}, headers=auth_headers(token))
        assert resp.status_code == 409

    def test_add_nonexistent_user(self, client):
        """Adding an email not in the system returns 404."""
        token, group_id = setup_user_and_group(client)
        resp = client.post(f'/api/groups/{group_id}/members',
                           json={'email': 'ghost@test.com'},
                           headers=auth_headers(token))
        assert resp.status_code == 404

    def test_add_member_to_nonexistent_group(self, client):
        """Adding to a group that doesn't exist returns 404."""
        register_user(client)
        token = login_user(client)
        resp = client.post('/api/groups/9999/members',
                           json={'email': 'alice@test.com'},
                           headers=auth_headers(token))
        assert resp.status_code == 404
