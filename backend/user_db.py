from typing import List, Dict, Any, Optional
from datetime import datetime
from database_config import db_config
from auth import auth_service
from user_models import UserCreate, UserResponse

class UserDB:
    """Database operations for user management."""
    
    @staticmethod
    def init_user_tables():
        """Initialize user-related database tables."""
        
        # Create users table
        users_table_sql = '''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT,
                oauth_provider VARCHAR(50),
                oauth_id VARCHAR(255),
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        ''' if db_config.is_postgres else '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                oauth_provider TEXT,
                oauth_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        '''
        
        # Create user_sessions table for token management
        sessions_table_sql = '''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''' if db_config.is_postgres else '''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        '''
        
        # Execute table creation
        db_config.execute_query(users_table_sql, fetch='rowcount')
        db_config.execute_query(sessions_table_sql, fetch='rowcount')
        
        # Create indexes
        if db_config.is_postgres:
            db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)', fetch='rowcount')
            db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id)', fetch='rowcount')
            db_config.execute_query('CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)', fetch='rowcount')
    
    @staticmethod
    def create_user(user_data: UserCreate) -> Dict[str, Any]:
        """Create a new user."""
        now = datetime.now().isoformat()
        
        # Hash password if provided
        password_hash = None
        if user_data.password:
            password_hash = auth_service.hash_password(user_data.password)
        
        if db_config.is_postgres:
            query = '''
                INSERT INTO users (username, email, password_hash, oauth_provider, oauth_id, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s) 
                RETURNING id
            '''
            result = db_config.execute_query(
                query, 
                (user_data.username, user_data.email, password_hash, user_data.oauth_provider, user_data.oauth_id, now, now), 
                'one'
            )
            user_id = result['id']
        else:
            query = '''
                INSERT INTO users (username, email, password_hash, oauth_provider, oauth_id, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            '''
            db_config.execute_query(
                query, 
                (user_data.username, user_data.email, password_hash, user_data.oauth_provider, user_data.oauth_id, now, now)
            )
            result = db_config.execute_query('SELECT last_insert_rowid() as id', (), 'one')
            user_id = result['id']
        
        return {
            'id': user_id,
            'username': user_data.username,
            'email': user_data.email,
            'oauth_provider': user_data.oauth_provider,
            'oauth_id': user_data.oauth_id,
            'created_at': now
        }
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        query = 'SELECT * FROM users WHERE email = %s' if db_config.is_postgres else 'SELECT * FROM users WHERE email = ?'
        return db_config.execute_query(query, (email,), 'one')
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        query = 'SELECT * FROM users WHERE username = %s' if db_config.is_postgres else 'SELECT * FROM users WHERE username = ?'
        return db_config.execute_query(query, (username,), 'one')
    
    @staticmethod
    def get_user_by_oauth(provider: str, oauth_id: str) -> Optional[Dict[str, Any]]:
        """Get user by OAuth provider and ID."""
        query = '''
            SELECT * FROM users WHERE oauth_provider = %s AND oauth_id = %s
        ''' if db_config.is_postgres else '''
            SELECT * FROM users WHERE oauth_provider = ? AND oauth_id = ?
        '''
        return db_config.execute_query(query, (provider, oauth_id), 'one')
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        query = 'SELECT * FROM users WHERE id = %s' if db_config.is_postgres else 'SELECT * FROM users WHERE id = ?'
        return db_config.execute_query(query, (user_id,), 'one')
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """Update user information."""
        if not kwargs:
            return False
        
        kwargs['updated_at'] = datetime.now().isoformat()
        
        set_clause = ', '.join([f"{key} = %s" if db_config.is_postgres else f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        
        query = f'UPDATE users SET {set_clause} WHERE id = %s' if db_config.is_postgres else f'UPDATE users SET {set_clause} WHERE id = ?'
        rows_affected = db_config.execute_query(query, tuple(values), 'rowcount')
        return rows_affected > 0
    
    @staticmethod
    def create_or_update_oauth_user(user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user from OAuth information."""
        # Check if user exists
        existing_user = UserDB.get_user_by_oauth(user_info['provider'], user_info['id'])
        
        if existing_user:
            # Update existing user
            UserDB.update_user(
                existing_user['id'],
                username=user_info.get('username'),
                email=user_info['email']
            )
            return UserDB.get_user_by_id(existing_user['id'])
        else:
            # Create new user
            user_data = UserCreate(
                username=user_info.get('username') or user_info['email'].split('@')[0],
                email=user_info['email'],
                oauth_provider=user_info['provider'],
                oauth_id=user_info['id']
            )
            return UserDB.create_user(user_data)

user_db = UserDB()
