import pytest
from flask import Flask
from models import db
import os
import dotenv
from loguru import logger
from flask_restx import Api
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import JWTManager

# Import namespaces instead of blueprints
from routes.products import api as products_ns
from routes.auth import api as auth_ns, setup_jwt_callbacks
from routes.customers import api as customers_ns
from routes.orders import api as orders_ns

dotenv.load_dotenv()

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    # Initialize extensions
    db.init_app(app)
    limiter = Limiter(key_func=get_remote_address, default_limits=["100 per hour"])
    limiter.init_app(app)

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

    # Add RESTX namespaces
    api.add_namespace(products_ns, path='/api')
    api.add_namespace(auth_ns, path='/api')
    setup_jwt_callbacks(app)
    api.add_namespace(customers_ns, path='/api')
    api.add_namespace(orders_ns, path='/api')

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session

@pytest.fixture
def client(app):
    return app.test_client()

def get_token(client):
    resp = client.post('/api/register', json={
        'username': 'testUser',
        'password': 'Password123'
    })
    response = client.post('/api/login', json={
        'username': 'testUser',
        'password': 'Password123'
    })
    return response.get_json()['access_token']

def get_token_header(token):
    return {'Authorization': f'Bearer {token}'}