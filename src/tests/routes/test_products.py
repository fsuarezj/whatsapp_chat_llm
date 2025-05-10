import pytest
from app_factory import create_app, db
from conftest import get_token, get_token_header
from loguru import logger

def test_create_product(client):
    token = get_token(client)
    response = client.post('/api/products', json={
        'name': 'Test Product',
        'price': 9.99
    }, headers=get_token_header(token))
    assert response.status_code == 201

def test_get_products(client):
    token = get_token(client)
    # Create a product
    client.post('/api/products', json={
        'name': 'Test Product',
        'price': 9.99
    }, headers=get_token_header(token))
    # Get products
    response = client.get('/api/products', headers=get_token_header(token))
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
