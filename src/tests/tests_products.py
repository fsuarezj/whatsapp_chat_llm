import pytest
from app import create_app, db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def get_token(client):
    client.post('/api/auth/register', json={
        'email': 'prod@example.com',
        'password': 'password123'
    })
    response = client.post('/api/auth/login', json={
        'email': 'prod@example.com',
        'password': 'password123'
    })
    return response.get_json()['token']

def test_create_product(client):
    token = get_token(client)
    response = client.post('/api/products', json={
        'name': 'Test Product',
        'price': 9.99
    }, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201 or response.status_code == 200

def test_get_products(client):
    token = get_token(client)
    # Create a product
    client.post('/api/products', json={
        'name': 'Test Product',
        'price': 9.99
    }, headers={'Authorization': f'Bearer {token}'})
    # Get products
    response = client.get('/api/products', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
