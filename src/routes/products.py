from flask_restx import Namespace, Resource, fields
from flask import request, make_response
from models import db, Product
from decorators import jwt_required
from loguru import logger
from app_factory import limiter
from werkzeug.exceptions import BadRequest
import re

# Create namespace
api = Namespace('products', description='Product operations')

# Define models for Swagger documentation
product_model = api.model('Product', {
    'id': fields.Integer(readonly=True, description='Product identifier'),
    'name': fields.String(required=True, description='Product name', max_length=80),
    'price': fields.Float(required=True, description='Product price', min=0),
    'description': fields.String(description='Product description', max_length=255),
    'picture_url': fields.String(description='Product picture URL', max_length=255),
    'is_active': fields.Boolean(description='Product active status')
})

def validate_product_name(name):
    """Validate product name"""
    if not isinstance(name, str) or not name.strip():
        raise BadRequest("Name must be a non-empty string")
    if len(name) > 80:
        raise BadRequest("Name must be less than 80 characters")
    # Check for potentially harmful characters
    if re.search(r'[<>"\'/]', name):
        raise BadRequest("Name contains invalid characters")

def validate_price(price):
    """Validate product price"""
    if not isinstance(price, (int, float)):
        raise BadRequest("Price must be a number")
    if price < 0:
        raise BadRequest("Price cannot be negative")
    if price > 999999.99:  # Reasonable maximum price
        raise BadRequest("Price exceeds maximum allowed value")

def validate_description(description):
    """Validate product description"""
    if description is not None:
        if not isinstance(description, str):
            raise BadRequest("Description must be a string")
        if len(description) > 255:
            raise BadRequest("Description must be less than 255 characters")

def validate_picture_url(url):
    """Validate product picture URL"""
    logger.debug(f"Validating picture URL: {url}")
    if url is not None and url != "":
        if not isinstance(url, str):
            raise BadRequest("Picture URL must be a string")
        if len(url) > 255:
            raise BadRequest("Picture URL must be less than 255 characters")
        # More comprehensive URL validation
        if not re.match(r'^https?://[^\s]+$', url) or '//' not in url[8:]:
            raise BadRequest("Invalid URL format")

def validate_product_data(data, update=False):
    """Validate all product data"""
    if not isinstance(data, dict):
        raise BadRequest("Invalid data format")

    # Required fields for creation
    if not update:
        required_fields = {'name', 'price'}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise BadRequest(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate each field if present
    if 'name' in data:
        validate_product_name(data['name'])
    if 'price' in data:
        validate_price(data['price'])
    if 'description' in data:
        validate_description(data['description'])
    if 'picture_url' in data:
        validate_picture_url(data['picture_url'])
    if 'is_active' in data and not isinstance(data['is_active'], bool):
        raise BadRequest("is_active must be a boolean")

    # Check for invalid fields
    allowed_fields = {'name', 'price', 'description', 'picture_url', 'is_active'}
    invalid_fields = set(data.keys()) - allowed_fields
    if invalid_fields:
        raise BadRequest(f"Invalid fields provided: {', '.join(invalid_fields)}")

# Product list endpoint
@api.route('/products')
class ProductList(Resource):
    @api.doc('list_products', security='bearerAuth')
    @api.marshal_list_with(product_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(400, 'Invalid query parameters')
    @jwt_required
    @limiter.limit("10 per minute")
    def get(self, user_id):
        """List all products"""
        logger.info("Getting products")
        products = Product.query.all()
        return products

    @api.doc('create_product', security='bearerAuth')
    @api.expect(product_model)
    @api.marshal_with(product_model, code=201)
    @api.response(201, 'Product created successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(409, 'Product with this name already exists')
    @api.response(429, 'Too many requests')
    @jwt_required
    @limiter.limit("10 per minute")
    def post(self, user_id):
        """Create a new product"""
        data = request.json
        validate_product_data(data)

        # Check for duplicate product name
        if Product.query.filter_by(name=data['name']).first():
            raise BadRequest("Product with this name already exists")

        product = Product(**data)
        logger.info(f"Adding product: {product.__dict__}")
        db.session.add(product)
        db.session.commit()
        return product, 201

# Product detail endpoint
@api.route('/products/<int:product_id>')
@api.param('product_id', 'The product identifier')
class ProductResource(Resource):
    @api.doc('get_product', security='bearerAuth')
    @api.marshal_with(product_model)
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Product not found')
    @jwt_required
    @limiter.limit("10 per minute")
    def get(self, product_id, user_id):
        """Get a product by ID"""
        product = Product.query.filter_by(id=product_id).first_or_404()
        return product

    @api.doc('update_product', security='bearerAuth')
    @api.expect(product_model)
    @api.marshal_with(product_model)
    @api.response(200, 'Product updated successfully')
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Product not found')
    @api.response(409, 'Product with this name already exists')
    @jwt_required
    @limiter.limit("10 per minute")
    def put(self, product_id, user_id):
        """Update a product"""
        product = Product.query.filter_by(id=product_id).first_or_404()
        data = request.json
        validate_product_data(data, update=True)

        # Check for duplicate name if name is being updated
        if 'name' in data and data['name'] != product.name:
            if Product.query.filter_by(name=data['name']).first():
                raise BadRequest("Product with this name already exists")

        for key, value in data.items():
            setattr(product, key, value)
        db.session.commit()
        return product

    @api.doc('delete_product', security='bearerAuth')
    @api.response(204, 'Product deleted successfully')
    @api.response(400, 'Cannot delete product that is associated with orders')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Product not found')
    @jwt_required
    @limiter.limit("10 per minute")
    def delete(self, product_id, user_id):
        """Delete a product"""
        product = Product.query.filter_by(id=product_id).first_or_404()

        if product.orders:
            raise BadRequest("Cannot delete product that is associated with orders")

        db.session.delete(product)
        logger.info(f"Deleting product with ID: {product_id}")
        db.session.commit()
        logger.info(f"Product deleted with ID: {product_id}")
        return make_response('', 204)