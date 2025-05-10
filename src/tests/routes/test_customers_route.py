import pytest
from flask import url_for
from models import db
from models.customer_model import Customer
from conftest import get_token, get_token_header
from bs4 import BeautifulSoup

def test_create_customer(client):
    token = get_token(client)
    response = client.post("/api/customers", json={"name": "Diana", "phone_number": "12347890"}, headers=get_token_header(token))
    assert response.status_code == 201
    data = response.get_json()
    assert data['phone_number'] == "12347890"
    assert 'id' in data

def test_create_duplicated_customer(client, session):
    token = get_token(client)
    response = client.post("/api/customers", json={"name": "Diana", "phone_number": "1234567890"}, headers=get_token_header(token))
    response = client.post("/api/customers", json={"name": "Pepito", "phone_number": "1234567890"}, headers=get_token_header(token))
    assert response.status_code == 409
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.find('p').text
    assert text == "Customer with phone number 1234567890 already exists"

def test_update_customer(client, session):
    token = get_token(client)
    response = client.post("/api/customers", json={"name": "Diana", "phone_number": "1234567890"}, headers=get_token_header(token))
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == "Diana"
    assert 'id' in data
    print("Customer ID: ", data['id'])
    response = client.put(f"/api/customers/{data['id']}", json={"name": "Eve Updated", "phone_number": "1234567890"}, headers=get_token_header(token))
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == "Eve Updated"

def test_get_all_customers(client, session):
    token = get_token(client)
    response = client.post("/api/customers", json={"name": "Alice", "phone_number": "1234567890"}, headers=get_token_header(token))
    response = client.post("/api/customers", json={"name": "Bob", "phone_number": "1234567810"}, headers=get_token_header(token))
    response = client.get("/api/customers", headers=get_token_header(token))
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert any(c['name'] == "Alice" for c in data)
    assert any(c['name'] == "Bob" for c in data)

def test_get_single_customer(client, session):
    token = get_token(client)
    response = client.post("/api/customers", json={"name": "Charlie", "phone_number": "1234567890"}, headers=get_token_header(token))
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == "Charlie"
    assert 'id' in data
    response = client.get(f"/api/customers/{data['id']}", headers=get_token_header(token))
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == "Charlie"
    assert data['id'] == data['id']

def test_delete_customer(client, session):
    token = get_token(client)
    response = client.post("/api/customers", json={"name": "Frank", "phone_number": "1234567890"}, headers=get_token_header(token))
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == "Frank"
    assert 'id' in data
    response = client.delete(f"/api/customers/{data['id']}", headers=get_token_header(token))
    assert response.status_code == 204  # No Content
    # Ensure it's deleted
    response = client.get(f"/api/customers/{data['id']}", headers=get_token_header(token))
    assert response.status_code == 404
 