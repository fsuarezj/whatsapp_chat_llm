from flask import Flask, request, Response
import dotenv
import os
from typing import Dict
from chat_clients.whatsapp_green_client import WhatsAppGreenClient
from mtn_momo import MTNMoMo
import requests
import time
from loguru import logger
from chatbot.assistant import Assistant

from loguru_config import LoguruConfig
LoguruConfig.load(os.path.join("src", "config", "loguru.yaml"))

# Load environment variables
dotenv.load_dotenv()

# Initialize Flask app
app = Flask(__name__)


# Create a custom client by inheriting from WhatsAppGreenClient
class MyWhatsAppClient(WhatsAppGreenClient):
    def __init__(self, instance_id: str, instance_token: str):
        logger.debug("Initializing Whatsapp Client")
        super().__init__(instance_id, instance_token)
        self.assistant = Assistant()

    def _process_text_message(self, sender: str, sender_name: str, chat_name: str, text: str):
        """Handle incoming text messages"""
        logger.info(f"✨ New message received!")
        if chat_name == sender:
            print(f"Message in group {chat_name} from: {sender}")
        else:
            print(f"From: {sender}")
        print(f"Message: {text}")
        response = self.assistant.generate_stream_response(text)
        complete_response = ""
        for chunk in response:
            print(chunk)
            complete_response += chunk
        self.send_text_message(sender, complete_response)
        # Auto-reply
        #self.send_text_message(sender, f"Thanks for your message: {text}")

    def _process_file_message(self, sender: str, chat_name: str, file_data: Dict):
        """Handle incoming file messages"""
        print(f"Got file from {sender}: {file_data}")
        self.send_text_message(sender, "Thanks for the file!")

    def _process_location_message(self, sender: str, chat_name: str, location_data: Dict):
        """Handle incoming location messages"""
        print(f"Got location from {sender}: {location_data}")
        self.send_text_message(sender, "Thanks for sharing your location!")


# Initialize MTN MoMo client
momo = MTNMoMo(
    api_key='your_api_key',
    user_id='your_user_id',
    primary_key='your_primary_key',
    environment='sandbox'  # or 'production'
)

# Initialize WhatsApp client
whatsapp = MyWhatsAppClient(
    instance_id=os.getenv('GREEN_API_INSTANCE_ID'),
    instance_token=os.getenv('GREEN_API_INSTANCE_TOKEN')
)

# Check instance status (optional, but be careful with side effects)
try:
    status = whatsapp.get_instance_status()
    logger.info(f"Instance status: {status}")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:
        logger.error("Rate limit reached. Waiting before retrying...")
        time.sleep(5)

# Optionally send a startup message (be careful with side effects in production)
whatsapp.send_text_message(
    to='34696864400',
    message='Starting the server'
)

@app.route('/hello')
def hello_world():
    return "Flesk is running!"

# Example: Send a message
@app.route('/send_message', methods=['POST'])
def send_message():
    logger.debug("Sending message")
    try:
        response = whatsapp.send_text_message(
            to='34696864400',
            message='Hello from Green API!'
        )
        return response
    except Exception as e:
        return {'error': str(e)}, 500

# Setup webhook with authentication (runs on import)
WEBHOOK_TOKEN = os.getenv('GREEN_API_WEBHOOK_TOKEN')
whatsapp.setup_webhook(
    app=app,
    path='/webhook',
    webhook_token=WEBHOOK_TOKEN
)

#@app.route('/webhook', methods=['POST'])
#def webhook():
#    """Handle incoming webhook events with authentication"""
#    logger.debug("Received POST to /webhook")
#    try:
#        # Check for authentication token in headers
#        auth_header = request.headers.get('authorization')
#        if not auth_header or auth_header != f"Bearer {WEBHOOK_TOKEN}":
#            logger.warning("Unauthorized webhook attempt")
#            return Response("Unauthorized", status=401)
#        logger.debug("Authorized webhook")
#        
#        data = request.get_json()
#        logger.debug(f"Payload: {data}")
#        
#        if data.get('typeWebhook') == 'incomingMessageReceived':
#            message_data = data.get('messageData', {})
#            whatsapp.handle_message(data)
#            
#        return Response(status=200)
#        
#    except Exception as e:
#        logger.error(f"Error in webhook: {str(e)}")
#        return Response(status=500)


def set_webhook_url():
    # Your Codespace public URL + /webhook
    codespace_url = "https://staging-whatsapp-chat-llm/webhook"  # Replace with your actual URL
    instance_id = os.getenv('GREEN_API_INSTANCE_ID')
    instance_token = os.getenv('GREEN_API_INSTANCE_TOKEN')
    
    try:
        response = requests.post(
            f"https://api.green-api.com/waInstance{instance_id}/setSettings/{instance_token}",
            json={"webhookUrl": codespace_url}
        )
        response.raise_for_status()
        print(f"Webhook URL successfully set to: {codespace_url}")
    except Exception as e:
        print(f"Failed to set webhook URL: {str(e)}")

if __name__ == '__main__':
    # Initialize Loguru
    #LoguruConfig.load("loguru.yaml")

    #set_webhook_url()
    # Only run the development server when executing this file directly
    # This part won't run when deployed with Passenger
    app.run(port=3000, debug=False)

#transaction = momo.check_transaction('2')
#print(f"Date: {transaction['date']}")
#print(f"Amount: {transaction['amount']}")
#print(f"Phone Number: {transaction['phone_number']}")
#
#transactions = momo.get_last_transactions('phone_number_here', limit=5)
#for transaction in transactions:
#    print(f"Date: {transaction['date']}")
#    print(f"Amount: {transaction['amount']}")
#    print(f"Transaction ID: {transaction['transaction_id']}")
#
#payment = momo.request_payment(
#    phone_number='recipient_phone_number',
#    amount=100.00,
#    currency='EUR',
#    message='Payment for services'
#)
#print(f"Status: {payment['status']}")
#print(f"Transaction ID: {payment['transaction_id']}")
