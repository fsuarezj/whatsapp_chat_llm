from flask import Blueprint, request, jsonify, session
from models import db, Product
from decorators import jwt_required
from werkzeug.exceptions import BadRequest

from app_factory import limiter

products_bp = Blueprint('products', __name__)

@products_bp.route('/products', methods=['GET', 'POST'])
@jwt_required
@limiter.limit("10 per minute")
def products(user_id):
    if request.method == 'POST':
        data = request.json
        validate_product_data(data)
        product = Product(name=data['name'], price=data['price'])
        db.session.add(product)
        db.session.commit()
        return jsonify({'id': product.id, 'name': product.name, 'price': product.price}), 201
    else:
        products = Product.query.all()
        return jsonify([{'id': p.id, 'name': p.name, 'price': p.price} for p in products]), 200


@products_bp.route('/products/<int:product_id>', methods=['PUT', 'DELETE'])
@jwt_required
@limiter.limit("10 per minute")
def product_detail(product_id, user_id):
    product = Product.query.filter_by(id=product_id).first_or_404()
    if request.method == 'PUT':
        data = request.json
        if not isinstance(data, dict):
            raise BadRequest('Invalid data format')
        # Only update fields if they are present in the request
        if 'name' in data:
            validate_product_name(data['name'])
            product.name = data['name']
        if 'price' in data:
            validate_product_price(data['price'])
            product.price = data['price']
        db.session.commit()
        return jsonify({'message': 'Product updated', 'product': {'id': product.id, 'name': product.name, 'price': product.price}}), 200
    else:
        db.session.delete(product)
        db.session.commit()
        return "", 204

## Validations
def validate_product_name(name):
    if not isinstance(name, str) or not name.strip():
        raise BadRequest('Product name must be a non-empty string')
    if len(name) > 80:
        raise BadRequest('Product name must be less than 80 characters')

def validate_product_price(price):
    if not isinstance(price, (int, float)):
        raise BadRequest('Product price must be a number')
    if price <= 0:
        raise BadRequest('Product price must be greater than 0')

def validate_product_description(description):
    if not isinstance(description, str):
        raise BadRequest('Product description must be a string')
    if len(description) > 255:
        raise BadRequest('Product description must be less than 255 characters')

def validate_product_picture_url(picture_url):
    if not isinstance(picture_url, str):
        raise BadRequest('Product picture URL must be a string')
    if len(picture_url) > 255:
        raise BadRequest('Product picture URL must be less than 255 characters')
    # Basic URL validation
    if not picture_url.startswith(('http://', 'https://')):
        raise BadRequest('Product picture URL must start with http:// or https://')

def validate_product_is_active(is_active):
    if not isinstance(is_active, bool):
        raise BadRequest('Product is_active must be a boolean')

def validate_product_data(data):
    if not isinstance(data, dict):
        raise BadRequest('Invalid data format')
    if 'name' not in data:
        raise BadRequest('Product name is required')
    validate_product_name(data['name'])
    if 'price' not in data:
        raise BadRequest('Product price is required')
    validate_product_price(data['price'])
    if 'description' in data:
        validate_product_description(data['description'])
    if 'picture_url' in data:
        validate_product_picture_url(data['picture_url'])
    if 'is_active' in data:
        validate_product_is_active(data['is_active'])
    valid_fields = {'name', 'price', 'picture_url', 'description', 'is_active'}
    invalid_fields = set(data.keys()) - valid_fields
    if invalid_fields:
        raise BadRequest(f'Invalid fields: {", ".join(invalid_fields)}')

