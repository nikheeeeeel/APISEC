#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to PostgreSQL.
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def get_sqlite_connection():
    """Get SQLite connection."""
    sqlite_path = os.path.join(os.path.dirname(__file__), 'backend', 'apisec.db')
    return sqlite3.connect(sqlite_path)

def get_postgres_connection():
    """Get PostgreSQL connection."""
    database_url = os.getenv('DATABASE_URL', 'postgresql://apisec_user:apisec_password@localhost:5432/apisec')
    return psycopg2.connect(database_url)

def migrate_apis(pg_conn):
    """Migrate APIs table from SQLite to PostgreSQL."""
    print("Migrating APIs...")
    
    sqlite_conn = get_sqlite_connection()
    sqlite_conn.row_factory = sqlite3.Row
    
    try:
        # Get all APIs from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM apis")
        apis = sqlite_cursor.fetchall()
        
        pg_cursor = pg_conn.cursor()
        
        # Disable auto-increment temporarily to preserve IDs
        pg_cursor.execute("ALTER TABLE apis ALTER COLUMN id DROP DEFAULT")
        pg_cursor.execute("ALTER TABLE apis DROP CONSTRAINT apis_pkey CASCADE")
        
        for api in apis:
            api_dict = dict(api)
            pg_cursor.execute("""
                INSERT INTO apis (id, name, base_url, description, date_added) 
                VALUES (%s, %s, %s, %s, %s)
            """, (
                api_dict['id'],
                api_dict['name'],
                api_dict['base_url'],
                api_dict['description'],
                api_dict['date_added']
            ))
        
        # Restore primary key and sequence
        pg_cursor.execute("ALTER TABLE apis ADD CONSTRAINT apis_pkey PRIMARY KEY (id)")
        pg_cursor.execute("CREATE SEQUENCE IF NOT EXISTS apis_id_seq OWNED BY apis.id")
        pg_cursor.execute("SELECT setval('apis_id_seq', (SELECT MAX(id) FROM apis))")
        pg_cursor.execute("ALTER TABLE apis ALTER COLUMN id SET DEFAULT nextval('apis_id_seq')")
        
        pg_conn.commit()
        print(f"Migrated {len(apis)} APIs")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Error migrating APIs: {e}")
        raise
    finally:
        sqlite_conn.close()

def migrate_schema_snapshots(pg_conn):
    """Migrate schema_snapshots table from SQLite to PostgreSQL."""
    print("Migrating schema snapshots...")
    
    sqlite_conn = get_sqlite_connection()
    sqlite_conn.row_factory = sqlite3.Row
    
    try:
        # Get all schema snapshots from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM schema_snapshots")
        snapshots = sqlite_cursor.fetchall()
        
        pg_cursor = pg_conn.cursor()
        
        # Disable auto-increment temporarily to preserve IDs
        pg_cursor.execute("ALTER TABLE schema_snapshots ALTER COLUMN id DROP DEFAULT")
        pg_cursor.execute("ALTER TABLE schema_snapshots DROP CONSTRAINT schema_snapshots_pkey CASCADE")
        
        for snapshot in snapshots:
            snapshot_dict = dict(snapshot)
            
            # Parse JSON from SQLite
            schema_json = json.loads(snapshot_dict['schema_json'])
            
            # Convert dict to JSON string for PostgreSQL
            schema_json_str = json.dumps(schema_json)
            
            pg_cursor.execute("""
                INSERT INTO schema_snapshots (id, api_id, version_number, schema_json, schema_pdf, timestamp) 
                VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            """, (
                snapshot_dict['id'],
                snapshot_dict['api_id'],
                snapshot_dict['version_number'],
                schema_json_str,  # Pass as JSON string, cast to jsonb
                snapshot_dict['schema_pdf'],
                snapshot_dict['timestamp']
            ))
        
        # Restore primary key and sequence
        pg_cursor.execute("ALTER TABLE schema_snapshots ADD CONSTRAINT schema_snapshots_pkey PRIMARY KEY (id)")
        pg_cursor.execute("CREATE SEQUENCE IF NOT EXISTS schema_snapshots_id_seq OWNED BY schema_snapshots.id")
        pg_cursor.execute("SELECT setval('schema_snapshots_id_seq', (SELECT MAX(id) FROM schema_snapshots))")
        pg_cursor.execute("ALTER TABLE schema_snapshots ALTER COLUMN id SET DEFAULT nextval('schema_snapshots_id_seq')")
        
        pg_conn.commit()
        print(f"Migrated {len(snapshots)} schema snapshots")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Error migrating schema snapshots: {e}")
        raise
    finally:
        sqlite_conn.close()

def verify_migration(pg_conn):
    """Verify that data was migrated correctly."""
    print("Verifying migration...")
    
    sqlite_conn = get_sqlite_connection()
    sqlite_conn.row_factory = sqlite3.Row
    
    try:
        pg_cursor = pg_conn.cursor()
        sqlite_cursor = sqlite_conn.cursor()
        
        # Verify APIs count
        sqlite_cursor.execute("SELECT COUNT(*) as count FROM apis")
        sqlite_api_count = sqlite_cursor.fetchone()['count']
        
        pg_cursor.execute("SELECT COUNT(*) as count FROM apis")
        pg_api_count = pg_cursor.fetchone()[0]
        
        print(f"APIs - SQLite: {sqlite_api_count}, PostgreSQL: {pg_api_count}")
        assert sqlite_api_count == pg_api_count, "API count mismatch"
        
        # Verify schema snapshots count
        sqlite_cursor.execute("SELECT COUNT(*) as count FROM schema_snapshots")
        sqlite_snapshot_count = sqlite_cursor.fetchone()['count']
        
        pg_cursor.execute("SELECT COUNT(*) as count FROM schema_snapshots")
        pg_snapshot_count = pg_cursor.fetchone()[0]
        
        print(f"Schema Snapshots - SQLite: {sqlite_snapshot_count}, PostgreSQL: {pg_snapshot_count}")
        assert sqlite_snapshot_count == pg_snapshot_count, "Schema snapshot count mismatch"
        
        print("Migration verification successful!")
        
    except Exception as e:
        print(f"Verification error: {e}")
        raise
    finally:
        sqlite_conn.close()

def backup_sqlite_database():
    """Create a backup of SQLite database."""
    sqlite_path = os.path.join(os.path.dirname(__file__), 'backend', 'apisec.db')
    backup_path = f"backend/apisec_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    import shutil
    shutil.copy2(sqlite_path, backup_path)
    print(f"Created SQLite backup: {backup_path}")
    return backup_path

def main():
    """Main migration function."""
    print("Starting SQLite to PostgreSQL migration...")
    
    # Check if SQLite database exists
    sqlite_path = os.path.join(os.path.dirname(__file__), 'backend', 'apisec.db')
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database '{sqlite_path}' not found")
        sys.exit(1)
    
    # Create backup
    backup_path = backup_sqlite_database()
    
    try:
        # Connect to PostgreSQL
        pg_conn = get_postgres_connection()
        
        try:
            # Initialize PostgreSQL database
            from registry_db import init_db
            init_db()
            
            # Migrate data
            migrate_apis(pg_conn)
            migrate_schema_snapshots(pg_conn)
            
            # Verify migration
            verify_migration(pg_conn)
            
            print("Migration completed successfully!")
            print(f"SQLite database backed up to: {backup_path}")
            
        finally:
            pg_conn.close()
            
    except Exception as e:
        print(f"Migration failed: {e}")
        print("Please check the error above and restore from backup if needed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
