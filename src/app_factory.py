from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import db

from mtn_momo import MTNMoMo
from chat_clients.my_whatsapp_client import MyWhatsAppClient

import os
from loguru import logger

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    db.init_app(app)
    with app.app_context():
        db.create_all()  # This will create tables if they do not exist
    limiter.init_app(app)
    register_error_handlers(app)
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
        logger.error(f"Unhandled exception: {e}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500

limiter = Limiter(key_func=get_remote_address, default_limits=["100 per hour"])