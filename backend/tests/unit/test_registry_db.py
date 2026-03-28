#!/usr/bin/env python3
"""
Unit tests for registry database functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, Mock

# Import the modules we're testing
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from registry_db import init_db, ApiRegistry, SchemaSnapshot


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseInitialization:
    """Test database initialization functionality."""
    
    def test_init_db_creates_tables(self, test_database):
        """Test that init_db creates the necessary tables."""
        from database_config import db_config
        
        # Check that tables exist by querying them
        if db_config.is_postgres:
            # PostgreSQL check
            result = db_config.execute_query("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('apis', 'schema_snapshots')
            """, (), 'all')
            assert len(result) == 2
        else:
            # SQLite check
            result = db_config.execute_query("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('apis', 'schema_snapshots')
            """, (), 'all')
            assert len(result) == 2
    
    def test_init_db_idempotent(self, test_database):
        """Test that init_db can be called multiple times."""
        # Call init_db twice
        init_db()
        init_db()
        
        # Should not raise an error
        conn = sqlite3.connect(test_database)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['api_registry', 'schema_snapshots']
        for table in expected_tables:
            assert table in tables
        
        conn.close()


@pytest.mark.unit
@pytest.mark.database
class TestApiRegistry:
    """Test API registry functionality."""
    
    def test_create_api_success(self, test_database, test_api_data):
        """Test successful API creation."""
        os.environ['DB_PATH'] = test_database
        
        api = ApiRegistry.create(**test_api_data)
        
        assert api is not None
        assert api['name'] == test_api_data['name']
        assert api['base_url'] == test_api_data['base_url']
        assert api['description'] == test_api_data['description']
        assert 'id' in api
        assert 'created_at' in api
    
    def test_create_api_duplicate_url(self, test_database, test_api_data):
        """Test creating API with duplicate URL."""
        os.environ['DB_PATH'] = test_database
        
        # Create first API
        api1 = ApiRegistry.create(**test_api_data)
        
        # Try to create duplicate
        api2 = ApiRegistry.create(**test_api_data)
        
        assert api2 is None
    
    def test_get_all_apis_empty(self, test_database):
        """Test getting all APIs when none exist."""
        os.environ['DB_PATH'] = test_database
        
        apis = ApiRegistry.get_all()
        assert apis == []
    
    def test_get_all_apis_with_data(self, test_database, test_api_data):
        """Test getting all APIs with data."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Get all APIs
        apis = ApiRegistry.get_all()
        
        assert len(apis) == 1
        assert apis[0]['id'] == api['id']
        assert apis[0]['name'] == api['name']
    
    def test_get_api_by_id_success(self, test_database, test_api_data):
        """Test getting API by ID."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Get API by ID
        found_api = ApiRegistry.get_by_id(api['id'])
        
        assert found_api is not None
        assert found_api['id'] == api['id']
        assert found_api['name'] == api['name']
    
    def test_get_api_by_id_not_found(self, test_database):
        """Test getting API by ID when not found."""
        os.environ['DB_PATH'] = test_database
        
        api = ApiRegistry.get_by_id(999)
        assert api is None
    
    def test_get_api_by_url_success(self, test_database, test_api_data):
        """Test getting API by URL."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Get API by URL
        found_api = ApiRegistry.get_by_url(test_api_data['base_url'])
        
        assert found_api is not None
        assert found_api['id'] == api['id']
        assert found_api['base_url'] == api['base_url']
    
    def test_get_api_by_url_not_found(self, test_database):
        """Test getting API by URL when not found."""
        os.environ['DB_PATH'] = test_database
        
        api = ApiRegistry.get_by_url("https://nonexistent.example.com")
        assert api is None
    
    def test_update_api_success(self, test_database, test_api_data):
        """Test updating API."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Update API
        updated_data = {
            'name': 'Updated API Name',
            'base_url': 'https://updated.example.com',
            'description': 'Updated description'
        }
        
        success = ApiRegistry.update(api['id'], **updated_data)
        assert success is True
        
        # Verify update
        updated_api = ApiRegistry.get_by_id(api['id'])
        assert updated_api['name'] == 'Updated API Name'
        assert updated_api['base_url'] == 'https://updated.example.com'
        assert updated_api['description'] == 'Updated description'
    
    def test_update_api_not_found(self, test_database):
        """Test updating non-existent API."""
        os.environ['DB_PATH'] = test_database
        
        success = ApiRegistry.update(999, name='Updated Name')
        assert success is False
    
    def test_delete_api_success(self, test_database, test_api_data):
        """Test deleting API."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Delete API
        success = ApiRegistry.delete(api['id'])
        assert success is True
        
        # Verify deletion
        found_api = ApiRegistry.get_by_id(api['id'])
        assert found_api is None
    
    def test_delete_api_not_found(self, test_database):
        """Test deleting non-existent API."""
        os.environ['DB_PATH'] = test_database
        
        success = ApiRegistry.delete(999)
        assert success is False


@pytest.mark.unit
@pytest.mark.database
class TestSchemaSnapshot:
    """Test schema snapshot functionality."""
    
    def test_create_schema_snapshot_success(self, test_database, test_api_data, sample_openapi_schema):
        """Test successful schema snapshot creation."""
        os.environ['DB_PATH'] = test_database
        
        # Create API first
        api = ApiRegistry.create(**test_api_data)
        
        # Create schema snapshot
        snapshot = SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        assert snapshot is not None
        assert snapshot['api_id'] == api['id']
        assert 'schema_json' in snapshot
        assert 'version' in snapshot
        assert 'timestamp' in snapshot
        assert snapshot['version'] == 1
    
    def test_create_schema_snapshot_auto_increment(self, test_database, test_api_data, sample_openapi_schema, sample_swagger_schema):
        """Test schema snapshot version auto-increment."""
        os.environ['DB_PATH'] = test_database
        
        # Create API first
        api = ApiRegistry.create(**test_api_data)
        
        # Create first snapshot
        snapshot1 = SchemaSnapshot.create(api['id'], sample_openapi_schema)
        assert snapshot1['version'] == 1
        
        # Create second snapshot
        snapshot2 = SchemaSnapshot.create(api['id'], sample_swagger_schema)
        assert snapshot2['version'] == 2
    
    def test_create_schema_snapshot_api_not_found(self, test_database, sample_openapi_schema):
        """Test creating schema snapshot for non-existent API."""
        os.environ['DB_PATH'] = test_database
        
        snapshot = SchemaSnapshot.create(999, sample_openapi_schema)
        assert snapshot is None
    
    def test_get_by_api_success(self, test_database, test_api_data, sample_openapi_schema):
        """Test getting schemas by API ID."""
        os.environ['DB_PATH'] = test_database
        
        # Create API and schema
        api = ApiRegistry.create(**test_api_data)
        snapshot = SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        # Get schemas by API
        schemas = SchemaSnapshot.get_by_api(api['id'])
        
        assert len(schemas) == 1
        assert schemas[0]['id'] == snapshot['id']
        assert schemas[0]['version'] == snapshot['version']
    
    def test_get_by_api_empty(self, test_database, test_api_data):
        """Test getting schemas by API ID when none exist."""
        os.environ['DB_PATH'] = test_database
        
        # Create API only
        api = ApiRegistry.create(**test_api_data)
        
        # Get schemas by API
        schemas = SchemaSnapshot.get_by_api(api['id'])
        assert schemas == []
    
    def test_get_by_version_success(self, test_database, test_api_data, sample_openapi_schema):
        """Test getting schema by version."""
        os.environ['DB_PATH'] = test_database
        
        # Create API and schema
        api = ApiRegistry.create(**test_api_data)
        snapshot = SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        # Get schema by version
        schema = SchemaSnapshot.get_by_version(api['id'], 1)
        
        assert schema is not None
        assert schema['id'] == snapshot['id']
        assert schema['version'] == 1
    
    def test_get_by_version_not_found(self, test_database, test_api_data):
        """Test getting schema by version when not found."""
        os.environ['DB_PATH'] = test_database
        
        # Create API only
        api = ApiRegistry.create(**test_api_data)
        
        # Get non-existent schema
        schema = SchemaSnapshot.get_by_version(api['id'], 999)
        assert schema is None
    
    def test_get_latest_success(self, test_database, test_api_data, sample_openapi_schema, sample_swagger_schema):
        """Test getting latest schema."""
        os.environ['DB_PATH'] = test_database
        
        # Create API and multiple schemas
        api = ApiRegistry.create(**test_api_data)
        SchemaSnapshot.create(api['id'], sample_openapi_schema)
        SchemaSnapshot.create(api['id'], sample_swagger_schema)
        
        # Get latest schema
        latest = SchemaSnapshot.get_latest(api['id'])
        
        assert latest is not None
        assert latest['version'] == 2  # Should be the second schema
    
    def test_get_latest_empty(self, test_database, test_api_data):
        """Test getting latest schema when none exist."""
        os.environ['DB_PATH'] = test_database
        
        # Create API only
        api = ApiRegistry.create(**test_api_data)
        
        # Get latest schema
        latest = SchemaSnapshot.get_latest(api['id'])
        assert latest is None
    
    def test_update_pdf_success(self, test_database, test_api_data, sample_openapi_schema):
        """Test updating PDF content."""
        os.environ['DB_PATH'] = test_database
        
        # Create API and schema
        api = ApiRegistry.create(**test_api_data)
        snapshot = SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        # Update PDF
        pdf_content = b"fake pdf content"
        success = SchemaSnapshot.update_pdf(snapshot['id'], pdf_content)
        assert success is True
        
        # Verify update
        updated_schema = SchemaSnapshot.get_by_version(api['id'], 1)
        assert updated_schema['schema_pdf'] == pdf_content
    
    def test_update_pdf_not_found(self, test_database):
        """Test updating PDF for non-existent schema."""
        os.environ['DB_PATH'] = test_database
        
        success = SchemaSnapshot.update_pdf(999, b"fake pdf content")
        assert success is False
    
    def test_create_if_different_new_schema(self, test_database, test_api_data, sample_openapi_schema):
        """Test create_if_different with new schema."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Create schema (first time)
        result = SchemaSnapshot.create_if_different(api['id'], sample_openapi_schema)
        
        assert result['status'] == 'new'
        assert 'schema' in result
        assert result['schema']['schema_json'] == sample_openapi_schema
    
    def test_create_if_different_unchanged_schema(self, test_database, test_api_data, sample_openapi_schema):
        """Test create_if_different with unchanged schema."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Create schema (first time)
        SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        # Try to create same schema again
        result = SchemaSnapshot.create_if_different(api['id'], sample_openapi_schema)
        
        assert result['status'] == 'unchanged'
        assert 'schema' in result
        assert result['schema']['schema_json'] == sample_openapi_schema
    
    def test_create_if_different_changed_schema(self, test_database, test_api_data, sample_openapi_schema, sample_swagger_schema):
        """Test create_if_different with changed schema."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Create first schema
        SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        # Create different schema
        result = SchemaSnapshot.create_if_different(api['id'], sample_swagger_schema)
        
        assert result['status'] == 'changed'
        assert 'schema' in result
        assert result['schema']['schema_json'] == sample_swagger_schema


@pytest.mark.unit
@pytest.mark.database
class TestDatabaseConstraints:
    """Test database constraints and edge cases."""
    
    def test_api_name_required(self, test_database):
        """Test that API name is required."""
        os.environ['DB_PATH'] = test_database
        
        with pytest.raises(Exception):  # Should raise an integrity error
            ApiRegistry.create(
                name=None,
                base_url="https://example.com"
            )
    
    def test_api_base_url_required(self, test_database):
        """Test that API base URL is required."""
        os.environ['DB_PATH'] = test_database
        
        with pytest.raises(Exception):  # Should raise an integrity error
            ApiRegistry.create(
                name="Test API",
                base_url=None
            )
    
    def test_schema_json_required(self, test_database, test_api_data):
        """Test that schema JSON is required."""
        os.environ['DB_PATH'] = test_database
        
        # Create API first
        api = ApiRegistry.create(**test_api_data)
        
        # Try to create schema without JSON
        with pytest.raises(Exception):  # Should raise an integrity error
            SchemaSnapshot.create(api['id'], None)
    
    def test_foreign_key_constraints(self, test_database, sample_openapi_schema):
        """Test foreign key constraints."""
        os.environ['DB_PATH'] = test_database
        
        # Try to create schema for non-existent API
        with pytest.raises(Exception):  # Should raise a foreign key error
            SchemaSnapshot.create(999, sample_openapi_schema)
    
    def test_cascade_delete(self, test_database, test_api_data, sample_openapi_schema):
        """Test cascade delete behavior."""
        os.environ['DB_PATH'] = test_database
        
        # Create API and schema
        api = ApiRegistry.create(**test_api_data)
        snapshot = SchemaSnapshot.create(api['id'], sample_openapi_schema)
        
        # Delete API (should cascade delete schemas)
        ApiRegistry.delete(api['id'])
        
        # Verify schema is also deleted
        schema = SchemaSnapshot.get_by_version(api['id'], 1)
        assert schema is None


@pytest.mark.unit
@pytest.mark.database
class TestDatabasePerformance:
    """Test database performance considerations."""
    
    def test_large_schema_storage(self, test_database, test_api_data):
        """Test storing large schema data."""
        os.environ['DB_PATH'] = test_database
        
        # Create API
        api = ApiRegistry.create(**test_api_data)
        
        # Create large schema
        large_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Large API", "version": "1.0.0"},
            "paths": {
                f"/endpoint_{i}": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                f"field_{j}": {"type": "string"}
                                                for j in range(100)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                for i in range(1000)
            }
        }
        
        # Should handle large schema without issues
        snapshot = SchemaSnapshot.create(api['id'], large_schema)
        assert snapshot is not None
        
        # Should be able to retrieve it
        retrieved = SchemaSnapshot.get_by_version(api['id'], 1)
        assert retrieved is not None
        assert len(retrieved['schema_json']['paths']) == 1000
