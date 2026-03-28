import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from database_config import db_config
from user_db import user_db

def init_db():
    """Initialize database tables."""
    
    # Initialize user tables first
    user_db.init_user_tables()
    
    # Create APIs table with user_id
    apis_table_sql = '''
        CREATE TABLE IF NOT EXISTS apis (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            base_url TEXT NOT NULL,
            description TEXT,
            date_added TIMESTAMP NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''' if db_config.is_postgres else '''
        CREATE TABLE IF NOT EXISTS apis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            description TEXT,
            date_added TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    '''
    
    # Create schema_snapshots table (user_id will be through apis relation)
    snapshots_table_sql = '''
        CREATE TABLE IF NOT EXISTS schema_snapshots (
            id SERIAL PRIMARY KEY,
            api_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            schema_json JSONB NOT NULL,
            schema_pdf TEXT,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
        )
    ''' if db_config.is_postgres else '''
        CREATE TABLE IF NOT EXISTS schema_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            schema_json TEXT NOT NULL,
            schema_pdf TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
        )
    '''
    
    # Execute table creation
    db_config.execute_query(apis_table_sql, fetch='rowcount')
    db_config.execute_query(snapshots_table_sql, fetch='rowcount')
    
    # Add user_id column to existing apis table if it doesn't exist
    try:
        if db_config.is_postgres:
            db_config.execute_query('ALTER TABLE apis ADD COLUMN IF NOT EXISTS user_id INTEGER NOT NULL DEFAULT 1', fetch='rowcount')
        else:
            # Check if column exists first for SQLite
            check_column = "PRAGMA table_info(apis)"
            columns = db_config.execute_query(check_column, (), 'all')
            has_user_id = any(col['name'] == 'user_id' for col in columns)
            
            if not has_user_id:
                db_config.execute_query('ALTER TABLE apis ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1', fetch='rowcount')
    except Exception as e:
        print(f"Note: user_id column may already exist or migration not needed: {e}")
    
    # Create indexes for better performance
    if db_config.is_postgres:
        db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_apis_base_url ON apis(base_url)', fetch='rowcount')
        db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_apis_user_id ON apis(user_id)', fetch='rowcount')
        db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_schema_snapshots_api_id ON schema_snapshots(api_id)', fetch='rowcount')
        db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_schema_snapshots_version ON schema_snapshots(api_id, version_number)', fetch='rowcount')
    
    # Create default admin user if not exists
    create_default_admin_user()

def create_default_admin_user():
    """Create default admin user if it doesn't exist."""
    try:
        # Check if admin user exists
        existing_admin = user_db.get_user_by_username('admin')
        if not existing_admin:
            from user_models import UserCreate
            from auth import auth_service
            
            # Create admin user with hashed password
            admin_data = UserCreate(
                username='admin',
                email='admin@apisec.local',
                password='admin'
            )
            user_db.create_user(admin_data)
            print("Default admin user created (username: admin, password: admin)")
    except Exception as e:
        print(f"Error creating default admin user: {e}")

