from routes.auth import auth_bp
from routes.products import products_bp
from routes.whatsapp_chat import whatsapp_chat_bp, setup_chat_webhook
from app_factory import create_app, init_clients, register_error_handlers

import dotenv
import os
from loguru import logger

from loguru_config import LoguruConfig
LoguruConfig.load(os.path.join("src", "config", "loguru.yaml"))

# Load environment variables
dotenv.load_dotenv()

app = create_app()
whatsapp, momo = init_clients()
register_error_handlers(app)
# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(products_bp, url_prefix='/api')
app.register_blueprint(whatsapp_chat_bp, url_prefix='/api')


# Inject whatsapp client into chat blueprint
import routes.whatsapp_chat
routes.whatsapp_chat.whatsapp = whatsapp

# Setup webhook with authentication (runs on import)
setup_chat_webhook(app, whatsapp)

# Optionally send a startup message (be careful with side effects in production)
whatsapp.send_text_message(
    to='34696864400',
    message='Starting the server'
)

#whatsapp.set_webhook_url("https://staging-whatsapp-chat-llm/webhook")

if __name__ == '__main__':
    app.run(port=3000, debug=True)

## Check instance status (optional, but be careful with side effects)
#try:
#    status = whatsapp.get_instance_status()
#    logger.info(f"Instance status: {status}")
#except requests.exceptions.HTTPError as e:
#    if e.response.status_code == 429:
#        logger.error("Rate limit reached. Waiting before retrying...")
#        time.sleep(5)

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
