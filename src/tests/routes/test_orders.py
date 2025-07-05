import pytest
import datetime
from werkzeug.exceptions import BadRequest, NotFound
from models.order_model import db, Order, OrderType, OrderPaymentStatus, OrderDeliveryStatus
from models.customer_model import Customer
from models.product_model import Product
from conftest import get_token, get_token_header
from bs4 import BeautifulSoup

@pytest.fixture
def auth_headers(client):
    token = get_token(client)
    return get_token_header(token)

@pytest.fixture
def sample_customer(client, auth_headers):
    response = client.post(
        "/api/customers",
        json={"name": "Test Customer", "phone_number": "1234567890"},
        headers=auth_headers
    )
    assert response.status_code == 201
    return response.json

@pytest.fixture
def sample_product(client, auth_headers):
    response = client.post(
        "/api/products",
        json={"name": "Test Product", "price": 50.00},
        headers=auth_headers
    )
    assert response.status_code == 201
    return response.json

@pytest.fixture
def sample_order(client, auth_headers, sample_customer, sample_product):
    data = {
        'customer_id': sample_customer['id'],
        'order_type': 'pickup',
        'items': [
            {'product_id': sample_product['id'], 'quantity': 2}
        ]
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 201
    return response.json

@pytest.fixture
def multiple_customers(client, auth_headers):
    customers = []
    for i in range(3):
        response = client.post(
            "/api/customers",
            json={"name": f"Test Customer {i}", "phone_number": f"123456789{i}"},
            headers=auth_headers
        )
        assert response.status_code == 201
        customers.append(response.json)
    return customers

@pytest.fixture
def multiple_orders(client, auth_headers, multiple_customers, sample_product):
    orders = []
    # Create orders for different customers and dates
    dates = [
        datetime.datetime.now(datetime.UTC),
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1),
        datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2)
    ]
    
    for i, customer in enumerate(multiple_customers):
        data = {
            'customer_id': customer['id'],
            'order_type': 'pickup',
            'items': [
                {'product_id': sample_product['id'], 'quantity': i + 1}
            ],
            'datetime': dates[i].isoformat()
        }
        response = client.post('/api/orders', json=data, headers=auth_headers)
        assert response.status_code == 201
        orders.append(response.json)
    return orders

def test_create_order_success(client, auth_headers, sample_customer, sample_product):
    data = {
        'customer_id': sample_customer['id'],
        'order_type': 'pickup',
        'items': [
            {'product_id': sample_product['id'], 'quantity': 2}
        ]
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 201
    assert 'id' in response.json

def test_create_order_invalid_data(client, auth_headers):
    # Test missing required fields
    data = {
        'customer_id': 999,  # Non-existent customer
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 400

    # Test invalid order type
    data = {
        'customer_id': 1,
        'order_type': 'invalid_type',
        'items': []
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 400

    # Test invalid quantity
    data = {
        'customer_id': 1,
        'order_type': 'pickup',
        'items': [
            {'product_id': 1, 'quantity': -1}
        ]
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_get_order_success(client, auth_headers, sample_order):
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    data = response.json
    assert data['id'] == sample_order['id']
    assert data['customer_id'] == sample_order['customer_id']
    assert 'items' in data
    assert len(data['items']) > 0

def test_get_order_not_found(client, auth_headers):
    response = client.get('/api/orders/999', headers=auth_headers)
    assert response.status_code == 404

def test_get_all_orders(client, auth_headers, sample_order):
    response = client.get('/api/orders', headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) > 0
    assert any(order['id'] == sample_order['id'] for order in response.json)

def test_get_orders_by_date(client, auth_headers, multiple_orders):
    # Test today's orders
    today = datetime.datetime.now(datetime.UTC).date()
    response = client.get(f'/api/orders?date={today}', headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json, list)
    today_orders = response.json
    assert len(today_orders) > 0
    assert all(datetime.datetime.fromisoformat(order['datetime']).date() == today for order in today_orders)

    # Test yesterday's orders
    yesterday = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)).date()
    response = client.get(f'/api/orders?date={yesterday}', headers=auth_headers)
    assert response.status_code == 200
    yesterday_orders = response.json
    assert len(yesterday_orders) > 0
    assert all(datetime.datetime.fromisoformat(order['datetime']).date() == yesterday for order in yesterday_orders)

    # Test orders from two days ago
    two_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=2)).date()
    response = client.get(f'/api/orders?date={two_days_ago}', headers=auth_headers)
    assert response.status_code == 200
    two_days_ago_orders = response.json
    assert len(two_days_ago_orders) > 0
    assert all(datetime.datetime.fromisoformat(order['datetime']).date() == two_days_ago for order in two_days_ago_orders)

    # Verify we get different orders for different dates
    assert len(set(order['id'] for order in today_orders) & 
              set(order['id'] for order in yesterday_orders)) == 0
    assert len(set(order['id'] for order in yesterday_orders) & 
              set(order['id'] for order in two_days_ago_orders)) == 0

