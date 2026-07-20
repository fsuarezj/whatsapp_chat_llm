from flask import Flask, request, Response
import dotenv
import os
from typing import Dict, Optional
from chat_clients.whatsapp_green_client import WhatsAppGreenClient
from mtn_momo import MTNMoMo
import requests
import time
from loguru_config import LoguruConfig
from chatbot.assistant import Assistant

dotenv.load_dotenv()

app = Flask(__name__)


def _create_momo_client() -> Optional[MTNMoMo]:
    api_key = os.getenv("MTN_MOMO_API_KEY")
    user_id = os.getenv("MTN_MOMO_USER_ID")
    primary_key = os.getenv("MTN_MOMO_PRIMARY_KEY")
    if not all([api_key, user_id, primary_key]):
        return None
    return MTNMoMo(
        api_key=api_key,
        user_id=user_id,
        primary_key=primary_key,
        environment=os.getenv("MTN_MOMO_ENVIRONMENT", "sandbox"),
    )


momo = _create_momo_client()


class MyWhatsAppClient(WhatsAppGreenClient):
    def __init__(self, instance_id: str, instance_token: str):
        super().__init__(instance_id, instance_token)
        self.assistant = Assistant()

    def _process_text_message(self, sender: str, sender_name: str, chat_name: str, text: str):
        """Handle incoming text messages."""
        print("New message received!")
        if chat_name == sender:
            print(f"Message in group {chat_name} from: {sender}")
        else:
            print(f"From: {sender} ({sender_name})")
        print(f"Message: {text}")

        phone = sender.split("@")[0] if "@" in sender else sender
        response = self.assistant.generate_stream_response(text, customer_phone=phone)
        complete_response = ""
        for chunk in response:
            print(chunk)
            complete_response += chunk
        self.send_text_message(sender, complete_response)

    def _process_file_message(self, sender: str, chat_name: str, file_data: Dict):
        print(f"Got file from {sender}: {file_data}")
        self.send_text_message(sender, "Thanks for the file!")

    def _process_location_message(self, sender: str, chat_name: str, location_data: Dict):
        print(f"Got location from {sender}: {location_data}")
        self.send_text_message(sender, "Thanks for sharing your location!")


def _init_whatsapp_client() -> MyWhatsAppClient:
    instance_id = os.getenv("GREEN_API_INSTANCE_ID")
    instance_token = os.getenv("GREEN_API_INSTANCE_TOKEN")
    webhook_token = os.getenv("GREEN_API_WEBHOOK_TOKEN")

    whatsapp = MyWhatsAppClient(instance_id=instance_id, instance_token=instance_token)
    whatsapp.setup_webhook(app=app, path="/webhook", webhook_token=webhook_token)
    return whatsapp


@app.route("/hello")
def hello_world():
    return "Flask is running!"


def set_webhook_url(webhook_url: str) -> None:
    instance_id = os.getenv("GREEN_API_INSTANCE_ID")
    instance_token = os.getenv("GREEN_API_INSTANCE_TOKEN")
    if not webhook_url or not instance_id or not instance_token:
        print("Skipping webhook setup: missing WEBHOOK_URL or Green API credentials")
        return

    try:
        response = requests.post(
            f"https://api.green-api.com/waInstance{instance_id}/setSettings/{instance_token}",
            json={"webhookUrl": webhook_url},
            timeout=30,
        )
        response.raise_for_status()
        print(f"Webhook URL successfully set to: {webhook_url}")
    except Exception as exc:
        print(f"Failed to set webhook URL: {exc}")


if __name__ == "__main__":
    loguru_config_path = os.path.join(os.path.dirname(__file__), "config", "loguru.yaml")
    if os.path.exists(loguru_config_path):
        LoguruConfig.load(loguru_config_path)

    whatsapp = _init_whatsapp_client()

    try:
        status = whatsapp.get_instance_status()
        print(f"Instance status: {status}")
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            print("Rate limit reached. Waiting before retrying...")
            time.sleep(5)

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        set_webhook_url(webhook_url)

    startup_phone = os.getenv("STARTUP_NOTIFY_PHONE")
    if startup_phone:
        whatsapp.send_text_message(to=startup_phone, message="Starting the server")

    port = int(os.getenv("BOT_PORT", "3000"))
    app.run(host="0.0.0.0", port=port, debug=False)
