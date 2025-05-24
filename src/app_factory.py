from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from flask_restx import Api
from models import db
from flask import request

from mtn_momo import MTNMoMo
from chat_clients.my_whatsapp_client import MyWhatsAppClient

import os
from loguru import logger

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()

    # Initialize Flask-RESTX
    api = Api(
        app,
        version='1.0',
        title='WhatsApp Chat API',
        description='API for WhatsApp chat and business operations',
        doc='/docs',
        security='bearerAuth'
    )

    # Add security scheme
    api.authorizations = {
        'bearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    }

    from routes.auth import api as auth_ns, setup_jwt_callbacks
    from routes.customers import api as customers_ns
    from routes.orders import api as orders_ns
    from routes.products import api as products_ns

    # Add namespaces
    api.add_namespace(auth_ns, path='/api')
    setup_jwt_callbacks(app)
    api.add_namespace(customers_ns, path='/api')
    api.add_namespace(orders_ns, path='/api')
    api.add_namespace(products_ns, path='/api')

    # Register error handlers
    register_error_handlers(app)

    @limiter.request_filter
    def filter_requests():
        logger.debug(f"Rate limit check for {request.remote_addr}")
        return False  # Don't filter any requests

    return app

def init_clients():
    whatsapp = MyWhatsAppClient(
        instance_id=os.getenv('GREEN_API_INSTANCE_ID'),
        instance_token=os.getenv('GREEN_API_INSTANCE_TOKEN')
    )
    momo = MTNMoMo(
        api_key='your_api_key',
        user_id='your_user_id',
        primary_key='your_primary_key',
        environment='sandbox'
    )
    return whatsapp, momo

def register_error_handlers(app: Flask):
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, RateLimitExceeded):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': str(e.description)
            }), 429
        logger.error(f"Unhandled exception: {e}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)