def test_get_orders_by_customer(client, auth_headers, multiple_orders, multiple_customers):
    # Test orders for first customer
    first_customer = multiple_customers[0]
    response = client.get(f'/api/orders?customer_id={first_customer["id"]}', headers=auth_headers)
    assert response.status_code == 200
    first_customer_orders = response.json
    assert len(first_customer_orders) > 0
    assert all(order['customer_id'] == first_customer['id'] for order in first_customer_orders)

    # Test orders for second customer
    second_customer = multiple_customers[1]
    response = client.get(f'/api/orders?customer_id={second_customer["id"]}', headers=auth_headers)
    assert response.status_code == 200
    second_customer_orders = response.json
    assert len(second_customer_orders) > 0
    assert all(order['customer_id'] == second_customer['id'] for order in second_customer_orders)

    # Test orders for third customer
    third_customer = multiple_customers[2]
    response = client.get(f'/api/orders?customer_id={third_customer["id"]}', headers=auth_headers)
    assert response.status_code == 200
    third_customer_orders = response.json
    assert len(third_customer_orders) > 0
    assert all(order['customer_id'] == third_customer['id'] for order in third_customer_orders)

    # Verify we get different orders for different customers
    assert len(set(order['id'] for order in first_customer_orders) & 
              set(order['id'] for order in second_customer_orders)) == 0
    assert len(set(order['id'] for order in second_customer_orders) & 
              set(order['id'] for order in third_customer_orders)) == 0

def test_get_orders_by_customer_and_date(client, auth_headers, multiple_orders, multiple_customers):
    # Test orders for first customer on today's date
    first_customer = multiple_customers[0]
    today = datetime.datetime.now(datetime.UTC).date()
    response = client.get(
        f'/api/orders?customer_id={first_customer["id"]}&date={today}',
        headers=auth_headers
    )
    assert response.status_code == 200
    filtered_orders = response.json
    assert len(filtered_orders) > 0
    assert all(
        order['customer_id'] == first_customer['id'] and 
        datetime.datetime.fromisoformat(order['datetime']).date() == today 
        for order in filtered_orders
    )

