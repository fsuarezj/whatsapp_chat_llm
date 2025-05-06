from flask import Blueprint, request, jsonify, session, current_app, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import re
from datetime import timedelta, datetime, timezone
from loguru import logger
#from flask_wtf.csrf import validate_csrf, CSRFError
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt, set_access_cookies,
    set_refresh_cookies, unset_jwt_cookies
)

auth_bp = Blueprint('auth', __name__)

# Example: simple in-memory rate limiter (for demo, use Redis or similar in prod)
login_attempts = {}

# In-memory token blacklist (use Redis or DB in production)
jwt_blacklist = set()

def is_strong_password(password):
    # Example: at least 8 chars, one uppercase, one lowercase, one digit
    return (
        len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'[a-z]', password) and
        re.search(r'\d', password)
    )

@auth_bp.route('/register', methods=['POST'])
def register():
    logger.debug(f"Register request received")
    data = request.json

    # Input validation
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    # Username validation: only allow alphanumeric and underscores, 3-30 chars
    if not re.match(r'^[a-zA-Z0-9_]{3,30}$', data['username']):
        return jsonify({'error': 'Invalid username. Only letters, numbers, and underscores allowed (3-30 chars).'}), 400

    # Prevent XSS: reject usernames with HTML special characters (redundant with above, but extra safe)
    if re.search(r'[<>"\'/]', data['username']):
        return jsonify({'error': 'Invalid username.'}), 400

    if not is_strong_password(data['password']):
        return jsonify({'error': 'Password does not meet complexity requirements'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username exists'}), 400

    user = User(
        username=data['username'],
        password=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json

    # Input validation
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Invalid credentials'}), 401

    username = data['username']
    ip = request.remote_addr

    # Rate limiting: allow max 5 attempts per 10 minutes per IP
    key = f"{ip}:{username}"
    attempts = login_attempts.get(key, {'count': 0, 'time': None})
    from time import time
    now = time()
    if attempts['time'] and now - attempts['time'] > 600:
        attempts = {'count': 0, 'time': now}
    attempts['count'] += 1
    attempts['time'] = now
    login_attempts[key] = attempts
    if attempts['count'] > 5:
        return jsonify({'error': 'Too many login attempts. Try again later.'}), 429

    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, data['password']):
        # Reset login attempts on success
        login_attempts.pop(key, None)
        logger.debug(f"User ID: {user.id}")
        access_token = create_access_token(identity=str(user.id), additional_claims={"username": user.username})
        refresh_token = create_refresh_token(identity=str(user.id))
        logger.info(f"User {username} logged in from IP: {ip}")
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 900  # 15 minutes
        }), 200
    else:
        # Log failed attempt
        logger.warning(f"Failed login for user: {username} from IP: {ip}")
        return jsonify({'error': 'Invalid credentials'}), 401

# Token revocation helpers
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    print(f"JTI: {jti}")
    jwt_blacklist.add(jti)
    logger.info(f"User {get_jwt_identity()} logged out, token revoked")
    response = jsonify({'message': 'Logged out'})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    logger.info(f"Access token refreshed for user {identity}")
    return jsonify({'access_token': access_token, 'token_type': 'Bearer', 'expires_in': 900}), 200

# Protect routes with @jwt_required()
@auth_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    return jsonify({'message': f'Hello user {user_id}'}), 200

# JWT callbacks for token revocation
@auth_bp.record_once
def setup_jwt_callbacks(state):
    jwt = JWTManager(state.app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        return jwt_payload['jti'] in jwt_blacklist

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has been revoked'}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 422

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Missing token'}), 401