import pytest
from flask import Flask
from models import db
import os
import dotenv
from loguru import logger
from routes.auth import auth_bp
from routes.products import products_bp
from routes.customers import customers_bp
from routes.orders import orders_bp

dotenv.load_dotenv()

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')

    db.init_app(app)
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(products_bp, url_prefix='/api')
    app.register_blueprint(customers_bp, url_prefix='/api')
    app.register_blueprint(orders_bp, url_prefix='/api')

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