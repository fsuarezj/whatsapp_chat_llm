from functools import wraps
from flask import request, jsonify, current_app
import jwt
from loguru import logger

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header missing or invalid'}), 401
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            logger.info(f"Payload: {payload}")
            user_id = payload['sub']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError) as e:
            logger.error(f"Error decoding token: {e}")
            return jsonify({'error': 'Invalid or expired token'}), 401
        kwargs['user_id'] = user_id
        return f(*args, **kwargs)
    return decorated
