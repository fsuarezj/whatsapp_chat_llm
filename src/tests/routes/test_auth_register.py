import pytest
from flask import Flask
from routes.auth import auth_bp
from models import db

def test_register_success(client):
    response = client.post('api/register', json={
        'username': 'testuser',
        'password': 'StrongPass1'
    })
    assert response.status_code == 201
    assert response.get_json()['message'] == 'User registered'

def test_register_missing_username(client):
    response = client.post('api/register', json={
        'password': 'StrongPass1'
    })
    assert response.status_code == 400
    assert 'error' in response.get_json()

def test_register_missing_password(client):
    response = client.post('api/register', json={
        'username': 'testuser'
    })
    assert response.status_code == 400
    assert 'error' in response.get_json()

def test_register_no_data(client):
    response = client.post('api/register', json={})
    assert response.status_code == 400
    assert 'error' in response.get_json()

def test_register_weak_password(client):
    response = client.post('api/register', json={
        'username': 'testuser',
        'password': 'weak'
    })
    assert response.status_code == 400
    assert 'error' in response.get_json()

def test_register_existing_username(client):
    # First registration
    client.post('api/register', json={
        'username': 'testuser',
        'password': 'StrongPass1'
    })
    # Second registration with same username
    response = client.post('api/register', json={
        'username': 'testuser',
        'password': 'AnotherStrong1'
    })
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Username exists'

def test_register_password_no_uppercase(client):
    response = client.post('api/register', json={
        'username': 'user2',
        'password': 'lowercase1'
    })
    assert response.status_code == 400

def test_register_password_no_lowercase(client):
    response = client.post('api/register', json={
        'username': 'user3',
        'password': 'UPPERCASE1'
    })
    assert response.status_code == 400

def test_register_password_no_digit(client):
    response = client.post('api/register', json={
        'username': 'user4',
        'password': 'NoDigitsHere'
    })
    assert response.status_code == 400