class ApiRegistry:
    @staticmethod
    def create(name: str, base_url: str, description: Optional[str] = None, user_id: int = 1) -> Dict[str, Any]:
        date_added = datetime.now().isoformat()
        
        if db_config.is_postgres:
            query = '''
                INSERT INTO apis (name, base_url, description, date_added, user_id) 
                VALUES (%s, %s, %s, %s, %s) 
                RETURNING id
            '''
            result = db_config.execute_query(query, (name, base_url, description, date_added, user_id), 'one')
            api_id = result['id']
        else:
            query = '''
                INSERT INTO apis (name, base_url, description, date_added, user_id) 
                VALUES (?, ?, ?, ?, ?)
            '''
            db_config.execute_query(query, (name, base_url, description, date_added, user_id))
            # Get last inserted row ID for SQLite
            result = db_config.execute_query('SELECT last_insert_rowid() as id', (), 'one')
            api_id = result['id']
        
        return {
            'id': api_id,
            'name': name,
            'base_url': base_url,
            'description': description,
            'date_added': date_added,
            'user_id': user_id
        }
    
    @staticmethod
    def get_all(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if user_id:
            query = 'SELECT * FROM apis WHERE user_id = %s ORDER BY id DESC' if db_config.is_postgres else 'SELECT * FROM apis WHERE user_id = ? ORDER BY id DESC'
            return db_config.execute_query(query, (user_id,), 'all')
        else:
            query = 'SELECT * FROM apis ORDER BY id DESC'
            return db_config.execute_query(query, (), 'all')
    
    @staticmethod
    def get_by_url(base_url: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if user_id:
            query = 'SELECT * FROM apis WHERE base_url = %s AND user_id = %s' if db_config.is_postgres else 'SELECT * FROM apis WHERE base_url = ? AND user_id = ?'
            return db_config.execute_query(query, (base_url, user_id), 'one')
        else:
            query = 'SELECT * FROM apis WHERE base_url = %s' if db_config.is_postgres else 'SELECT * FROM apis WHERE base_url = ?'
            return db_config.execute_query(query, (base_url,), 'one')
    
    @staticmethod
    def get_by_id(api_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if user_id:
            query = 'SELECT * FROM apis WHERE id = %s AND user_id = %s' if db_config.is_postgres else 'SELECT * FROM apis WHERE id = ? AND user_id = ?'
            return db_config.execute_query(query, (api_id, user_id), 'one')
        else:
            query = 'SELECT * FROM apis WHERE id = %s' if db_config.is_postgres else 'SELECT * FROM apis WHERE id = ?'
            return db_config.execute_query(query, (api_id,), 'one')
    
    @staticmethod
    def update(api_id: int, name: str, base_url: str, description: Optional[str]) -> bool:
        query = '''
            UPDATE apis SET name = %s, base_url = %s, description = %s 
            WHERE id = %s
        ''' if db_config.is_postgres else '''
            UPDATE apis SET name = ?, base_url = ?, description = ? 
            WHERE id = ?
        '''
        rows_affected = db_config.execute_query(query, (name, base_url, description, api_id), 'rowcount')
        return rows_affected > 0
    
    @staticmethod
    def delete(api_id: int) -> bool:
        query = 'DELETE FROM apis WHERE id = %s' if db_config.is_postgres else 'DELETE FROM apis WHERE id = ?'
        rows_affected = db_config.execute_query(query, (api_id,), 'rowcount')
        return rows_affected > 0


class SchemaSnapshot:
    @staticmethod
    def create(api_id: int, schema_json: Dict[str, Any], schema_pdf: Optional[str] = None) -> Dict[str, Any]:
        # Get next version number
        version_query = '''
            SELECT COALESCE(MAX(version_number), 0) + 1 as next_version 
            FROM schema_snapshots WHERE api_id = %s
        ''' if db_config.is_postgres else '''
            SELECT COALESCE(MAX(version_number), 0) + 1 as next_version 
            FROM schema_snapshots WHERE api_id = ?
        '''
        result = db_config.execute_query(version_query, (api_id,), 'one')
        version_number = result['next_version']
        
        timestamp = datetime.now().isoformat()
        
        if db_config.is_postgres:
            # PostgreSQL can store JSON directly but needs proper handling
            query = '''
                INSERT INTO schema_snapshots (api_id, version_number, schema_json, schema_pdf, timestamp) 
                VALUES (%s, %s, %s::jsonb, %s, %s) 
                RETURNING id
            '''
            result = db_config.execute_query(query, (api_id, version_number, json.dumps(schema_json), schema_pdf, timestamp), 'one')
            snapshot_id = result['id']
        else:
            # SQLite needs JSON as string
            schema_json_str = json.dumps(schema_json)
            query = '''
                INSERT INTO schema_snapshots (api_id, version_number, schema_json, schema_pdf, timestamp) 
                VALUES (?, ?, ?, ?, ?)
            '''
            db_config.execute_query(query, (api_id, version_number, schema_json_str, schema_pdf, timestamp))
            result = db_config.execute_query('SELECT last_insert_rowid() as id', (), 'one')
            snapshot_id = result['id']
        
        return {
            'id': snapshot_id,
            'api_id': api_id,
            'version_number': version_number,
            'schema_json': schema_json,
            'schema_pdf': schema_pdf,
            'timestamp': timestamp
        }
    
    @staticmethod
    def schema_exists(api_id: int, schema_json: Dict[str, Any]) -> bool:
        if db_config.is_postgres:
            query = '''
                SELECT COUNT(*) as count FROM schema_snapshots 
                WHERE api_id = %s AND schema_json::jsonb = %s::jsonb
            '''
            result = db_config.execute_query(query, (api_id, schema_json), 'one')
        else:
            schema_json_str = json.dumps(schema_json)
            query = '''
                SELECT COUNT(*) as count FROM schema_snapshots 
                WHERE api_id = ? AND schema_json = ?
            '''
            result = db_config.execute_query(query, (api_id, schema_json_str), 'one')
        
        return result['count'] > 0
    
    @staticmethod
    def create_if_different(api_id: int, schema_json: Dict[str, Any], schema_pdf: Optional[str] = None) -> Dict[str, Any]:
        # Check if schema already exists
        if SchemaSnapshot.schema_exists(api_id, schema_json):
            return {
                'status': 'unchanged',
                'message': 'Schema has not changed',
                'schema': SchemaSnapshot.get_latest(api_id)
            }
        
        # Create new schema if different
        return SchemaSnapshot.create(api_id, schema_json, schema_pdf)
    
    @staticmethod
    def update_pdf(snapshot_id: int, schema_pdf: str) -> bool:
        query = '''
            UPDATE schema_snapshots SET schema_pdf = %s 
            WHERE id = %s
        ''' if db_config.is_postgres else '''
            UPDATE schema_snapshots SET schema_pdf = ? 
            WHERE id = ?
        '''
        rows_affected = db_config.execute_query(query, (schema_pdf, snapshot_id), 'rowcount')
        return rows_affected > 0
    
    @staticmethod
    def get_by_api(api_id: int) -> List[Dict[str, Any]]:
        query = '''
            SELECT * FROM schema_snapshots 
            WHERE api_id = %s ORDER BY version_number DESC
        ''' if db_config.is_postgres else '''
            SELECT * FROM schema_snapshots 
            WHERE api_id = ? ORDER BY version_number DESC
        '''
        rows = db_config.execute_query(query, (api_id,), 'all')
        
        results = []
        for row in rows:
            if db_config.is_postgres:
                # PostgreSQL already returns JSON as dict
                results.append(row)
            else:
                # SQLite needs JSON parsing
                row['schema_json'] = json.loads(row['schema_json'])
                results.append(row)
        
        return results
    
    @staticmethod
    def get_latest(api_id: int) -> Optional[Dict[str, Any]]:
        query = '''
            SELECT * FROM schema_snapshots 
            WHERE api_id = %s ORDER BY version_number DESC LIMIT 1
        ''' if db_config.is_postgres else '''
            SELECT * FROM schema_snapshots 
            WHERE api_id = ? ORDER BY version_number DESC LIMIT 1
        '''
        row = db_config.execute_query(query, (api_id,), 'one')
        
        if not row:
            return None
        
        if not db_config.is_postgres:
            # SQLite needs JSON parsing
            row['schema_json'] = json.loads(row['schema_json'])
        
        return row
    
    @staticmethod
    def get_by_version(api_id: int, version_number: int) -> Optional[Dict[str, Any]]:
        query = '''
            SELECT * FROM schema_snapshots 
            WHERE api_id = %s AND version_number = %s
        ''' if db_config.is_postgres else '''
            SELECT * FROM schema_snapshots 
            WHERE api_id = ? AND version_number = ?
        '''
        row = db_config.execute_query(query, (api_id, version_number), 'one')
        
        if not row:
            return None
        
        if not db_config.is_postgres:
            # SQLite needs JSON parsing
            row['schema_json'] = json.loads(row['schema_json'])
        
        return row
