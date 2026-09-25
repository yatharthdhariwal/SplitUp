"""
Tests for authentication endpoints:
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/auth/me
"""
from tests.conftest import register_user, login_user, auth_headers


class TestRegister:
    def test_register_success(self, client):
        """A new user with valid data gets a 201 response."""
        resp = register_user(client)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['user']['email'] == 'alice@test.com'
        assert data['user']['name'] == 'Alice'
        assert 'password' not in data['user']  # never return the password!

    def test_register_duplicate_email(self, client):
        """Registering the same email twice returns 409 Conflict."""
        register_user(client)
        resp = register_user(client)  # same email again
        assert resp.status_code == 409

    def test_register_missing_name(self, client):
        """Missing required fields returns 400."""
        resp = client.post('/api/auth/register', json={
            'email': 'bob@test.com', 'password': 'pass123'
            # name is missing
        })
        assert resp.status_code == 400

    def test_register_missing_email(self, client):
        resp = client.post('/api/auth/register', json={
            'name': 'Bob', 'password': 'pass123'
        })
        assert resp.status_code == 400

    def test_register_missing_password(self, client):
        resp = client.post('/api/auth/register', json={
            'name': 'Bob', 'email': 'bob@test.com'
        })
        assert resp.status_code == 400

    def test_register_empty_body(self, client):
        resp = client.post('/api/auth/register', json={})
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        """Valid credentials return 200 with an access_token."""
        register_user(client)
        resp = client.post('/api/auth/login', json={
            'email': 'alice@test.com', 'password': 'secret123'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'alice@test.com'

    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        register_user(client)
        resp = client.post('/api/auth/login', json={
            'email': 'alice@test.com', 'password': 'WRONG'
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        """Email not in the system returns 401."""
        resp = client.post('/api/auth/login', json={
            'email': 'ghost@test.com', 'password': 'whatever'
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post('/api/auth/login', json={'email': 'alice@test.com'})
        assert resp.status_code == 400


class TestMe:
    def test_me_returns_user(self, client):
        """Authenticated GET /me returns the logged-in user's info."""
        register_user(client)
        token = login_user(client)
        resp = client.get('/api/auth/me', headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['email'] == 'alice@test.com'

    def test_me_requires_auth(self, client):
        """Calling /me without a token returns 401."""
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        """A garbage token returns 401."""
        resp = client.get('/api/auth/me', headers={'Authorization': 'Bearer garbage'})
        assert resp.status_code == 401
