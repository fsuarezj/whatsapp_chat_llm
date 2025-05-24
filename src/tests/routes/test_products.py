import pytest
from app_factory import create_app, db
from conftest import get_token, get_token_header
from loguru import logger
from models import Product

def test_create_product_success(client):
    """Test successful product creation"""
    token = get_token(client)
    product_data = {
        'name': 'Test Product',
        'price': 9.99,
        'description': 'A test product',
        'picture_url': 'http://example.com/image.jpg',
        'is_active': True
    }
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == product_data['name']
    assert data['price'] == product_data['price']
    assert data['description'] == product_data['description']
    assert data['picture_url'] == product_data['picture_url']
    assert data['is_active'] == product_data['is_active']

def test_create_product_validation(client):
    """Test product creation validation"""
    token = get_token(client)
    
    # Test missing required fields
    response = client.post('/api/products', json={}, headers=get_token_header(token))
    assert response.status_code == 400
    
    # Test invalid price (negative)
    response = client.post('/api/products', json={
        'name': 'Test Product',
        'price': -9.99
    }, headers=get_token_header(token))
    assert response.status_code == 400
    
    # Test name too long
    response = client.post('/api/products', json={
        'name': 'a' * 81,  # Max length is 80
        'price': 9.99
    }, headers=get_token_header(token))
    assert response.status_code == 400

def test_create_duplicate_product(client):
    """Test creating a product with duplicate name"""
    token = get_token(client)
    product_data = {
        'name': 'Duplicate Product',
        'price': 9.99
    }
    
    # Create first product
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 201
    
    # Try to create duplicate
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 400

def test_get_products_list(client):
    """Test getting list of products"""
    token = get_token(client)
    
    # Create multiple products
    products = [
        {'name': 'Product 1', 'price': 9.99},
        {'name': 'Product 2', 'price': 19.99},
        {'name': 'Product 3', 'price': 29.99}
    ]
    
    for product in products:
        response = client.post('/api/products', json=product, headers=get_token_header(token))
        assert response.status_code == 201
    
    # Get all products
    response = client.get('/api/products', headers=get_token_header(token))
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= len(products)  # Could be more if other tests created products

def test_get_product_by_id(client):
    """Test getting a specific product"""
    token = get_token(client)
    
    # Create a product
    product_data = {
        'name': 'Test Product',
        'price': 9.99
    }
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 201
    created_product = response.get_json()
    
    # Get the product by ID
    response = client.get(f'/api/products/{created_product["id"]}', headers=get_token_header(token))
    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == created_product['id']
    assert data['name'] == product_data['name']
    assert data['price'] == product_data['price']

def test_get_nonexistent_product(client):
    """Test getting a product that doesn't exist"""
    token = get_token(client)
    response = client.get('/api/products/99999', headers=get_token_header(token))
    assert response.status_code == 404

def test_update_product(client):
    """Test updating a product"""
    token = get_token(client)
    
    # Create a product
    product_data = {
        'name': 'Original Product',
        'price': 9.99
    }
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 201
    created_product = response.get_json()
    
    # Update the product
    update_data = {
        'name': 'Updated Product',
        'price': 19.99,
        'description': 'Updated description'
    }
    response = client.put(
        f'/api/products/{created_product["id"]}',
        json=update_data,
        headers=get_token_header(token)
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == update_data['name']
    assert data['price'] == update_data['price']
    assert data['description'] == update_data['description']

def test_delete_product(client):
    """Test deleting a product"""
    token = get_token(client)
    
    # Create a product
    product_data = {
        'name': 'Product to Delete',
        'price': 9.99
    }
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 201
    created_product = response.get_json()
    
    # Delete the product
    response = client.delete(
        f'/api/products/{created_product["id"]}',
        headers=get_token_header(token)
    )
    assert response.status_code == 204
    
    # Verify product is deleted
    response = client.get(
        f'/api/products/{created_product["id"]}',
        headers=get_token_header(token)
    )
    assert response.status_code == 404

def test_unauthorized_access(client):
    """Test unauthorized access to product endpoints"""
    # Try to access without token
    response = client.get('/api/products')
    assert response.status_code == 401
    
    response = client.post('/api/products', json={'name': 'Test', 'price': 9.99})
    assert response.status_code == 401
    
    response = client.put('/api/products/1', json={'name': 'Test', 'price': 9.99})
    assert response.status_code == 401
    
    response = client.delete('/api/products/1')
    assert response.status_code == 401

# TODO: Not working, check why
#def test_rate_limiting(client):
#    """Test rate limiting on product endpoints"""
#    token = get_token(client)
#    
#    # Make multiple requests in quick succession
#    for _ in range(11):  # Limit is 10 per minute
#        response = client.get('/api/products', headers=get_token_header(token))
#    
#    # The 11th request should be rate limited
#    assert response.status_code == 429

def test_product_relationships(client):
    """Test product relationships with orders"""
    token = get_token(client)
    
    # Create a product
    product_data = {
        'name': 'Product for Order',
        'price': 9.99
    }
    response = client.post('/api/products', json=product_data, headers=get_token_header(token))
    assert response.status_code == 201
    product = response.get_json()
    
    # Create a customer
    customer_data = {
        'name': 'Test Customer',
        'phone_number': '1234567890'
    }
    response = client.post('/api/customers', json=customer_data, headers=get_token_header(token))
    assert response.status_code == 201
    customer = response.get_json()
    
    # Create an order with the product
    order_data = {
        'customer_id': customer['id'],
        'order_type': 'pickup',
        'items': [
            {
                'product_id': product['id'],
                'quantity': 2
            }
        ]
    }
    response = client.post('/api/orders', json=order_data, headers=get_token_header(token))
    assert response.status_code == 201
    
    # Verify product is still accessible
    response = client.get(f'/api/products/{product["id"]}', headers=get_token_header(token))
    assert response.status_code == 200
