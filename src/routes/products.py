from flask import Blueprint, request, jsonify, session
from models import db, Product
import jwt
from flask import current_app
from functools import wraps
from loguru import logger

products_bp = Blueprint('products', __name__)

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header missing or invalid'}), 401
        token = auth_header.split(' ')[1]
        try:
            logger.debug(f"Token: {token}")
            logger.debug(f"Secret key: {current_app.config['SECRET_KEY']}")
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            logger.debug(f"Payload: {payload}")
            user_id = payload['username']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError) as e:
            logger.error(f"Error decoding token: {e}")
            return jsonify({'error': 'Invalid or expired token'}), 401
        # Attach user_id to kwargs for use in the route
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)
    return decorated


@products_bp.route('/products', methods=['GET', 'POST'])
@jwt_required
def products(user_id):
    if request.method == 'POST':
        data = request.json
        product = Product(name=data['name'], price=data['price'], user_id=user_id)
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product added'})
    else:
        products = Product.query.filter_by(user_id=user_id).all()
        return jsonify([{'id': p.id, 'name': p.name, 'price': p.price} for p in products])


@products_bp.route('/products/<int:product_id>', methods=['PUT', 'DELETE'])
@jwt_required
def product_detail(product_id, user_id):
    product = Product.query.filter_by(id=product_id, user_id=user_id).first_or_404()
    if request.method == 'PUT':
        data = request.json
        product.name = data['name']
        product.price = data['price']
        db.session.commit()
        return jsonify({'message': 'Product updated'})
    else:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted'})
