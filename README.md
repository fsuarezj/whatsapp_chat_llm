# WhatsApp Chat LLM

A Flask-based WhatsApp chat application with LLM integration for business operations.

## Features

- WhatsApp Business API integration
- LLM-powered chat assistant
- Customer and order management
- Product catalog
- MTN Mobile Money integration
- RESTful API with Swagger documentation

## Database Configuration

This application supports two database configurations:

### Development (Default)
- **Database**: SQLite
- **File**: `instance/app.db`
- **Configuration**: Automatic, no additional setup required

### Production
- **Database**: MariaDB/MySQL
- **Driver**: PyMySQL
- **Configuration**: Set environment variables

#### Required Environment Variables for Production

```bash
FLASK_ENV=production
DB_HOST=your-mariadb-host
DB_PORT=3306
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
```

#### MariaDB Setup

1. Install MariaDB on your server
2. Create a database and user:
   ```sql
   CREATE DATABASE whatsapp_chat_llm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'whatsapp_user'@'%' IDENTIFIED BY 'your_secure_password';
   GRANT ALL PRIVILEGES ON whatsapp_chat_llm.* TO 'whatsapp_user'@'%';
   FLUSH PRIVILEGES;
   ```

3. Set the environment variables in your production environment
4. Run database migrations: `python scripts/migrate_database.py`

## Installation

1. Clone the repository
2. Install dependencies: `uv sync`
3. Copy `.env.example` to `.env` and configure your environment variables
4. Run the application: `python src/app.py`

## API Documentation

Once running, visit `/docs` for interactive API documentation.

## License

[License information]
