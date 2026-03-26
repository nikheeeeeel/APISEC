import sqlite3
import psycopg2
import os
import sys
from passlib.context import CryptContext

DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "userpassword")
DB_NAME = os.environ.get("DB_NAME", "apisec")
SQLITE_PATH = "apisec.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def main():
    if not os.path.exists(SQLITE_PATH):
        print(f"SQLite DB {SQLITE_PATH} not found. Nothing to migrate.")
        return

    # 1. Connect to Postgres
    print("Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, 
            user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        )
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"Failed to connect to Postgres: {e}")
        sys.exit(1)

    # Make sure tables exist
    from registry_db import init_db
    init_db()

    # 2. Connect to SQLite
    print("Connecting to SQLite...")
    sl_conn = sqlite3.connect(SQLITE_PATH)
    sl_conn.row_factory = sqlite3.Row
    sl_cursor = sl_conn.cursor()

    # 3. Create Default User in Postgres
    print("Creating default user 'user'...")
    hashed_password = pwd_context.hash("user")
    
    pg_cursor.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, CURRENT_TIMESTAMP) ON CONFLICT (username) DO NOTHING RETURNING id",
        ("user", hashed_password)
    )
    result = pg_cursor.fetchone()
    if result:
        user_id = result[0]
        print(f"Created standard user. ID = {user_id}")
    else:
        pg_cursor.execute("SELECT id FROM users WHERE username = 'user'")
        user_id = pg_cursor.fetchone()[0]
        print(f"User already exists. ID = {user_id}")

    # 4. Migrate APIs
    print("Migrating APIs...")
    sl_cursor.execute("SELECT * FROM apis")
    apis = sl_cursor.fetchall()
    
    # Store old to new ID mapping
    api_id_map = {}
    
    for api in apis:
        pg_cursor.execute(
            "INSERT INTO apis (user_id, name, base_url, description, date_added) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, api['name'], api['base_url'], api['description'], api['date_added'])
        )
        new_api_id = pg_cursor.fetchone()[0]
        api_id_map[api['id']] = new_api_id
        print(f"  Migrated API: {api['name']} (old id: {api['id']} -> new id: {new_api_id})")

    # 5. Migrate Schema Snapshots
    print("Migrating Schema Snapshots...")
    sl_cursor.execute("SELECT * FROM schema_snapshots")
    snapshots = sl_cursor.fetchall()
    
    for snap in snapshots:
        old_api_id = snap['api_id']
        if old_api_id not in api_id_map:
            print(f"  Warning: Skipping snapshot for missing api_id {old_api_id}")
            continue
            
        new_api_id = api_id_map[old_api_id]
        
        pg_cursor.execute(
            "INSERT INTO schema_snapshots (api_id, version_number, schema_json, schema_pdf, timestamp) VALUES (%s, %s, %s, %s, %s)",
            (new_api_id, snap['version_number'], snap['schema_json'], snap['schema_pdf'], snap['timestamp'])
        )
        print(f"  Migrated Snapshot Version {snap['version_number']} for mapped API {new_api_id}")

    pg_conn.commit()
    print("Migration successful! Committing data.")
    
    # Clean up
    pg_cursor.close()
    pg_conn.close()
    sl_cursor.close()
    sl_conn.close()
    
    # Delete SQLite Database
    print(f"Deleting SQLite database {SQLITE_PATH}...")
    try:
        os.remove(SQLITE_PATH)
        print("SQLite database successfully removed.")
    except Exception as e:
        print(f"Warning: Failed to delete {SQLITE_PATH}: {e}")

if __name__ == "__main__":
    main()
