"""
Flask Application Factory Module

This module provides the application factory pattern for creating and configuring
the Flask application. It handles database initialization, API setup, middleware
configuration, and client initialization for WhatsApp and MTN Mobile Money services.

Key Components:
- Flask application creation and configuration
- SQLAlchemy database setup
- Flask-RESTX API configuration with Swagger documentation
- Rate limiting with Flask-Limiter
- JWT authentication setup
- Error handling and logging
- External service client initialization

Dependencies:
- Flask: Web framework
- Flask-RESTX: API documentation and validation
- Flask-Limiter: Rate limiting
- SQLAlchemy: Database ORM
- Loguru: Logging
- MTN MoMo: Mobile money integration
- WhatsApp Green API: WhatsApp Business API integration

Author: [Your Name]
Date: [Date]
Version: 1.0
"""

from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from flask_restx import Api
from models import db
from flask import request
from flask_cors import CORS
import dotenv
from sqlalchemy import inspect

import os
from loguru import logger

# Global rate limiter instance
# Configured with fixed-window strategy and memory storage
limiter = Limiter(
    key_func=get_remote_address,  # Use client IP address for rate limiting
    default_limits=["100 per hour"],  # Default limit: 100 requests per hour per IP
    storage_uri="memory://",  # Store rate limit data in memory
    strategy="fixed-window"  # Use fixed time window for rate limiting
)


def get_database_uri():
    """
    Get the appropriate database URI based on the environment.
    
    Returns SQLite URI for development and MariaDB URI for production.
    
    Returns:
        str: Database connection URI
        
    Environment Variables for Production:
        FLASK_ENV: Environment ('development' or 'production')
        DB_HOST: MariaDB host address
        DB_PORT: MariaDB port (default: 3306)
        DB_NAME: Database name
        DB_USER: Database username
        DB_PASSWORD: Database password
    """
    environment = os.getenv('FLASK_ENV', 'development').lower()
    
    if environment == 'development':
        # Development: Use SQLite
        return 'sqlite:///../../instance/app.db'
    elif environment == 'production':
        # Production: Use MariaDB
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', 'whatsapp_chat_llm')
        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', '')
        
        if not db_password:
            logger.warning("DB_PASSWORD not set for production database")
        
        # Construct MariaDB URI with PyMySQL driver
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
    else:
        raise ValueError(f"FLASK_ENV must be 'development' or 'production', not '{environment}'")


def check_schema_exists(db):
    """
    Check if the database schema already exists by inspecting existing tables.
    
    Args:
        db: SQLAlchemy database instance
        
    Returns:
        bool: True if schema exists (tables are present), False otherwise
    """
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    # Check if any of our expected tables exist
    expected_tables = ['user', 'product', 'customer', 'order', 'order_product']
    existing_expected_tables = [table for table in existing_tables if table in expected_tables]
    
    return len(existing_expected_tables) > 0


def create_app():
    """
    Create and configure the Flask application.
    
    This function implements the application factory pattern, creating a Flask
    app instance and configuring all necessary extensions, middleware, and
    route registrations.
    
    Configuration includes:
    - Database connection (SQLite for development, MariaDB for production)
    - JWT secret key from environment variables
    - Flask-RESTX API with Swagger documentation
    - Rate limiting middleware
    - Error handlers
    - Route namespace registration
    
    Returns:
        Flask: Configured Flask application instance
        
    Environment Variables Required:
        JWT_SECRET_KEY: Secret key for JWT token signing
        GREEN_API_INSTANCE_ID: WhatsApp Green API instance ID
        GREEN_API_INSTANCE_TOKEN: WhatsApp Green API instance token
        FLASK_ENV: Environment ('development' or 'production')
        
    Production Database Environment Variables:
        DB_HOST: MariaDB host address
        DB_PORT: MariaDB port (default: 3306)
        DB_NAME: Database name
        DB_USER: Database username
        DB_PASSWORD: Database password
        
    Raises:
        Exception: If database initialization fails
    """
    # Create Flask application instance
    app = Flask(__name__)
    #

    # Database connection for development
    #  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../../instance/app.db'
    # Configure database connection based on environment
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure JWT secret key from environment variables
    # This should be a strong, random key in production
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    
    # Initialize Flask extensions
    db.init_app(app)  # Initialize SQLAlchemy database
    limiter.init_app(app)  # Initialize rate limiter
    
    # Create database tables if they don't exist
    # This ensures the database schema is set up on first run
    with app.app_context():
        if not check_schema_exists(db):
            logger.info("Database schema not found. Creating tables...")
            db.create_all()
            logger.info("Database tables created successfully.")
        else:
            logger.info("Database schema already exists. Skipping table creation.")

    # Initialize Flask-RESTX API with Swagger documentation
    api = Api(
        app,
        version='1.0',
        title='WhatsApp Chat API',
        description='API for WhatsApp chat and business operations',
        doc='/docs',  # Swagger UI endpoint
        security='bearerAuth'  # Default security scheme
    )

    # Configure JWT Bearer token authentication scheme
    # This enables Swagger UI to include Authorization headers
    api.authorizations = {
        'bearerAuth': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
    }

    # Get CORS origins from environment variable
    cors_origins = os.getenv('CORS_ORIGINS')

    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins.split(','),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": True  # If you need to send cookies/credentials
        }
    })
    
    # Import route namespaces
    # These contain the actual API endpoints and business logic
    from routes.auth import api as auth_ns, setup_jwt_callbacks
    from routes.customers import api as customers_ns
    from routes.orders import api as orders_ns
    from routes.products import api as products_ns

    # Register API namespaces with the main API
    # All namespaces are mounted under /api prefix
    api.add_namespace(auth_ns, path='/api')  # Authentication endpoints
    setup_jwt_callbacks(app)  # Configure JWT callbacks for authentication
    api.add_namespace(customers_ns, path='/api')  # Customer management endpoints
    api.add_namespace(orders_ns, path='/api')  # Order management endpoints
    api.add_namespace(products_ns, path='/api')  # Product management endpoints

    # Register global error handlers
    register_error_handlers(app)

    # Configure rate limiter request filter
    # This function is called for every request to determine if rate limiting applies
    @limiter.request_filter
    def filter_requests():
        """
        Rate limiter request filter function.
        
        This function is called for every incoming request to determine
        whether rate limiting should be applied. Currently configured to
        not filter any requests (return False), meaning all requests
        are subject to rate limiting.
        
        Returns:
            bool: False to apply rate limiting to all requests
        """
        logger.debug(f"Rate limit check for {request.remote_addr}")
        return False # Don't filter any requests

    return app


