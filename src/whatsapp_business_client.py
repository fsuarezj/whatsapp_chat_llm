import requests
from flask import Flask, request, Response
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime

class WhatsAppBusinessClient:
    def __init__(self, token: str, phone_number_id: str, version: str = 'v17.0'):
        """
        Initialize WhatsApp Client with your Meta credentials
        
        Args:
            token: Your Meta API token
            phone_number_id: Your WhatsApp Business Phone Number ID
            version: API version
        """
        self.token = token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/{version}/{phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=f'whatsapp_{datetime.now().strftime("%Y%m%d")}.log'
        )
        self.logger = logging.getLogger(__name__)

    def send_text_message(self, to: str, message: str, preview_url: bool = False) -> Dict:
        """
        Send a text message to a WhatsApp number
        
        Args:
            to: Recipient's phone number (international format without +)
            message: Text message to send
            preview_url: Whether to preview URLs in the message
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": preview_url,
                    "body": message
                }
            }
            
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"Message sent successfully to {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send message to {to}: {str(e)}")
            raise

    def send_template_message(self, to: str, template_name: str, 
                            language_code: str, components: Optional[List[Dict]] = None) -> Dict:
        """
        Send a template message
        
        Args:
            to: Recipient's phone number
            template_name: Name of the template
            language_code: Language code (e.g., "en")
            components: Template components (optional)
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code
                    }
                }
            }

            if components:
                payload["template"]["components"] = components

            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"Template message sent successfully to {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send template message to {to}: {str(e)}")
            raise

    def send_media_message(self, to: str, media_type: str, media_url: str, 
                          caption: Optional[str] = None) -> Dict:
        """
        Send a media message (image, video, audio, document)
        
        Args:
            to: Recipient's phone number
            media_type: Type of media ('image', 'video', 'audio', 'document')
            media_url: URL of the media file
            caption: Optional caption for the media
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": media_type,
                media_type: {
                    "link": media_url
                }
            }

            if caption and media_type in ['image', 'video', 'document']:
                payload[media_type]["caption"] = caption

            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            self.logger.info(f"Media message sent successfully to {to}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send media message to {to}: {str(e)}")
            raise

    def setup_webhook(self, app: Flask, path: str, verify_token: str):
        """
        Setup webhook endpoints for receiving messages
        
        Args:
            app: Flask application instance
            path: Webhook path
            verify_token: Verification token for webhook setup
        """
        @app.route(path, methods=['GET'])
        def verify():
            """Handle webhook verification from Meta"""
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')

            if mode and token:
                if mode == 'subscribe' and token == verify_token:
                    self.logger.info('Webhook verified successfully')
                    return challenge
                return Response(status=403)

        @app.route(path, methods=['POST'])
        def webhook():
            """Handle incoming webhook events"""
            data = request.get_json()
            
            if data['object']:
                if (data.get('entry') and
                    data['entry'][0].get('changes') and
                    data['entry'][0]['changes'][0].get('value')):
                    
                    value = data['entry'][0]['changes'][0]['value']
                    
                    # Handle different types of messages
                    if value.get('messages'):
                        message = value['messages'][0]
                        self._handle_message(message, value)
                    elif value.get('statuses'):
                        status = value['statuses'][0]
                        self._handle_status_update(status)
                    
                return 'EVENT_RECEIVED'
            return Response(status=404)

    def _handle_message(self, message: Dict, value: Dict):
        """
        Handle different types of incoming messages
        
        Args:
            message: Message data from webhook
            value: Complete value object from webhook
        """
        try:
            msg_type = message.get('type')
            from_number = value.get('contacts', [{}])[0].get('wa_id')
            
            if msg_type == 'text':
                text = message.get('text', {}).get('body', '')
                self.logger.info(f"Received text message from {from_number}: {text}")
                self._process_text_message(from_number, text)
                
            elif msg_type in ['image', 'video', 'audio', 'document']:
                media_id = message.get(msg_type, {}).get('id')
                self.logger.info(f"Received {msg_type} message from {from_number}")
                self._process_media_message(from_number, msg_type, media_id)
                
            elif msg_type == 'location':
                location = message.get('location', {})
                self.logger.info(f"Received location from {from_number}")
                self._process_location_message(from_number, location)
                
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")

    def _process_text_message(self, from_number: str, text: str):
        """Override this method to handle text messages"""
        pass

    def _process_media_message(self, from_number: str, media_type: str, media_id: str):
        """Override this method to handle media messages"""
        pass

    def _process_location_message(self, from_number: str, location: Dict):
        """Override this method to handle location messages"""
        pass

    def _handle_status_update(self, status: Dict):
        """Handle message status updates"""
        try:
            status_type = status.get('status')
            message_id = status.get('id')
            self.logger.info(f"Message {message_id} status: {status_type}")
            
        except Exception as e:
            self.logger.error(f"Error handling status update: {str(e)}")