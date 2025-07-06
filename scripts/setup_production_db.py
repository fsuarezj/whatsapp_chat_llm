#!/usr/bin/env python3
"""
Production Database Setup Script

This script helps set up the MariaDB database for production deployment.
It creates the database and user if they don't exist.

Usage:
    python scripts/setup_production_db.py

Environment Variables Required:
    DB_HOST: MariaDB host address
    DB_PORT: MariaDB port (default: 3306)
    DB_NAME: Database name
    DB_USER: Database username
    DB_PASSWORD: Database password
    DB_ROOT_PASSWORD: Root password for MariaDB (optional, for creating user/database)

Author: [Your Name]
Date: [Date]
Version: 1.2
"""

import os
import sys
from pathlib import Path
import pymysql
from loguru import logger
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

def validate_environment():
    """Validate required environment variables"""
    required_vars = {
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_NAME': os.getenv('DB_NAME', 'whatsapp_chat_llm'),
        'DB_USER': os.getenv('DB_USER', 'whatsapp_user'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', ''),
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        return False
    
    return True

def test_mysql_connection(host, port, user, password, database=None):
    """Test MySQL/MariaDB connection"""
    try:
        connection_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'charset': 'utf8mb4'
        }
        
        if database:
            connection_params['database'] = database
            
        conn = pymysql.connect(**connection_params)
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            logger.info(f"Connected to MySQL/MariaDB version: {version[0]}")
            
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def check_database_exists(host, port, user, password, database):
    """Check if database exists and user has access to it"""
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        
        with conn.cursor() as cursor:
            # Test if we can access the database
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()
            if current_db and current_db[0] == database:
                logger.info(f"✓ Database '{database}' exists and is accessible")
                return True
        
        conn.close()
        return True
    except Exception as e:
        logger.info(f"Database '{database}' is not accessible: {e}")
        return False

def setup_production_database():
    """Set up MariaDB database and user for production"""
    
    # Validate environment variables
    if not validate_environment():
        sys.exit(1)
    
    # Get database configuration from environment
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', '3306'))
    db_name = os.getenv('DB_NAME', 'whatsapp_chat_llm')
    db_user = os.getenv('DB_USER', 'whatsapp_user')
    db_password = os.getenv('DB_PASSWORD', '')
    db_root_password = os.getenv('DB_ROOT_PASSWORD', '')
    
    logger.info(f"Setting up database '{db_name}' on {db_host}:{db_port}")
    
    try:
        # First, try to connect with the application user to the specific database
        logger.info("Testing application user connection to database...")
        if check_database_exists(db_host, db_port, db_user, db_password, db_name):
            logger.info("✓ Database already exists and is accessible with application user")
            logger.info("✓ Production database setup completed successfully")
            logger.info("Next steps:")
            logger.info("1. Run database migration: python scripts/migrate_database.py")
            logger.info("2. Fix password column if needed: python scripts/fix_password_column.py")
            logger.info("3. Start the application: python src/app.py")
            return
        
        # If we can't connect to the database, try connecting without specifying database
        logger.info("Testing application user connection without database...")
        if test_mysql_connection(db_host, db_port, db_user, db_password):
            logger.info("✓ Application user exists but database access failed")
            logger.info("Database may not exist or user lacks permissions")
        else:
            logger.info("✗ Application user connection failed")
        
        # Only use root password if provided and needed
        if db_root_password:
            logger.info("Testing root connection...")
            if not test_mysql_connection(db_host, db_port, 'root', db_root_password):
                logger.error("Failed to connect as root. Check DB_ROOT_PASSWORD and server accessibility.")
                sys.exit(1)
            
            # Connect as root to create database and user
            root_conn = pymysql.connect(
                host=db_host,
                port=db_port,
                user='root',
                password=db_root_password,
                charset='utf8mb4'
            )
            
            with root_conn.cursor() as cursor:
                # Create database if it doesn't exist
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info(f"✓ Database '{db_name}' created or already exists")
                
                # Create user if it doesn't exist
                cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_password}'")
                logger.info(f"✓ User '{db_user}' created or already exists")
                
                # Grant privileges
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%'")
                cursor.execute("FLUSH PRIVILEGES")
                logger.info(f"✓ Privileges granted to user '{db_user}' on database '{db_name}'")
            
            root_conn.close()
        else:
            logger.warning("DB_ROOT_PASSWORD not provided and database setup is needed")
            logger.info("Please provide DB_ROOT_PASSWORD or create the database and user manually:")
            logger.info(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            logger.info(f"CREATE USER '{db_user}'@'%' IDENTIFIED BY '{db_password}';")
            logger.info(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'%';")
            logger.info("FLUSH PRIVILEGES;")
            sys.exit(1)
        
        # Final test connection with the application user
        logger.info("Testing application user connection...")
        if not test_mysql_connection(db_host, db_port, db_user, db_password, db_name):
            logger.error("Failed to connect with application user. Check user permissions.")
            sys.exit(1)
        
        logger.info("✓ Production database setup completed successfully")
        logger.info("Next steps:")
        logger.info("1. Run database migration: python scripts/migrate_database.py")
        logger.info("2. Fix password column if needed: python scripts/fix_password_column.py")
        logger.info("3. Start the application: python src/app.py")
        
    except Exception as e:
        logger.error(f"✗ Database setup failed: {e}")
        logger.error("Please check your MariaDB server is running and accessible")
        sys.exit(1)

def main():
    """Main function with error handling"""
    try:
        setup_production_database()
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 