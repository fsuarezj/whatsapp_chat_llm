from flask import Flask, request, Response
import dotenv
import os
from typing import Dict
from chat_clients.whatsapp_green_client import WhatsAppGreenClient
from mtn_momo import MTNMoMo
import requests
import time

# Load environment variables
dotenv.load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Create a custom client by inheriting from WhatsAppGreenClient
class MyWhatsAppClient(WhatsAppGreenClient):
    def _process_text_message(self, sender: str, chat_name: str, text: str):
        """Handle incoming text messages"""
        print(f"✨ New message received!")
        if chat_name == sender:
            print(f"Message in group {chat_name} from: {sender}")
        else:
            print(f"From: {sender}")
        print(f"Message: {text}")
            
        # Auto-reply
        self.send_text_message(sender, f"Thanks for your message: {text}")

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

# Example: Send a message
@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        response = whatsapp.send_text_message(
            to='34696864400',
            message='Hello from Green API!'
        )
        return response
    except Exception as e:
        return {'error': str(e)}, 500

# Example: Send a file
@app.route('/send_file', methods=['POST'])
def send_file():
    try:
        response = whatsapp.send_file(
            to='1234567890',
            file_url='https://example.com/file.pdf',
            caption='Check this out!'
        )
        return response
    except Exception as e:
        return {'error': str(e)}, 500

def set_webhook_url():
    # Your Codespace public URL + /webhook
    codespace_url = "https://psychic-cod-vwgjv9xpj9fx4q7-3000.app.github.dev/webhook"  # Replace with your actual URL
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

    # Initialize WhatsApp client
    whatsapp = MyWhatsAppClient(
        instance_id=os.getenv('GREEN_API_INSTANCE_ID'),
        instance_token=os.getenv('GREEN_API_INSTANCE_TOKEN')
    )

    # Setup webhook with authentication
    WEBHOOK_TOKEN = os.getenv('GREEN_API_WEBHOOK_TOKEN')  # Add this to your .env file
    whatsapp.setup_webhook(
        app=app,
        path='/webhook',
        webhook_token=WEBHOOK_TOKEN
    )

    try:
        status = whatsapp.get_instance_status()
        print(f"Instance status: {status}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limit reached. Waiting before retrying...")
            time.sleep(5)  # Wait 5 seconds before continuing
    
    whatsapp.send_text_message(
        to='34696864400',
        message='Starting the server'
    )
    
    #set_webhook_url()
    app.run(port=3000, debug=True)

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
