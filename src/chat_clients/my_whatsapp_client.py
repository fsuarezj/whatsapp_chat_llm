from chat_clients.whatsapp_green_client import WhatsAppGreenClient
from chatbot.assistant import Assistant
from loguru import logger
from typing import Dict
import requests

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

    def set_webhook_url(self, webhook_url):
        try:
            response = requests.post(
                f"https://api.green-api.com/waInstance{self.instance_id}/setSettings/{self.instance_token}",
                json={"webhookUrl": webhook_url}
            )
            response.raise_for_status()
            print(f"Webhook URL successfully set to: {webhook_url}")
        except Exception as e:
            print(f"Failed to set webhook URL: {str(e)}")