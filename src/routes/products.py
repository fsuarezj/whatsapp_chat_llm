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
        product = Product(name=data['name'], price=data['price'], user_id=user_id)
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product added'})
    else:
        products = Product.query.filter_by(user_id=user_id).all()
        return jsonify([{'id': p.id, 'name': p.name, 'price': p.price} for p in products])


@products_bp.route('/products/<int:product_id>', methods=['PUT', 'DELETE'])
@jwt_required
@limiter.limit("10 per minute")
def product_detail(product_id, user_id):
    product = Product.query.filter_by(id=product_id, user_id=user_id).first_or_404()
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
        return jsonify({'message': 'Product updated'})
    else:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted'})

def validate_product_name(name):
    if not isinstance(name, str) or not name.strip():
        raise BadRequest('Product name must be a non-empty string')

def validate_product_price(price):
    if not isinstance(price, (int, float)):
        raise BadRequest('Product price must be a number')

def validate_product_data(data):
    if not isinstance(data, dict):
        raise BadRequest('Invalid data format')
    if 'name' not in data:
        raise BadRequest('Product name is required')
    validate_product_name(data['name'])
    if 'price' not in data:
        raise BadRequest('Product price is required')
    validate_product_price(data['price'])
