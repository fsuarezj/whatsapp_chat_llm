from flask import Blueprint, request
from loguru import logger
import os

whatsapp_chat_bp = Blueprint('whatsapp_chat', __name__)

# These will be set from app.py
whatsapp = None

@whatsapp_chat_bp.route('/hello')
def hello_world():
    return "Flesk is running!"

@whatsapp_chat_bp.route('/send_message', methods=['POST'])
def send_message():
    logger.debug("Sending message")
    try:
        response = whatsapp.send_text_message(
            to='34696864400',
            message='Test message from Green API!'
        )
        return response
    except Exception as e:
        return {'error': str(e)}, 500

def setup_chat_webhook(app, whatsapp_client):
    WEBHOOK_TOKEN = os.getenv('GREEN_API_WEBHOOK_TOKEN')
    whatsapp_client.setup_webhook(
        app=app,
        path='/webhook',
        webhook_token=WEBHOOK_TOKEN
    )