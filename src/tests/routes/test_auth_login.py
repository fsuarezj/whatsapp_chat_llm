import pytest
from flask import session
from routes.auth import auth_bp, login_attempts
from models import db, User
from werkzeug.security import generate_password_hash

def create_user(username, password):
    user = User(username=username, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

def test_login_missing_data(client):
    # No data None
    resp = client.post('api/login', json=None)
    assert resp.status_code == 415
    # No data empty
    resp = client.post('api/login', json={})
    assert resp.status_code == 401
    # Missing username
    resp = client.post('api/login', json={'password': 'pass'})
    assert resp.status_code == 401
    # Missing password
    resp = client.post('api/login', json={'username': 'user'})
    assert resp.status_code == 401

def test_login_invalid_credentials(client):
    create_user('user1', 'Password123')
    # Wrong username
    resp = client.post('api/login', json={'username': 'user2', 'password': 'Password123'})
    assert resp.status_code == 401
    # Wrong password
    resp = client.post('api/login', json={'username': 'user1', 'password': 'WrongPass'})
    assert resp.status_code == 401

def test_login_success(client):
    create_user('user1', 'Password123')
    resp = client.post('api/login', json={'username': 'user1', 'password': 'Password123'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['token_type'] == 'Bearer'
    assert data['expires_in'] == 900

def test_login_rate_limit(client, monkeypatch):
    create_user('user1', 'Password123')
    key = '127.0.0.1:user1'
    # Simulate 5 failed attempts
    for _ in range(5):
        resp = client.post('api/login', json={'username': 'user1', 'password': 'WrongPass'})
        assert resp.status_code == 401
    # 6th attempt should be rate limited
    resp = client.post('api/login', json={'username': 'user1', 'password': 'WrongPass'})
    assert resp.status_code == 429
    assert 'Too many login attempts' in resp.get_json()['error']
    # Simulate time passing (over 10 minutes)
    login_attempts[key]['time'] -= 601
    resp = client.post('api/login', json={'username': 'user1', 'password': 'WrongPass'})
    assert resp.status_code == 401  # Not rate limited anymore

def test_login_resets_rate_limit_on_success(client):
    create_user('user1', 'Password123')
    key = '127.0.0.1:user1'
    # 2 failed attempts
    for _ in range(2):
        client.post('api/login', json={'username': 'user1', 'password': 'WrongPass'})
    # Successful login
    resp = client.post('api/login', json={'username': 'user1', 'password': 'Password123'})
    assert resp.status_code == 200
    # Attempts should be reset
    assert key not in login_attempts
