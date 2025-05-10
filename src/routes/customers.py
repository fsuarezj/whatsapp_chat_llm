from flask import Blueprint, request, jsonify, abort
from models import db
from models.customer_model import Customer  # Use your real Customer model
from decorators import jwt_required
from loguru import logger
from werkzeug.exceptions import BadRequest, Conflict, NotFound
import re

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers', methods=['GET'])
@jwt_required
def get_all_customers(user_id):
    customers = Customer.query.all()
    logger.debug(customers)
    return jsonify([{"id": c.id, "name": c.name, "phone_number": c.phone_number, "address": c.address, "notes": c.notes} for c in customers]), 200

@customers_bp.route('/customers/<int:customer_id>', methods=['GET'])
@jwt_required
def get_single_customer(customer_id, user_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
       raise NotFound("Customer not found")
    return jsonify({
        "id": customer.id,
        "name": customer.name,
        "phone_number": customer.phone_number,
        "address": customer.address,
        "notes": customer.notes
    }), 200

@customers_bp.route('/customers', methods=['POST'])
@jwt_required
def create_customer(user_id):
    data = request.get_json()
    if not data:
        raise BadRequest("No data provided")
    validate_customer_data(data)

    # Check if customer with phone number already exists
    existing_customer = Customer.query.filter_by(phone_number=data['phone_number']).first()
    #existing_customer = db.session.get(Customer, data['phone_number'])
    if existing_customer:
        raise Conflict(f"Customer with phone number {data['phone_number']} already exists")
        
    customer = Customer(
        name=data.get('name'),
        phone_number=data['phone_number'],
        address=data.get('address'),
        notes=data.get('notes')
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({
        "id": customer.id,
        "name": customer.name,
        "phone_number": customer.phone_number,
        "address": customer.address,
        "notes": customer.notes
    }), 201

@customers_bp.route('/customers/<int:customer_id>', methods=['PUT'])
@jwt_required
def update_customer(customer_id, user_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        raise NotFound("Customer not found")
    data = request.get_json()
    if not data:
        raise BadRequest("No data provided")
    validate_customer_data(data)
    
    if 'name' in data:
        customer.name = data['name']
    if 'phone_number' in data:
        customer.phone_number = data['phone_number']
    if 'address' in data:
        customer.address = data['address']
    if 'notes' in data:
        customer.notes = data['notes']
    
    db.session.commit()
    return jsonify({
        "id": customer.id,
        "name": customer.name,
        "phone_number": customer.phone_number,
        "address": customer.address,
        "notes": customer.notes
    }), 200

@customers_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
@jwt_required
def delete_customer(customer_id, user_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        raise NotFound("Customer not found")
    db.session.delete(customer)
    db.session.commit()
    return "", 204

def validate_customer_name(name):
    if not isinstance(name, str) or not name.strip():
        raise BadRequest("Name must be a non-empty string")
    if len(name) > 80:  # Based on Customer model field length
        raise BadRequest("Name must be less than 80 characters")

def validate_phone_number(phone):
    if not isinstance(phone, str) or not phone.strip():
        raise BadRequest("Phone number must be a non-empty string")
    if len(phone) > 20:  # Based on Customer model field length
        raise BadRequest("Phone number must be less than 20 characters")
    # Could add more specific phone validation if needed
    if not re.match(r'^(?:\+?\d{1,3})?(?:\d{6,10})$', phone):
        raise BadRequest("Phone number must be 6 to 10 digits, country code optional")

def validate_address(address):
    if not isinstance(address, str) or not address.strip():
        raise BadRequest("Address must be a non-empty string")
    if len(address) > 255:
        raise BadRequest("Address must be less than 255 characters")

def validate_customer_data(data, update=False):
    if not isinstance(data, dict):
        raise BadRequest("Invalid data format")
    if 'phone_number' not in data and not update:
        raise BadRequest("Phone number is required")
    validate_phone_number(data['phone_number'])
    if 'name' in data:
        validate_customer_name(data['name'])
    if 'address' in data:
        validate_address(data['address'])
    # Check for invalid fields
    allowed_fields = {'phone_number', 'name', 'address'}
    invalid_fields = set(data.keys()) - allowed_fields
    if invalid_fields:
        raise BadRequest(f"Invalid fields provided: {', '.join(invalid_fields)}")
        

