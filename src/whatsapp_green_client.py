import requests
from flask import Flask, request, Response
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import os
from pprint import pprint

class WhatsAppGreenClient:
    def __init__(self, instance_id: str, instance_token: str):
        """
        Initialize WhatsApp Green API Client
        
        Args:
            instance_id: Your Green API Instance ID
            instance_token: Your Green API Instance Token
        """
        self.instance_id = os.getenv('GREEN_API_INSTANCE_ID')
        self.instance_token = os.getenv('GREEN_API_INSTANCE_TOKEN')
        self.base_url = f"https://7105.api.green-api.com/waInstance{instance_id}"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=f'whatsapp_green_{datetime.now().strftime("%Y%m%d")}.log'
        )
        self.logger = logging.getLogger(__name__)

    def send_text_message(self, to: str, message: str) -> Dict:
        """
        Send a text message to a WhatsApp number
        
        Args:
            to: Recipient's phone number (with country code, no +)
            message: Text message to send
        """
        try:
            endpoint = f"{self.base_url}/sendMessage/{self.instance_token}"
            payload = {
                "chatId": f"{to}@c.us",
                "message": message
            }
            
            response = requests.post(
                endpoint,
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"Message sent successfully to {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send message to {to}: {str(e)}")
            raise

    def send_file(self, to: str, file_url: str, caption: Optional[str] = None) -> Dict:
        """
        Send a file to a WhatsApp number
        
        Args:
            to: Recipient's phone number
            file_url: URL of the file to send
            caption: Optional caption for the file
        """
        try:
            endpoint = f"{self.base_url}/sendFileByUrl/{self.instance_token}"
            payload = {
                "chatId": f"{to}@c.us",
                "urlFile": file_url,
                "fileName": file_url.split('/')[-1]
            }
            
            if caption:
                payload["caption"] = caption

            response = requests.post(
                endpoint,
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"File sent successfully to {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send file to {to}: {str(e)}")
            raise

    def send_location(self, to: str, latitude: float, longitude: float, name: Optional[str] = None) -> Dict:
        """
        Send a location to a WhatsApp number
        
        Args:
            to: Recipient's phone number
            latitude: Location latitude
            longitude: Location longitude
            name: Optional location name
        """
        try:
            endpoint = f"{self.base_url}/sendLocation/{self.instance_token}"
            payload = {
                "chatId": f"{to}@c.us",
                "latitude": latitude,
                "longitude": longitude
            }
            
            if name:
                payload["nameLocation"] = name

            response = requests.post(
                endpoint,
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"Location sent successfully to {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send location to {to}: {str(e)}")
            raise

    def setup_webhook(self, app: Flask, path: str):
        """
        Setup webhook endpoint for receiving messages
        
        Args:
            app: Flask application instance
            path: Webhook path
        """
        @app.route(path, methods=['POST'])
        def webhook():
            """Handle incoming webhook events"""
            try:
                data = request.get_json()
                pprint(data)
                
                if data.get('typeWebhook') == 'incomingMessageReceived':
                    message_data = data.get('messageData', {})
                    self._handle_message(data)
                    
                return Response(status=200)
                
            except Exception as e:
                self.logger.error(f"Error in webhook: {str(e)}")
                return Response(status=500)

    def _handle_message(self, message_data: Dict):
        """
        Handle different types of incoming messages
        
        Args:
            message_data: Message data from webhook
        """
        try:
            message_type = message_data.get('messageData').get('typeMessage')
            sender = message_data.get('senderData', {}).get('sender')
            sender_name = message_data.get('senderData', {}).get('senderName')
            
            if message_type == 'textMessage':
                text = message_data.get('messageData').get('textMessageData', {}).get('textMessage', '')
                self.logger.info(f"Received text message from {sender}: {text}")
                self._process_text_message(sender_name, text)
                
            elif message_type == 'fileMessage':
                file_data = message_data.get('messageData').get('fileMessageData', {})
                self.logger.info(f"Received file from {sender}")
                self._process_file_message(sender, file_data)
                
            elif message_type == 'locationMessage':
                location_data = message_data.get('messageData').get('locationMessageData', {})
                self.logger.info(f"Received location from {sender}")
                self._process_location_message(sender, location_data)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")

    def _process_text_message(self, sender: str, text: str):
        """Override this method to handle text messages"""
        pass

    def _process_file_message(self, sender: str, file_data: Dict):
        """Override this method to handle file messages"""
        pass

    def _process_location_message(self, sender: str, location_data: Dict):
        """Override this method to handle location messages"""
        pass

    def get_instance_status(self) -> Dict:
        """Get the status of the WhatsApp instance"""
        try:
            endpoint = f"{self.base_url}/getStateInstance/{self.instance_token}"
            response = requests.get(endpoint)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get instance status: {str(e)}")
            raise 