def test_update_order_payment_status_success(client, auth_headers, sample_order):
    data = {'payment_status': 'paid'}
    response = client.put(f'/api/orders/{sample_order["id"]}/payment_status', json=data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['message'] == 'Order payment status updated successfully'

    # Verify the payment status was updated
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['payment_status'] == 'paid'

def test_update_order_payment_status_invalid(client, auth_headers, sample_order):
    data = {'payment_status': 'invalid_status'}
    response = client.put(f'/api/orders/{sample_order["id"]}/payment_status', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_update_order_payment_status_missing_field(client, auth_headers, sample_order):
    data = {}
    response = client.put(f'/api/orders/{sample_order["id"]}/payment_status', json=data, headers=auth_headers)
    assert response.status_code == 400
    assert "payment_status is required" in response.get_json()['message']

def test_update_order_payment_status_not_found(client, auth_headers):
    data = {'payment_status': 'paid'}
    response = client.put('/api/orders/999/payment_status', json=data, headers=auth_headers)
    assert response.status_code == 404

def test_update_order_delivery_status_success(client, auth_headers, sample_order):
    data = {'delivery_status': 'delivered'}
    response = client.put(f'/api/orders/{sample_order["id"]}/delivery_status', json=data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['message'] == 'Order delivery status updated successfully'

    # Verify the delivery status was updated
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['delivery_status'] == 'delivered'

def test_update_order_delivery_status_invalid(client, auth_headers, sample_order):
    data = {'delivery_status': 'invalid_status'}
    response = client.put(f'/api/orders/{sample_order["id"]}/delivery_status', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_update_order_delivery_status_missing_field(client, auth_headers, sample_order):
    data = {}
    response = client.put(f'/api/orders/{sample_order["id"]}/delivery_status', json=data, headers=auth_headers)
    assert response.status_code == 400
    assert "delivery_status is required" in response.get_json()['message']

def test_update_order_delivery_status_not_found(client, auth_headers):
    data = {'delivery_status': 'delivered'}
    response = client.put('/api/orders/999/delivery_status', json=data, headers=auth_headers)
    assert response.status_code == 404

def test_update_order_type_success_pickup_to_delivery(client, auth_headers, sample_order):
    """Test updating order type from pickup to delivery"""
    data = {'order_type': 'delivery'}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['message'] == 'Order type updated successfully'

    # Verify the order type was updated
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['order_type'] == 'delivery'

def test_update_order_type_success_delivery_to_pickup(client, auth_headers, sample_customer, sample_product):
    """Test updating order type from delivery to pickup"""
    # First create an order with delivery type
    data = {
        'customer_id': sample_customer['id'],
        'order_type': 'delivery',
        'items': [
            {'product_id': sample_product['id'], 'quantity': 1}
        ]
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 201
    order = response.json

    # Update to pickup
    update_data = {'order_type': 'pickup'}
    response = client.put(f'/api/orders/{order["id"]}/order_type', json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['message'] == 'Order type updated successfully'

    # Verify the order type was updated
    response = client.get(f'/api/orders/{order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['order_type'] == 'pickup'

def test_update_order_type_invalid_value(client, auth_headers, sample_order):
    """Test updating order type with invalid value"""
    data = {'order_type': 'invalid_type'}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_update_order_type_missing_field(client, auth_headers, sample_order):
    """Test updating order type without providing the field"""
    data = {}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 400
    assert "order_type is required" in response.get_json()['message']

def test_update_order_type_not_found(client, auth_headers):
    """Test updating order type for non-existent order"""
    data = {'order_type': 'delivery'}
    response = client.put('/api/orders/999/order_type', json=data, headers=auth_headers)
    assert response.status_code == 404

def test_update_order_type_invalid_data_format(client, auth_headers, sample_order):
    """Test updating order type with invalid data format"""
    # Test with string instead of dict
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json="invalid", headers=auth_headers)
    assert response.status_code == 400

    # Test with list instead of dict
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=["delivery"], headers=auth_headers)
    assert response.status_code == 400

def test_update_order_type_case_sensitivity(client, auth_headers, sample_order):
    """Test that order type is case sensitive"""
    data = {'order_type': 'PICKUP'}  # Uppercase
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 400

    data = {'order_type': 'Delivery'}  # Title case
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_update_order_type_empty_string(client, auth_headers, sample_order):
    """Test updating order type with empty string"""
    data = {'order_type': ''}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_update_order_type_null_value(client, auth_headers, sample_order):
    """Test updating order type with null value"""
    data = {'order_type': None}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 400

def test_update_order_type_extra_fields(client, auth_headers, sample_order):
    """Test updating order type with extra fields (should still work)"""
    data = {
        'order_type': 'delivery',
        'extra_field': 'should_be_ignored',
        'another_field': 123
    }
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['message'] == 'Order type updated successfully'

    # Verify only the order_type was updated
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['order_type'] == 'delivery'

def test_update_order_type_same_value(client, auth_headers, sample_order):
    """Test updating order type to the same value (should work)"""
    # First verify the current order type
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    original_order_type = response.json['order_type']

    # Update to the same value
    data = {'order_type': original_order_type}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json['message'] == 'Order type updated successfully'

    # Verify the order type remains the same
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 200
    assert response.json['order_type'] == original_order_type

def test_update_order_type_unauthorized(client, sample_order):
    """Test updating order type without authentication"""
    data = {'order_type': 'delivery'}
    response = client.put(f'/api/orders/{sample_order["id"]}/order_type', json=data)
    assert response.status_code == 401

def test_update_order_type_wrong_method(client, auth_headers, sample_order):
    """Test updating order type with wrong HTTP method"""
    data = {'order_type': 'delivery'}
    
    # Test with GET method
    response = client.get(f'/api/orders/{sample_order["id"]}/order_type', headers=auth_headers)
    assert response.status_code == 405  # Method Not Allowed
    
    # Test with POST method
    response = client.post(f'/api/orders/{sample_order["id"]}/order_type', json=data, headers=auth_headers)
    assert response.status_code == 405  # Method Not Allowed
    
    # Test with DELETE method
    response = client.delete(f'/api/orders/{sample_order["id"]}/order_type', headers=auth_headers)
    assert response.status_code == 405  # Method Not Allowed

def test_delete_order_success(client, auth_headers, sample_order):
    response = client.delete(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 204

    # Verify the order was deleted
    response = client.get(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 404

def test_delete_paid_order(client, auth_headers, sample_order):
    # First update the order to paid status
    data = {'payment_status': 'paid'}
    response = client.put(f'/api/orders/{sample_order["id"]}/payment_status', json=data, headers=auth_headers)
    assert response.status_code == 200

    # Try to delete the paid order
    response = client.delete(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 400
    assert "Cannot delete paid or delivered orders" in response.get_json()['message']

def test_delete_delivered_order(client, auth_headers, sample_order):
    # First update the order to delivered status
    data = {'delivery_status': 'delivered'}
    response = client.put(f'/api/orders/{sample_order["id"]}/delivery_status', json=data, headers=auth_headers)
    assert response.status_code == 200

    # Try to delete the delivered order
    response = client.delete(f'/api/orders/{sample_order["id"]}', headers=auth_headers)
    assert response.status_code == 400
    assert "Cannot delete paid or delivered orders" in response.get_json()['message']

def test_duplicate_order_validation(client, auth_headers, sample_order, sample_customer, sample_product):
    # Try to create an identical order
    data = {
        'customer_id': sample_customer['id'],
        'order_type': 'pickup',
        'items': [
            {'product_id': sample_product['id'], 'quantity': 2}
        ]
    }
    response = client.post('/api/orders', json=data, headers=auth_headers)
    assert response.status_code == 400
    assert "Duplicate order detected" in response.get_json()['message']