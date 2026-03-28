import os
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration and connection management."""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///apisec.db')
        self.is_postgres = 'postgresql' in self.database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_engine(self):
        """Initialize SQLAlchemy engine."""
        if self.engine is None:
            if self.is_postgres:
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,
                    pool_recycle=300,
                    echo=False
                )
            else:
                self.engine = create_engine(
                    self.database_url,
                    echo=False
                )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        return self.engine
    
    def get_connection(self):
        """Get database connection using psycopg2 for PostgreSQL or sqlite3 for SQLite."""
        if self.is_postgres:
            return psycopg2.connect(self.database_url)
        else:
            import sqlite3
            return sqlite3.connect('apisec.db')
    
    def get_session(self):
        """Get SQLAlchemy session."""
        if self.SessionLocal is None:
            self.init_engine()
        return self.SessionLocal()
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = 'all'):
        """Execute a query and return results."""
        if self.is_postgres:
            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params or ())
                    conn.commit()
                    
                    if fetch == 'all':
                        return [dict(row) for row in cursor.fetchall()]
                    elif fetch == 'one':
                        result = cursor.fetchone()
                        return dict(result) if result else None
                    elif fetch == 'many':
                        return cursor.fetchall()
                    elif fetch == 'rowcount':
                        return cursor.rowcount
                    else:
                        # For DDL statements, return rowcount
                        return cursor.rowcount
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                conn.close()
        else:
            import sqlite3
            conn = sqlite3.connect('apisec.db')
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                
                if fetch == 'all':
                    return [dict(row) for row in cursor.fetchall()]
                elif fetch == 'one':
                    result = cursor.fetchone()
                    return dict(result) if result else None
                elif fetch == 'many':
                    return cursor.fetchall()
                elif fetch == 'rowcount':
                    return cursor.rowcount
                else:
                    # For DDL statements, return rowcount
                    return cursor.rowcount
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                conn.close()

# Global database configuration instance
db_config = DatabaseConfig()
