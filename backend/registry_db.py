import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DATABASE_PATH = "apisec.db"

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL,
            description TEXT,
            date_added TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_id INTEGER NOT NULL,
            version_number INTEGER NOT NULL,
            schema_json TEXT NOT NULL,
            schema_pdf TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (api_id) REFERENCES apis(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

class ApiRegistry:
    @staticmethod
    def create(name: str, base_url: str, description: Optional[str] = None) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor()
        date_added = datetime.now().isoformat()
        
        cursor.execute(
            'INSERT INTO apis (name, base_url, description, date_added) VALUES (?, ?, ?, ?)',
            (name, base_url, description, date_added)
        )
        api_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            'id': api_id,
            'name': name,
            'base_url': base_url,
            'description': description,
            'date_added': date_added
        }
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM apis ORDER BY id DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_url(base_url: str) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM apis WHERE base_url = ?', (base_url,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    @staticmethod
    def get_by_id(api_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM apis WHERE id = ?', (api_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    @staticmethod
    def update(api_id: int, name: str, base_url: str, description: Optional[str]) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE apis SET name = ?, base_url = ?, description = ? WHERE id = ?',
            (name, base_url, description, api_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    @staticmethod
    def delete(api_id: int) -> bool:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM apis WHERE id = ?', (api_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


class SchemaSnapshot:
    @staticmethod
    def create(api_id: int, schema_json: Dict[str, Any], schema_pdf: Optional[str] = None) -> Dict[str, Any]:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT COALESCE(MAX(version_number), 0) + 1 FROM schema_snapshots WHERE api_id = ?',
            (api_id,)
        )
        version_number = cursor.fetchone()[0]
        
        timestamp = datetime.now().isoformat()
        schema_json_str = json.dumps(schema_json)
        
        cursor.execute(
            'INSERT INTO schema_snapshots (api_id, version_number, schema_json, schema_pdf, timestamp) VALUES (?, ?, ?, ?, ?)',
            (api_id, version_number, schema_json_str, schema_pdf, timestamp)
        )
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
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
        conn = get_db()
        cursor = conn.cursor()
        
        schema_json_str = json.dumps(schema_json)
        cursor.execute(
            'SELECT COUNT(*) FROM schema_snapshots WHERE api_id = ? AND schema_json = ?',
            (api_id, schema_json_str)
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
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
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE schema_snapshots SET schema_pdf = ? WHERE id = ?',
            (schema_pdf, snapshot_id)
        )
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    @staticmethod
    def get_by_api(api_id: int) -> List[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM schema_snapshots WHERE api_id = ? ORDER BY version_number DESC',
            (api_id,)
        )
        rows = cursor.fetchall()
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
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM schema_snapshots WHERE api_id = ? ORDER BY version_number DESC LIMIT 1',
            (api_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        result['schema_json'] = json.loads(result['schema_json'])
        return result
    
    @staticmethod
    def get_by_version(api_id: int, version_number: int) -> Optional[Dict[str, Any]]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM schema_snapshots WHERE api_id = ? AND version_number = ?',
            (api_id, version_number)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        result = dict(row)
        result['schema_json'] = json.loads(result['schema_json'])
        return result
