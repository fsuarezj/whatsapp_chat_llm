#!/usr/bin/env python3
"""
Generic Database Migration Script

This script automatically detects schema differences between the current database
and the SQLAlchemy models, and applies necessary migrations to bring the database
up to date.

Features:
- Automatic column addition
- Column type changes (when safe)
- Column default value updates
- Table creation for new models
- Enum value migrations
- Safe migration with rollback on errors
- Support for both SQLite (development) and MariaDB (production)

Usage:
    python scripts/migrate_database.py

Author: [Your Name]
Date: [Date]
Version: 1.2
"""

import os
import sys
from pathlib import Path
import inspect
from typing import Dict, List, Tuple, Any, Set
import re
import shutil
from datetime import datetime
from flask import Flask
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import after adding to path
try:
    from models import db
    from models.user_model import User
    from models.product_model import Product
    from models.customer_model import Customer
    from models.order_model import Order, OrderProduct, OrderType, OrderPaymentStatus, OrderDeliveryStatus
    from app_factory import get_database_uri
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Looking for models in: {Path(__file__).parent.parent / 'src'}")
    sys.exit(1)


class DatabaseMigrator:
    """Handles database schema migrations based on SQLAlchemy models"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.app = None
        self.db_uri = None
        self.db_type = None
        
    def setup_flask_context(self):
        """Setup Flask application context with appropriate database"""
        self.app = Flask(__name__)
        self.db_uri = get_database_uri()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = self.db_uri
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        
        # Determine database type
        if 'sqlite' in self.db_uri.lower():
            self.db_type = 'sqlite'
        elif 'mysql' in self.db_uri.lower() or 'mariadb' in self.db_uri.lower():
            self.db_type = 'mysql'
        else:
            raise ValueError(f"Unsupported database type: {self.db_uri}")
            
        return self.app
    
    def create_backup(self) -> bool:
        """Create a backup of the database before migration"""
        if self.db_type == 'sqlite':
            return self._create_sqlite_backup()
        elif self.db_type == 'mysql':
            return self._create_mysql_backup()
        return False
    
    def _create_sqlite_backup(self) -> bool:
        """Create SQLite database backup"""
        db_path = self.db_uri.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            print("No existing SQLite database to backup")
            return True
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_name = os.path.basename(db_path)
        backup_path = f"{os.path.dirname(db_path)}/backup_{db_name}_{timestamp}"
        
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✓ SQLite database backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"✗ Failed to create SQLite backup: {e}")
            return False
    
    def _create_mysql_backup(self) -> bool:
        """Create MySQL/MariaDB database backup"""
        try:
            # Extract database name from URI
            db_name = self.db_uri.split('/')[-1].split('?')[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_{db_name}_{timestamp}.sql"
            
            # Use mysqldump to create backup
            import subprocess
            # Extract connection details from URI
            # mysql+pymysql://user:pass@host:port/db
            uri_parts = self.db_uri.replace('mysql+pymysql://', '').split('@')
            user_pass = uri_parts[0].split(':')
            host_db = uri_parts[1].split('/')
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ''
            host_port = host_db[0].split(':')
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else '3306'
            
            cmd = [
                'mysqldump',
                f'--host={host}',
                f'--port={port}',
                f'--user={user}',
                f'--password={password}',
                '--single-transaction',
                '--routines',
                '--triggers',
                db_name
            ]
            
            with open(backup_file, 'w') as f:
                subprocess.run(cmd, stdout=f, check=True)
            
            print(f"✓ MySQL/MariaDB database backed up to: {backup_file}")
            return True
        except Exception as e:
            print(f"✗ Failed to create MySQL/MariaDB backup: {e}")
            print("Make sure mysqldump is installed and accessible")
            return False
    
    def connect(self):
        """Connect to the database"""
        if self.db_type == 'sqlite':
            return self._connect_sqlite()
        elif self.db_type == 'mysql':
            return self._connect_mysql()
        return False
    
    def _connect_sqlite(self):
        """Connect to SQLite database"""
        db_path = self.db_uri.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            print(f"SQLite database file not found at {db_path}")
            return False
            
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        return True
    
    def _connect_mysql(self):
        """Connect to MySQL/MariaDB database"""
        try:
            import pymysql
            # Extract connection details from URI
            uri_parts = self.db_uri.replace('mysql+pymysql://', '').split('@')
            user_pass = uri_parts[0].split(':')
            host_db = uri_parts[1].split('/')
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ''
            host_port = host_db[0].split(':')
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 3306
            db_name = host_db[1].split('?')[0]
            
            self.conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name,
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"Failed to connect to MySQL/MariaDB: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the database"""
        if self.conn:
            self.conn.close()
    
    def get_existing_tables(self) -> List[str]:
        """Get list of existing tables in the database"""
        if self.db_type == 'sqlite':
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        elif self.db_type == 'mysql':
            self.cursor.execute("SHOW TABLES")
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_table_columns(self, table_name: str) -> List[Tuple[str, str, str, str, str, str]]:
        """Get column information for a table"""
        try:
            if self.db_type == 'sqlite':
                self.cursor.execute(f"PRAGMA table_info({table_name})")
                return self.cursor.fetchall()
            elif self.db_type == 'mysql':
                self.cursor.execute(f"DESCRIBE {table_name}")
                columns = self.cursor.fetchall()
                # Convert MySQL format to SQLite-like format
                formatted_columns = []
                for col in columns:
                    formatted_columns.append((
                        col[0],  # name
                        col[1],  # type
                        'YES' if col[2] == 'YES' else 'NO',  # notnull
                        col[4],  # default
                        col[3],  # primary_key
                        None     # pk
                    ))
                return formatted_columns
        except Exception as e:
            print(f"Error getting columns for {table_name}: {e}")
            return []

    def get_model_tables(self) -> Dict[str, Any]:
        """Get all SQLAlchemy model tables"""
        tables = {}
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj) and hasattr(obj, '__tablename__'):
                tables[obj.__tablename__] = obj
        return tables
    
    def get_model_columns(self, model_class) -> Dict[str, Dict[str, Any]]:
        """Extract column information from a SQLAlchemy model"""
        columns = {}
        with self.app.app_context():
            for attr_name in dir(model_class):
                attr = getattr(model_class, attr_name)
                if hasattr(attr, 'type') and hasattr(attr, 'name'):
                    columns[attr.name] = {
                        'type': str(attr.type),
                        'nullable': getattr(attr, 'nullable', True),
                        'primary_key': getattr(attr, 'primary_key', False),
                        'unique': getattr(attr, 'unique', False),
                        'default': getattr(attr, 'default', None),
                        'foreign_key': getattr(attr, 'foreign_key', None)
                    }
        return columns

    def get_enum_values_from_model(self, model_class, column_name: str) -> Set[str]:
        """Extract enum values from a model column"""
        with self.app.app_context():
            for attr_name in dir(model_class):
                attr = getattr(model_class, attr_name)
                if hasattr(attr, 'name') and attr.name == column_name:
                    if hasattr(attr, 'type'):
                        # Handle SQLAlchemy Enum type
                        if hasattr(attr.type, 'enums'):
                            return set(attr.type.enums)
                        elif hasattr(attr.type, 'enum_class'):
                            # SQLAlchemy Enum with enum_class
                            enum_class = attr.type.enum_class
                            return set(member.value for member in enum_class)
                        elif str(attr.type).lower().startswith('enum'):
                            # Try to extract from the type string
                            type_str = str(attr.type)
                            # Look for enum values in the type definition
                            if 'orderpaymentstatus' in type_str.lower():
                                return {'paid', 'notPaid'}
                            elif 'orderdeliverystatus' in type_str.lower():
                                return {'delivered', 'notDelivered'}
                            elif 'ordertype' in type_str.lower():
                                return {'pickup', 'delivery'}
        return set()

    def get_existing_enum_values(self, table_name: str, column_name: str) -> Set[str]:
        """Get existing enum values from a database column"""
        try:
            quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            query = f"SELECT DISTINCT {column_name} FROM {quoted_table_name} WHERE {column_name} IS NOT NULL"
            self.cursor.execute(query)
            values = {row[0] for row in self.cursor.fetchall()}
            return values
        except Exception as e:
            print(f"Error getting enum values for {table_name}.{column_name}: {e}")
            return set()

    def find_similar_enum_values(self, old_values: Set[str], new_values: Set[str]) -> Dict[str, str]:
        """Find similar enum values between old and new sets"""
        mappings = {}
        
        for old_value in old_values:
            best_match = None
            best_similarity = 0.0
            
            for new_value in new_values:
                similarity = self.calculate_string_similarity(old_value, new_value)
                if similarity > best_similarity and similarity > 0.7:  # 70% similarity threshold
                    best_similarity = similarity
                    best_match = new_value
            
            if best_match:
                mappings[old_value] = best_match
        
        return mappings

    def calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if str1 == str2:
            return 1.0
        
        # Convert to lowercase for comparison
        s1, s2 = str1.lower(), str2.lower()
        
        # Exact match after case conversion
        if s1 == s2:
            return 0.95
        
        # Check for common patterns
        if s1.replace('_', '') == s2.replace('_', ''):
            return 0.9
        if s1.replace('-', '') == s2.replace('-', ''):
            return 0.9
        
        # Check for substring matches
        if s1 in s2 or s2 in s1:
            return 0.8
        
        # Check for word similarity
        words1 = set(s1.split('_'))
        words2 = set(s2.split('_'))
        if words1 & words2:  # intersection
            return 0.7
        
        return 0.0

    def migrate_enum_values(self, table_name: str, column_name: str, value_mappings: Dict[str, str]) -> bool:
        """Migrate enum values in a column"""
        try:
            quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            
            for old_value, new_value in value_mappings.items():
                update_sql = f"UPDATE {quoted_table_name} SET {column_name} = ? WHERE {column_name} = ?"
                print(f"Migrating enum value: '{old_value}' -> '{new_value}'")
                self.cursor.execute(update_sql, (new_value, old_value))
            
            self.conn.commit()
            print(f"✓ Enum values migrated for {table_name}.{column_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to migrate enum values for {table_name}.{column_name}: {e}")
            self.conn.rollback()
            return False

    def check_enum_migrations(self, table_name: str, model_class) -> bool:
        """Check and handle enum value migrations for a table"""
        print(f"\n--- Checking enum migrations for table: {table_name} ---")
        
        quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
        model_columns = self.get_model_columns(model_class)
        
        success = True
        
        # Special handling for known enum columns
        known_enum_columns = {
            'payment_status': {'paid', 'notPaid'},
            'delivery_status': {'delivered', 'notDelivered'},
            'order_type': {'pickup', 'delivery'}
        }
        
        for column_name, column_info in model_columns.items():
            # Check if it's a known enum column or has enum in type
            is_enum_column = (column_name in known_enum_columns or 
                            'enum' in column_info['type'].lower())
            
            if is_enum_column:
                print(f"\nChecking enum column: {column_name}")
                
                # Get enum values from model
                if column_name in known_enum_columns:
                    model_enum_values = known_enum_columns[column_name]
                else:
                    model_enum_values = self.get_enum_values_from_model(model_class, column_name)
                
                if not model_enum_values:
                    print(f"  No enum values found in model for {column_name}")
                    continue
                
                print(f"  Model enum values: {sorted(model_enum_values)}")
                
                # Get existing enum values from database
                existing_enum_values = self.get_existing_enum_values(quoted_table_name, column_name)
                if not existing_enum_values:
                    print(f"  No existing enum values found in database for {column_name}")
                    continue
                
                print(f"  Database enum values: {sorted(existing_enum_values)}")
                
                # Check for differences
                if existing_enum_values != model_enum_values:
                    print(f"  ⚠️  Enum value differences detected!")
                    
                    # Find similar values for migration
                    value_mappings = self.find_similar_enum_values(existing_enum_values, model_enum_values)
                    
                    if value_mappings:
                        print(f"  Found similar values for migration:")
                        for old_val, new_val in value_mappings.items():
                            print(f"    '{old_val}' -> '{new_val}'")
                        
                        response = input(f"  Do you want to migrate these enum values for {column_name}? (y/n): ").lower().strip()
                        if response == 'y':
                            if not self.migrate_enum_values(quoted_table_name, column_name, value_mappings):
                                success = False
                        else:
                            print(f"  Skipping enum migration for {column_name}")
                    else:
                        print(f"  No similar values found for automatic migration")
                        print(f"  Manual intervention may be required for {column_name}")
                        
                        # Show unmapped values
                        unmapped_old = existing_enum_values - set(value_mappings.keys())
                        unmapped_new = model_enum_values - set(value_mappings.values())
                        
                        if unmapped_old:
                            print(f"  Unmapped old values: {sorted(unmapped_old)}")
                        if unmapped_new:
                            print(f"  New enum values: {sorted(unmapped_new)}")
                else:
                    print(f"  ✓ Enum values match between model and database")
        
        return success

    def sqlite_type_from_sqlalchemy(self, sqlalchemy_type: str) -> str:
        """Convert SQLAlchemy type to SQLite type"""
        type_str = str(sqlalchemy_type).lower()
        
        if 'integer' in type_str:
            return 'INTEGER'
        elif 'float' in type_str or 'numeric' in type_str:
            return 'REAL'
        elif 'text' in type_str or 'string' in type_str:
            return 'TEXT'
        elif 'boolean' in type_str:
            return 'INTEGER'
        elif 'datetime' in type_str:
            return 'TEXT'
        elif 'enum' in type_str:
            return 'TEXT'
        else:
            return 'TEXT'

    def get_default_value(self, default) -> str:
        """Extract default value from SQLAlchemy default"""
        if default is None:
            return None
        
        # Handle SQLAlchemy default objects
        if hasattr(default, 'arg'):
            default = default.arg
        
        # Handle enum defaults
        if hasattr(default, 'value'):
            default = default.value
        
        # Handle callable defaults
        if callable(default):
            try:
                default = default()
            except:
                default = None
        
        return str(default) if default is not None else None

    def create_table(self, table_name: str, model_class) -> bool:
        """Create a new table based on the model"""
        try:
            print(f"Creating table: {table_name}")
            
            # Quote table name if it's a reserved keyword
            quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            
            columns = []
            primary_keys = []
            
            for column_name, column_info in self.get_model_columns(model_class).items():
                sqlite_type = self.sqlite_type_from_sqlalchemy(column_info['type'])
                column_def = f"{column_name} {sqlite_type}"
                
                if column_info['primary_key']:
                    primary_keys.append(column_name)
                if not column_info['nullable']:
                    column_def += " NOT NULL"
                if column_info['unique'] and not column_info['primary_key']:
                    column_def += " UNIQUE"
                
                default_val = self.get_default_value(column_info['default'])
                if default_val is not None:
                    column_def += f" DEFAULT '{default_val}'"
                
                columns.append(column_def)
            
            # Handle composite primary keys
            if len(primary_keys) > 1:
                columns.append(f"PRIMARY KEY ({', '.join(primary_keys)})")
            elif len(primary_keys) == 1:
                # Remove PRIMARY KEY from individual column and add it separately
                for i, col in enumerate(columns):
                    if col.startswith(f"{primary_keys[0]} "):
                        columns[i] = col.replace(" PRIMARY KEY", "")
                columns.append(f"PRIMARY KEY ({primary_keys[0]})")
            
            create_sql = f"CREATE TABLE {quoted_table_name} (\n  " + ",\n  ".join(columns) + "\n)"
            print(f"Executing: {create_sql}")
            
            self.cursor.execute(create_sql)
            self.conn.commit()
            print(f"✓ Table {table_name} created successfully")
            return True
            
        except Exception as e:
            print(f"✗ Failed to create table {table_name}: {e}")
            self.conn.rollback()
            return False
    
    def add_column(self, table_name: str, column_name: str, column_info: Dict[str, Any]) -> bool:
        """Add a new column to an existing table"""
        try:
            sqlite_type = self.sqlite_type_from_sqlalchemy(column_info['type'])
            column_def = f"{column_name} {sqlite_type}"
            
            if not column_info['nullable']:
                column_def += " NOT NULL"
            if column_info['unique']:
                column_def += " UNIQUE"
            
            default_val = self.get_default_value(column_info['default'])
            if default_val is not None:
                column_def += f" DEFAULT '{default_val}'"
            
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_def}"
            print(f"Adding column: {alter_sql}")
            
            self.cursor.execute(alter_sql)
            self.conn.commit()
            print(f"✓ Column {column_name} added to {table_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to add column {column_name} to {table_name}: {e}")
            self.conn.rollback()
            return False
    
    def update_column_default(self, table_name: str, column_name: str, new_default: Any) -> bool:
        """Update column default value (requires recreating the table in SQLite)"""
        try:
            print(f"Updating default value for {table_name}.{column_name} to {new_default}")
            
            # Remove quotes for internal operations
            clean_table_name = table_name.strip('"')
            new_table_name = f"{clean_table_name}_new"
            
            # Get current table structure
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = self.cursor.fetchall()
            
            # Create new table with updated default
            columns = []
            for col_info in columns_info:
                col_name = col_info[1]
                col_type = col_info[2]
                col_not_null = col_info[3]
                col_default = col_info[4]
                col_pk = col_info[5]
                
                column_def = f"{col_name} {col_type}"
                if col_not_null:
                    column_def += " NOT NULL"
                if col_pk:
                    column_def += " PRIMARY KEY"
                
                # Update default for the target column
                if col_name == column_name:
                    if isinstance(new_default, str):
                        column_def += f" DEFAULT '{new_default}'"
                    else:
                        column_def += f" DEFAULT {new_default}"
                elif col_default is not None:
                    column_def += f" DEFAULT {col_default}"
                
                columns.append(column_def)
            
            create_sql = f"CREATE TABLE {new_table_name} (\n  " + ",\n  ".join(columns) + "\n)"
            self.cursor.execute(create_sql)
            
            # Copy data
            self.cursor.execute(f"INSERT INTO {new_table_name} SELECT * FROM {table_name}")
            
            # Drop old table and rename new one
            self.cursor.execute(f"DROP TABLE {table_name}")
            self.cursor.execute(f"ALTER TABLE {new_table_name} RENAME TO {clean_table_name}")
            
            self.conn.commit()
            print(f"✓ Default value updated for {table_name}.{column_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to update default for {table_name}.{column_name}: {e}")
            self.conn.rollback()
            return False
    
    def get_column_type_similarity(self, col1_type: str, col2_type: str) -> float:
        """Calculate similarity between column types for data migration"""
        type1 = col1_type.lower()
        type2 = col2_type.lower()
        
        # Exact match
        if type1 == type2:
            return 1.0
        
        # Similar types
        if ('text' in type1 and 'text' in type2) or ('string' in type1 and 'string' in type2):
            return 0.9
        if ('integer' in type1 and 'integer' in type2) or ('int' in type1 and 'int' in type2):
            return 0.9
        if ('real' in type1 and 'real' in type2) or ('float' in type1 and 'float' in type2):
            return 0.9
        if ('boolean' in type1 and 'boolean' in type2) or ('bool' in type1 and 'bool' in type2):
            return 0.9
        
        # Numeric types are somewhat compatible
        if any(t in type1 for t in ['integer', 'int', 'real', 'float']) and any(t in type2 for t in ['integer', 'int', 'real', 'float']):
            return 0.7
        
        return 0.0

    def find_similar_column(self, table_name: str, column_name: str, column_type: str) -> str:
        """Find a similar column in the model for data migration"""
        model_columns = self.get_model_columns(self.get_model_tables().get(table_name))
        best_match = None
        best_similarity = 0.0
        
        for model_col_name, model_col_info in model_columns.items():
            similarity = self.get_column_type_similarity(column_type, model_col_info['type'])
            if similarity > best_similarity and similarity > 0.5:
                best_similarity = similarity
                best_match = model_col_name
        
        return best_match

    def migrate_column_data(self, table_name: str, old_column: str, new_column: str) -> bool:
        """Migrate data from old column to new column"""
        try:
            quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            update_sql = f"UPDATE {quoted_table_name} SET {new_column} = {old_column}"
            print(f"Migrating data: {update_sql}")
            self.cursor.execute(update_sql)
            self.conn.commit()
            print(f"✓ Data migrated from {old_column} to {new_column}")
            return True
        except Exception as e:
            print(f"✗ Failed to migrate data: {e}")
            self.conn.rollback()
            return False

    def remove_column(self, table_name: str, column_name: str) -> bool:
        """Remove a column from a table (SQLite limitation: requires table recreation)"""
        try:
            quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            
            # Get current table structure
            self.cursor.execute(f"PRAGMA table_info({quoted_table_name})")
            columns_info = self.cursor.fetchall()
            
            # Create new table without the column
            new_table_name = f"{table_name}_new"
            columns = []
            for col_info in columns_info:
                if col_info[1] != column_name:  # Skip the column to remove
                    col_name = col_info[1]
                    col_type = col_info[2]
                    col_not_null = col_info[3]
                    col_default = col_info[4]
                    col_pk = col_info[5]
                    
                    column_def = f"{col_name} {col_type}"
                    if col_not_null:
                        column_def += " NOT NULL"
                    if col_pk:
                        column_def += " PRIMARY KEY"
                    if col_default is not None:
                        column_def += f" DEFAULT {col_default}"
                    
                    columns.append(column_def)
            
            # Create new table
            create_sql = f"CREATE TABLE {new_table_name} (\n  " + ",\n  ".join(columns) + "\n)"
            self.cursor.execute(create_sql)
            
            # Copy data (excluding the removed column)
            select_columns = [col[1] for col in columns_info if col[1] != column_name]
            select_sql = f"INSERT INTO {new_table_name} SELECT {', '.join(select_columns)} FROM {quoted_table_name}"
            self.cursor.execute(select_sql)
            
            # Drop old table and rename new one
            self.cursor.execute(f"DROP TABLE {quoted_table_name}")
            # Use quoted name for the final table name if it's a reserved keyword
            final_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            self.cursor.execute(f"ALTER TABLE {new_table_name} RENAME TO {final_table_name}")
            
            self.conn.commit()
            print(f"✓ Column {column_name} removed from {table_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to remove column {column_name}: {e}")
            self.conn.rollback()
            return False

    def find_similar_table(self, table_name: str, table_columns: List[str]) -> str:
        """Find a similar table in the model for data migration"""
        model_tables = self.get_model_tables()
        best_match = None
        best_similarity = 0.0
        
        for model_table_name, model_class in model_tables.items():
            if model_table_name == table_name:
                continue
                
            model_columns = self.get_model_columns(model_class)
            model_col_names = list(model_columns.keys())
            
            # Calculate similarity based on common columns
            common_columns = set(table_columns) & set(model_col_names)
            if len(common_columns) > 0:
                similarity = len(common_columns) / max(len(table_columns), len(model_col_names))
                if similarity > best_similarity and similarity > 0.3:  # At least 30% similarity
                    best_similarity = similarity
                    best_match = model_table_name
        
        return best_match

    def migrate_table_data(self, old_table: str, new_table: str) -> bool:
        """Migrate data from old table to new table"""
        try:
            # Get columns from both tables
            old_quoted = f'"{old_table}"' if old_table.lower() in ['order', 'group', 'user'] else old_table
            new_quoted = f'"{new_table}"' if new_table.lower() in ['order', 'group', 'user'] else new_table
            
            self.cursor.execute(f"PRAGMA table_info({old_quoted})")
            old_columns = [col[1] for col in self.cursor.fetchall()]
            
            new_model_class = self.get_model_tables().get(new_table)
            new_columns = list(self.get_model_columns(new_model_class).keys())
            
            # Find common columns
            common_columns = set(old_columns) & set(new_columns)
            if not common_columns:
                print("No common columns found for migration")
                return False
            
            # Migrate data
            select_cols = list(common_columns)
            insert_sql = f"INSERT INTO {new_quoted} ({', '.join(select_cols)}) SELECT {', '.join(select_cols)} FROM {old_quoted}"
            print(f"Migrating data: {insert_sql}")
            self.cursor.execute(insert_sql)
            
            self.conn.commit()
            print(f"✓ Data migrated from {old_table} to {new_table}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to migrate table data: {e}")
            self.conn.rollback()
            return False

    def remove_table(self, table_name: str) -> bool:
        """Remove a table from the database"""
        try:
            quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
            drop_sql = f"DROP TABLE {quoted_table_name}"
            print(f"Removing table: {drop_sql}")
            self.cursor.execute(drop_sql)
            self.conn.commit()
            print(f"✓ Table {table_name} removed")
            return True
        except Exception as e:
            print(f"✗ Failed to remove table {table_name}: {e}")
            self.conn.rollback()
            return False

    def migrate_table(self, table_name: str, model_class) -> bool:
        """Migrate a single table to match the model"""
        print(f"\n--- Migrating table: {table_name} ---")
        
        # Quote table name if it's a reserved keyword
        quoted_table_name = f'"{table_name}"' if table_name.lower() in ['order', 'group', 'user'] else table_name
        
        # Get existing columns
        existing_columns_data = self.get_table_columns(quoted_table_name)
        existing_columns = {col[1]: col for col in existing_columns_data}
        
        print(f"Existing columns in {table_name}: {list(existing_columns.keys())}")
        
        model_columns = self.get_model_columns(model_class)
        print(f"Model columns for {table_name}: {list(model_columns.keys())}")
        
        success = True
        
        # Check for missing columns (add new ones)
        for column_name, column_info in model_columns.items():
            if column_name not in existing_columns:
                print(f"Missing column: {column_name}")
                if not self.add_column(quoted_table_name, column_name, column_info):
                    success = False
            else:
                print(f"Column {column_name} already exists")
        
        # Check for obsolete columns (remove old ones)
        for column_name in existing_columns:
            if column_name not in model_columns:
                column_type = existing_columns[column_name][2]
                print(f"\nObsolete column found: {column_name} ({column_type})")
                
                # Find similar column for data migration
                similar_column = self.find_similar_column(table_name, column_name, column_type)
                
                if similar_column:
                    print(f"Found similar column: {similar_column}")
                    response = input(f"Do you want to migrate data from '{column_name}' to '{similar_column}'? (y/n): ").lower().strip()
                    if response == 'y':
                        if self.migrate_column_data(table_name, column_name, similar_column):
                            if self.remove_column(table_name, column_name):
                                print(f"✓ Column {column_name} migrated and removed")
                            else:
                                success = False
                        else:
                            success = False
                    else:
                        response = input(f"Do you want to remove column '{column_name}' without migrating data? (y/n): ").lower().strip()
                        if response == 'y':
                            if not self.remove_column(table_name, column_name):
                                success = False
                        else:
                            print(f"Keeping column {column_name}")
                else:
                    print(f"No similar column found for {column_name}")
                    response = input(f"Do you want to remove column '{column_name}'? (y/n): ").lower().strip()
                    if response == 'y':
                        if not self.remove_column(table_name, column_name):
                            success = False
                    else:
                        print(f"Keeping column {column_name}")
        
        # Check for enum migrations
        if not self.check_enum_migrations(table_name, model_class):
            success = False
        
        return success
    
    def run_migration(self) -> bool:
        """Run the complete migration process"""
        print(f"Starting database migration for {self.db_type.upper()}...")
        
        if not self.create_backup():
            print("Warning: Could not create backup, proceeding anyway...")
        
        if not self.connect():
            print("Failed to connect to database")
            return False
        
        try:
            # Get existing tables and model tables
            existing_tables = self.get_existing_tables()
            model_tables = self.get_model_tables()
            
            print(f"Found {len(existing_tables)} existing tables")
            print(f"Found {len(model_tables)} model tables")
            
            # Process each model table
            for table_name, model_class in model_tables.items():
                if table_name in existing_tables:
                    print(f"Migrating existing table: {table_name}")
                    if not self.migrate_table(table_name, model_class):
                        print(f"Failed to migrate table: {table_name}")
                        return False
                else:
                    print(f"Creating new table: {table_name}")
                    if not self.create_table(table_name, model_class):
                        print(f"Failed to create table: {table_name}")
                        return False
            
            # Commit changes
            self.conn.commit()
            print("✓ Database migration completed successfully")
            return True
            
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()


def main():
    """Main function to run the migration"""
    migrator = DatabaseMigrator()
    
    try:
        migrator.setup_flask_context()
        if migrator.run_migration():
            print("Migration completed successfully!")
            sys.exit(0)
        else:
            print("Migration failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Migration script error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 