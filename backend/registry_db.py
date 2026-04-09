import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_db():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", "postgres"),
            dbname=os.environ.get("DB_NAME", "postgres")
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to Postgres: {e}")
        raise e

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apis (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            description TEXT,
            date_added TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_snapshots (
            id SERIAL PRIMARY KEY,
            api_id INTEGER NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL,
            schema_json TEXT NOT NULL,
            schema_pdf TEXT,
            schema_url TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            api_id INTEGER REFERENCES apis(id) ON DELETE SET NULL,
            type VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            format VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    
    # Migration: add schema_url column to existing databases
    cursor.execute('''
        ALTER TABLE schema_snapshots
        ADD COLUMN IF NOT EXISTS schema_url TEXT
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

class UserRegistry:
    @staticmethod
    def create(username: str, password_hash: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        created_at = datetime.now().isoformat()
        
        try:
            cursor.execute(
                'INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s) RETURNING id',
                (username, password_hash, created_at)
            )
            user_id = cursor.fetchone()['id']
            conn.commit()
            return {
                'id': user_id,
                'username': username,
                'created_at': created_at
            }
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_username(username: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None
        
    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT id, username, created_at FROM users WHERE id = %s', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return dict(row) if row else None

class ApiRegistry:
    @staticmethod
    def create(user_id: int, name: str, base_url: str, description: Optional[str] = None) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        date_added = datetime.now().isoformat()
        
        cursor.execute(
            'INSERT INTO apis (user_id, name, base_url, description, date_added) VALUES (%s, %s, %s, %s, %s) RETURNING id',
            (user_id, name, base_url, description, date_added)
        )
        api_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'id': api_id,
            'user_id': user_id,
            'name': name,
            'base_url': base_url,
            'description': description,
            'date_added': date_added
        }
    
    @staticmethod
    def get_all(user_id: int) -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM apis WHERE user_id = %s ORDER BY id DESC', (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_url(user_id: int, base_url: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM apis WHERE user_id = %s AND base_url = %s', (user_id, base_url))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return dict(row) if row else None
    
    @staticmethod
    def get_by_id(user_id: int, api_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM apis WHERE id = %s AND user_id = %s', (api_id, user_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return dict(row) if row else None
    
    @staticmethod
    def update(user_id: int, api_id: int, name: str, base_url: str, description: Optional[str]) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE apis SET name = %s, base_url = %s, description = %s WHERE id = %s AND user_id = %s',
            (name, base_url, description, api_id, user_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        return updated
    
    @staticmethod
    def delete(user_id: int, api_id: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM apis WHERE id = %s AND user_id = %s', (api_id, user_id))
        deleted = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        return deleted


class SchemaSnapshot:
    @staticmethod
    def create(api_id: int, schema_json: Dict[str, Any], schema_pdf: Optional[str] = None, schema_url: Optional[str] = None) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            'SELECT COALESCE(MAX(version_number), 0) + 1 AS ver FROM schema_snapshots WHERE api_id = %s',
            (api_id,)
        )
        version_number = cursor.fetchone()['ver']
        
        timestamp = datetime.now().isoformat()
        schema_json_str = json.dumps(schema_json)
        
        cursor.execute(
            'INSERT INTO schema_snapshots (api_id, version_number, schema_json, schema_pdf, schema_url, timestamp) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id',
            (api_id, version_number, schema_json_str, schema_pdf, schema_url, timestamp)
        )
        snapshot_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'id': snapshot_id,
            'api_id': api_id,
            'version_number': version_number,
            'schema_json': schema_json,
            'schema_pdf': schema_pdf,
            'schema_url': schema_url,
            'timestamp': timestamp
        }
    
    @staticmethod
    def schema_exists(api_id: int, schema_json: Dict[str, Any], schema_url: Optional[str] = None) -> bool:
        """Check if this exact schema content (or schema_url) already exists for this API."""
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # If a URL is provided, check by URL first (faster and avoids large JSON comparisons)
        if schema_url:
            cursor.execute(
                'SELECT COUNT(*) as cnt FROM schema_snapshots WHERE api_id = %s AND schema_url = %s',
                (api_id, schema_url)
            )
            count = cursor.fetchone()['cnt']
            if count > 0:
                cursor.close()
                conn.close()
                return True
        
        schema_json_str = json.dumps(schema_json)
        cursor.execute(
            'SELECT COUNT(*) as cnt FROM schema_snapshots WHERE api_id = %s AND schema_json = %s',
            (api_id, schema_json_str)
        )
        count = cursor.fetchone()['cnt']
        cursor.close()
        conn.close()
        
        return count > 0
    
    @staticmethod
    def create_if_different(api_id: int, schema_json: Dict[str, Any], schema_pdf: Optional[str] = None, schema_url: Optional[str] = None) -> Dict[str, Any]:
        # Check if schema already exists (by URL or content)
        if SchemaSnapshot.schema_exists(api_id, schema_json, schema_url):
            return {
                'status': 'unchanged',
                'message': 'Schema has not changed',
                'schema': SchemaSnapshot.get_latest(api_id)
            }
        
        # Create new schema if different
        return SchemaSnapshot.create(api_id, schema_json, schema_pdf, schema_url)
    
    @staticmethod
    def update_pdf(snapshot_id: int, schema_pdf: str) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE schema_snapshots SET schema_pdf = %s WHERE id = %s',
            (schema_pdf, snapshot_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        return updated
    
    @staticmethod
    def get_by_api(api_id: int) -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT * FROM schema_snapshots WHERE api_id = %s ORDER BY version_number DESC',
            (api_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        results = []
        for row in rows:
            result = dict(row)
            result['schema_json'] = json.loads(result['schema_json'])
            results.append(result)
        
        return results
    
    @staticmethod
    def get_latest(api_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT * FROM schema_snapshots WHERE api_id = %s ORDER BY version_number DESC LIMIT 1',
            (api_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        result['schema_json'] = json.loads(result['schema_json'])
        return result
    
    @staticmethod
    def get_by_version(api_id: int, version_number: int) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            'SELECT * FROM schema_snapshots WHERE api_id = %s AND version_number = %s',
            (api_id, version_number)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        result['schema_json'] = json.loads(result['schema_json'])
        return result

class ReportRegistry:
    @staticmethod
    def create(user_id: int, api_id: Optional[int], type: str, name: str, content: str, format: str) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        created_at = datetime.now().isoformat()
        
        cursor.execute(
            'INSERT INTO reports (user_id, api_id, type, name, content, format, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id',
            (user_id, api_id, type, name, content, format, created_at)
        )
        report_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            'id': report_id,
            'user_id': user_id,
            'api_id': api_id,
            'type': type,
            'name': name,
            'content': content,
            'format': format,
            'created_at': created_at
        }
    
    @staticmethod
    def get_all(user_id: int) -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM reports WHERE user_id = %s ORDER BY id DESC', (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def delete(user_id: int, report_id: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reports WHERE id = %s AND user_id = %s', (report_id, user_id))
        deleted = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        return deleted
