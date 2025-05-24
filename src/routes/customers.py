from flask_restx import Namespace, Resource, fields
from flask import request
from models import db
from models.customer_model import Customer
from decorators import jwt_required
from loguru import logger
from werkzeug.exceptions import BadRequest, Conflict, NotFound
import re

# Create namespace
api = Namespace('customers', description='Customer operations')

# Define models for Swagger documentation
customer_model = api.model('Customer', {
    'id': fields.Integer(readonly=True, description='Customer ID'),
    'name': fields.String(description='Customer name', max_length=80),
    'phone_number': fields.String(required=True, description='Customer phone number (6-10 digits, country code optional)', max_length=20),
    'address': fields.String(description='Customer address', max_length=255),
    'notes': fields.String(description='Additional notes about the customer')
})

@api.route('/customers')
class CustomerList(Resource):
    @api.doc('list_customers', security='bearerAuth')
    @api.marshal_list_with(customer_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(400, 'Invalid query parameters')
    @jwt_required
    def get(self, user_id):
        """List all customers"""
        customers = Customer.query.all()
        return customers

    @api.doc('create_customer', security='bearerAuth')
    @api.expect(customer_model)
    @api.marshal_with(customer_model, code=201)
    @api.response(201, 'Customer created successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(409, 'Customer with this phone number already exists')
    @jwt_required
    def post(self, user_id):
        """Create a new customer"""
        data = api.payload
        validate_customer_data(data)

        existing_customer = Customer.query.filter_by(phone_number=data['phone_number']).first()
        if existing_customer:
            raise Conflict(f"Customer with phone number {data['phone_number']} already exists")
            
        customer = Customer(**data)
        db.session.add(customer)
        db.session.commit()
        return customer, 201

@api.route('/customers/<int:customer_id>')
@api.param('customer_id', 'The customer identifier')
class CustomerResource(Resource):
    @api.doc('get_customer', security='bearerAuth')
    @api.marshal_with(customer_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Customer not found')
    @jwt_required
    def get(self, customer_id, user_id):
        """Get a customer by ID"""
        customer = db.session.get(Customer, customer_id)
        if not customer:
            api.abort(404, "Customer not found")
        return customer

    @api.doc('update_customer', security='bearerAuth')
    @api.expect(customer_model)
    @api.marshal_with(customer_model)
    @api.response(200, 'Customer updated successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Customer not found')
    @api.response(409, 'Customer with this phone number already exists')
    @jwt_required
    def put(self, customer_id, user_id):
        """Update a customer"""
        customer = db.session.get(Customer, customer_id)
        if not customer:
            api.abort(404, "Customer not found")
        
        data = api.payload
        validate_customer_data(data, update=True)
        
        for key, value in data.items():
            setattr(customer, key, value)
        
        db.session.commit()
        return customer

    @api.doc('delete_customer', security='bearerAuth')
    @api.response(204, 'Customer deleted successfully')
    @api.response(400, 'Cannot delete customer with associated orders')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Customer not found')
    @jwt_required
    def delete(self, customer_id, user_id):
        """Delete a customer"""
        customer = db.session.get(Customer, customer_id)
        if not customer:
            api.abort(404, "Customer not found")
        db.session.delete(customer)
        db.session.commit()
        return '', 204

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
        