def init_clients():
    """
    Initialize external service clients.
    
    Creates and configures clients for external services:
    - WhatsApp Green API client for messaging
    - MTN Mobile Money client for payments
    
    The WhatsApp client uses environment variables for configuration,
    while the MTN MoMo client uses placeholder values that should be
    replaced with actual credentials in production.
    
    Returns:
        tuple: (whatsapp_client, momo_client)
            - whatsapp_client: Configured MyWhatsAppClient instance
            - momo_client: Configured MTNMoMo instance
            
    Environment Variables Required:
        GREEN_API_INSTANCE_ID: WhatsApp Green API instance identifier
        GREEN_API_INSTANCE_TOKEN: WhatsApp Green API authentication token
        
    Note:
        MTN MoMo credentials are currently hardcoded and should be
        moved to environment variables for production use.
    """
    # Log WhatsApp API configuration for debugging
    logger.debug(f"GREEN_API_INSTANCE_ID: {os.getenv('GREEN_API_INSTANCE_ID')}")
    logger.debug(f"GREEN_API_INSTANCE_TOKEN: {os.getenv('GREEN_API_INSTANCE_TOKEN')}")
    
    # Initialize WhatsApp Green API client
    whatsapp = MyWhatsAppClient(
        instance_id=os.getenv('GREEN_API_INSTANCE_ID'),
        instance_token=os.getenv('GREEN_API_INSTANCE_TOKEN')
    )
    
    # Initialize MTN Mobile Money client
    # TODO: Move credentials to environment variables
    momo = MTNMoMo(
        api_key='your_api_key',  # Should be os.getenv('MTN_MOMO_API_KEY')
        user_id='your_user_id',  # Should be os.getenv('MTN_MOMO_USER_ID')
        primary_key='your_primary_key',  # Should be os.getenv('MTN_MOMO_PRIMARY_KEY')
        environment='sandbox'  # Use 'production' for live environment
    )
    
    return whatsapp, momo


def register_error_handlers(app: Flask):
    """
    Register global error handlers for the Flask application.
    
    This function sets up error handlers to provide consistent error
    responses across the application. It handles both specific exceptions
    (like rate limiting) and general exceptions.
    
    Args:
        app (Flask): Flask application instance to register handlers with
        
    Error Handlers:
        - RateLimitExceeded: Returns 429 status with rate limit message
        - Exception: Returns 500 status with generic error message
    """
    @app.errorhandler(Exception)
    def handle_exception(e):
        """
        Global exception handler.
        
        Handles all unhandled exceptions in the application. Provides
        specific handling for rate limiting errors and generic handling
        for all other exceptions.
        
        Args:
            e: The exception that was raised
            
        Returns:
            tuple: (response, status_code)
                - response: JSON error response
                - status_code: HTTP status code
        """
        # Handle rate limiting exceptions specifically
        if isinstance(e, RateLimitExceeded):
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': str(e.description)
            }), 429
        
        # Log all other exceptions for debugging
        logger.error(f"Unhandled exception: {e}")
        
        # Return generic error response for security
        return jsonify({'error': 'An unexpected error occurred.'}), 500