import pytest
from flask import Flask
from routes.auth import auth_bp
from models import db
from loguru import logger
import jwt  # Only if you need to decode tokens for test assertions
from flask import current_app

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    app.secret_key = 'test'
    db.init_app(app)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def get_jwt_from_response(resp):
    # Assuming JWT is returned in JSON as {'access_token': '...'}
    data = resp.get_json()
    return data.get('access_token') if data else None

def auth_header(token):
    return {'Authorization': f'Bearer {token}'}

def test_register_valid(client):
    resp = client.post('/auth/register', json={'username': 'testuser', 'password': 'StrongPass1'})
    assert resp.status_code == 201
    assert b'User registered' in resp.data or b'access_token' in resp.data  # If you return token

def test_register_missing_fields(client):
    resp = client.post('/auth/register', json={'username': 'testuser'})
    assert resp.status_code == 400
    resp = client.post('/auth/register', json={'password': 'StrongPass1'})
    assert resp.status_code == 400
    resp = client.post('/auth/register', json={})
    assert resp.status_code == 400

def test_register_weak_password(client):
    resp = client.post('/auth/register', json={'username': 'weak', 'password': '123'})
    assert resp.status_code == 400

def test_register_existing_user(client):
    client.post('/auth/register', json={'username': 'dup', 'password': 'StrongPass1'})
    resp = client.post('/auth/register', json={'username': 'dup', 'password': 'StrongPass1'})
    assert resp.status_code == 400

def test_register_sql_injection(client):
    resp = client.post('/auth/register', json={'username': "admin';--", 'password': 'StrongPass1'})
    assert resp.status_code in (200, 400)

def test_register_xss(client):
    resp = client.post('/auth/register', json={'username': "<script>alert(1)</script>", 'password': 'StrongPass1'})
    assert resp.status_code == 400

def test_login_valid(client):
    client.post('/auth/register', json={'username': 'loginuser', 'password': 'StrongPass1'})
    resp = client.post('/auth/login', json={'username': 'loginuser', 'password': 'StrongPass1'})
    assert resp.status_code == 200
    token = get_jwt_from_response(resp)
    assert token is not None

def test_login_invalid_password(client):
    client.post('/auth/register', json={'username': 'badpass', 'password': 'StrongPass1'})
    resp = client.post('/auth/login', json={'username': 'badpass', 'password': 'WrongPass'})
    assert resp.status_code == 401

def test_login_missing_fields(client):
    resp = client.post('/auth/login', json={'username': 'user'})
    assert resp.status_code == 401
    resp = client.post('/auth/login', json={'password': 'pass'})
    assert resp.status_code == 401
    resp = client.post('/auth/login', json={})
    assert resp.status_code == 401

def test_login_sql_injection(client):
    client.post('/auth/register', json={'username': 'sqltest', 'password': 'StrongPass1'})
    resp = client.post('/auth/login', json={'username': "sqltest' OR 1=1 --", 'password': 'StrongPass1'})
    assert resp.status_code == 401

def test_login_xss(client):
    resp = client.post('/auth/login', json={'username': "<script>alert(1)</script>", 'password': 'StrongPass1'})
    assert resp.status_code == 401

def test_login_rate_limit(client, monkeypatch):
    client.post('/auth/register', json={'username': 'ratelimit', 'password': 'StrongPass1'})
    for _ in range(6):
        resp = client.post('/auth/login', json={'username': 'ratelimit', 'password': 'WrongPass'})
    assert resp.status_code == 429

def test_logout_valid(client):
    # 1. Register and login to get a token
    client.post('/auth/register', json={'username': 'testuser', 'password': 'Testpass123'})
    login_resp = client.post('/auth/login', json={'username': 'testuser', 'password': 'Testpass123'})
    access_token = login_resp.get_json()['access_token']

    # 2. Pass the token in the Authorization header
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    logger.debug(f"Headers: {headers}")
    resp = client.post('/auth/logout', headers=headers)
    assert resp.status_code == 200

def test_logout_no_token(client):
    resp = client.post('/auth/logout')
    assert resp.status_code  == 401  # 401 Unauthorized is typical

def test_logout_invalid_token(client):
    resp = client.post('/auth/logout', headers=auth_header('invalid.token.here'))
    assert resp.status_code == 422

def test_logout_xss_token(client):
    resp = client.post('/auth/logout', headers=auth_header("<script>alert(1)</script>"))
    assert resp.status_code == 422