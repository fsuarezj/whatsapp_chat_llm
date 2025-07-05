from flask import Blueprint, request, jsonify, session, current_app, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import re
from datetime import timedelta, datetime, timezone
from loguru import logger
import os

#from flask_wtf.csrf import validate_csrf, CSRFError
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt, set_access_cookies,
    set_refresh_cookies, unset_jwt_cookies
)
from flask_restx import Namespace, Resource, fields

auth_bp = Blueprint('auth', __name__)

# Create namespace
api = Namespace('auth', description='Authentication operations')

# Define models for Swagger documentation
user_model = api.model('User', {
    'username': fields.String(required=True, description='Username (3-30 chars, alphanumeric and underscores only)', min_length=3, max_length=30),
    'password': fields.String(required=True, description='Password (min 8 chars, must include uppercase, lowercase, and digit)', min_length=8)
})

token_model = api.model('Token', {
    'access_token': fields.String(description='JWT access token'),
    'refresh_token': fields.String(description='JWT refresh token'),
    'token_type': fields.String(description='Token type', example='Bearer'),
    'expires_in': fields.Integer(description='Token expiration time in seconds', example=900)
})

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

@api.route('/register')
class Register(Resource):
    @api.doc('register_user')
    @api.expect(user_model)
    @api.response(201, 'User registered successfully')
    @api.response(400, 'Invalid input data or username exists')
    @api.response(409, 'Username already exists')
    def post(self):
        """Register a new user"""
        data = api.payload

        # Check if required fields exist
        if not data or 'username' not in data or 'password' not in data:
            api.abort(400, 'Missing required fields: username and password')

        # Input validation
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', data['username']):
            api.abort(400, 'Invalid username. Only letters, numbers, and underscores allowed (3-30 chars).')

        if re.search(r'[<>"\'/]', data['username']):
            api.abort(400, 'Invalid username.')

        if not is_strong_password(data['password']):
            api.abort(400, 'Password does not meet complexity requirements')

        if User.query.filter_by(username=data['username']).first():
            api.abort(409, 'Username already exists')

        user = User(
            username=data['username'],
            password=generate_password_hash(data['password'])
        )
        db.session.add(user)
        db.session.commit()
        return {'message': 'User registered'}, 201

@api.route('/login')
class Login(Resource):
    @api.doc('login_user')
    @api.expect(user_model)
    @api.response(200, 'Login successful', token_model)
    @api.response(400, 'Invalid input data')
    @api.response(401, 'Invalid credentials')
    @api.response(429, 'Too many login attempts')
    def post(self):
        """Login with user credentials"""

        data = api.payload
        # Check if required fields exist
        if not data or 'username' not in data or 'password' not in data:
            api.abort(400, 'Missing required fields: username and password')
        username = data['username']
        ip = request.remote_addr

        # Rate limiting
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
            api.abort(429, 'Too many login attempts. Try again later.')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, data['password']):
            login_attempts.pop(key, None)
            access_token = create_access_token(identity=str(user.id), additional_claims={"username": user.username})
            refresh_token = create_refresh_token(identity=str(user.id))
            logger.info(f"Login successful for user: {username} from IP: {ip}")
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': 900
            }, 200
        else:
            logger.warning(f"Failed login for user: {username} from IP: {ip}")
            api.abort(401, 'Invalid credentials')

@api.route('/logout')
class Logout(Resource):
    @api.doc('logout_user', security='bearerAuth')
    @api.response(200, 'Logout successful')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def post(self):
        """Logout user and revoke token"""
        jti = get_jwt()['jti']
        logger.info(f"User {get_jwt_identity()} logged out, token revoked")
        jwt_blacklist.add(jti)
        response = jsonify({'message': 'Logged out'})
        unset_jwt_cookies(response)
        logger.info(f"Response: {response}")
        return 200

@api.route('/refresh')
class Refresh(Resource):
    @api.doc('refresh_token', security='bearerAuth')
    @api.response(200, 'Token refreshed successfully', token_model)
    @api.response(401, 'Unauthorized')
    @jwt_required(refresh=True)
    def post(self):
        """Refresh access token"""
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        logger.info(f"Access token refreshed for user {identity}")
        return jsonify({'access_token': access_token, 'token_type': 'Bearer', 'expires_in': 900}), 200

@api.route('/protected')
class Protected(Resource):
    @api.doc('protected_route', security='bearerAuth')
    @api.response(200, 'Access granted')
    @api.response(401, 'Unauthorized')
    @jwt_required()
    def get(self):
        """Test protected endpoint"""
        user_id = get_jwt_identity()
        return jsonify({'message': f'Hello user {user_id}'}), 200

# JWT callbacks for token revocation
#@auth_bp.record_once
def setup_jwt_callbacks(app):
    jwt = JWTManager(app)

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