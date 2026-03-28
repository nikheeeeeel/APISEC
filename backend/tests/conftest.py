#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for APISEC testing.
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock
from pathlib import Path
import sys

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from registry_db import init_db, ApiRegistry, SchemaSnapshot
from database_config import db_config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_database():
    """Create a temporary database for testing."""
    # Use PostgreSQL for testing if DATABASE_URL is set, otherwise use SQLite
    if os.getenv('TEST_DATABASE_URL'):
        # Use PostgreSQL for testing
        original_url = os.getenv('DATABASE_URL', '')
        test_url = os.getenv('TEST_DATABASE_URL')
        os.environ['DATABASE_URL'] = test_url
        
        # Initialize test database
        init_db()
        
        yield test_url
        
        # Restore original DATABASE_URL
        if original_url:
            os.environ['DATABASE_URL'] = original_url
        else:
            os.environ.pop('DATABASE_URL', None)
    else:
        # Fallback to SQLite for local testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        # Backup original database if it exists
        original_db_path = os.path.join(os.path.dirname(__file__), '..', 'apisec.db')
        backup_path = None
        if os.path.exists(original_db_path):
            backup_path = original_db_path + '.backup'
            os.rename(original_db_path, backup_path)
        
        # Set database path for test
        os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
        init_db()
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        
        # Restore original database
        if backup_path and os.path.exists(backup_path):
            os.rename(backup_path, original_db_path)


@pytest.fixture
def test_client(test_database):
    """Create a test client with temporary database."""
    # The DATABASE_URL is already set in test_database fixture
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_openapi_schema():
    """Sample OpenAPI 3.0 schema for testing."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
            "description": "A test API for testing purposes"
        },
        "servers": [
            {"url": "https://api.example.com/v1", "description": "Production server"}
        ],
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get all users",
                    "description": "Retrieve a list of all users",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/User"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create a new user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/UserCreate"
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "User created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/users/{userId}": {
                "get": {
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer", "format": "int64"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/User"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "User not found"
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "name", "email"],
                    "properties": {
                        "id": {"type": "integer", "format": "int64"},
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "created_at": {"type": "string", "format": "date-time"}
                    }
                },
                "UserCreate": {
                    "type": "object",
                    "required": ["name", "email"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "email": {"type": "string", "format": "email"}
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_swagger_schema():
    """Sample Swagger 2.0 schema for testing."""
    return {
        "swagger": "2.0",
        "info": {
            "title": "Petstore API",
            "version": "1.0.0",
            "description": "A sample API that uses a petstore as an example"
        },
        "host": "petstore.swagger.io",
        "basePath": "/v2",
        "schemes": ["https"],
        "paths": {
            "/pet": {
                "post": {
                    "tags": ["pet"],
                    "summary": "Add a new pet to the store",
                    "operationId": "addPet",
                    "consumes": ["application/json"],
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "in": "body",
                            "name": "body",
                            "description": "Pet object that needs to be added to the store",
                            "required": True,
                            "schema": {"$ref": "#/definitions/Pet"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "successful operation",
                            "schema": {"$ref": "#/definitions/Pet"}
                        },
                        "405": {"description": "Invalid input"}
                    }
                }
            },
            "/pet/{petId}": {
                "get": {
                    "tags": ["pet"],
                    "summary": "Find pet by ID",
                    "operationId": "getPetById",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "type": "integer",
                            "format": "int64"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "successful operation",
                            "schema": {"$ref": "#/definitions/Pet"}
                        },
                        "400": {"description": "Invalid ID supplied"},
                        "404": {"description": "Pet not found"}
                    }
                }
            }
        },
        "definitions": {
            "Pet": {
                "type": "object",
                "required": ["name", "photoUrls"],
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "category": {"$ref": "#/definitions/Category"},
                    "name": {"type": "string", "example": "doggie"},
                    "photoUrls": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "tags": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/Tag"}
                    },
                    "status": {
                        "type": "string",
                        "description": "pet status in the store",
                        "enum": ["available", "pending", "sold"]
                    }
                }
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"}
                }
            },
            "Tag": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"}
                }
            }
        }
    }


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls."""
    client = Mock()
    client.get = Mock()
    client.post = Mock()
    client.put = Mock()
    client.delete = Mock()
    return client


@pytest.fixture
def mock_async_http_client():
    """Mock async HTTP client for external API calls."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def sample_api_responses():
    """Sample API responses for mocking."""
    return {
        "users_list": {
            "status": 200,
            "json": [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
            ]
        },
        "user_detail": {
            "status": 200,
            "json": {"id": 1, "name": "John Doe", "email": "john@example.com"}
        },
        "user_created": {
            "status": 201,
            "json": {"id": 3, "name": "New User", "email": "new@example.com"}
        },
        "not_found": {
            "status": 404,
            "json": {"error": "User not found"}
        },
        "server_error": {
            "status": 500,
            "json": {"error": "Internal server error"}
        }
    }


@pytest.fixture
def temp_directory():
    """Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_schema_file(sample_openapi_schema, temp_directory):
    """Create a temporary schema file for testing."""
    schema_file = temp_directory / "schema.json"
    with open(schema_file, 'w') as f:
        json.dump(sample_openapi_schema, f)
    return schema_file


@pytest.fixture
def mock_runtime_validator():
    """Mock runtime validator for testing."""
    validator = Mock()
    validator.validate_schema = AsyncMock()
    return validator


@pytest.fixture
def test_api_data():
    """Sample data for API registry testing."""
    return {
        "name": "Test API",
        "base_url": "https://api.example.com",
        "description": "A test API for testing purposes"
    }


# Helper functions for tests
def create_test_api(db_path: str, api_data: dict = None) -> dict:
    """Create a test API in the database."""
    if api_data is None:
        api_data = {
            "name": "Test API",
            "base_url": "https://api.example.com",
            "description": "A test API"
        }
    
    # DATABASE_URL is already set in the test fixture
    return ApiRegistry.create(**api_data)


def create_test_schema_snapshot(db_path: str, api_id: int, schema: dict) -> dict:
    """Create a test schema snapshot in the database."""
    # DATABASE_URL is already set in the test fixture
    return SchemaSnapshot.create(api_id, schema)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require external services)"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests (end-to-end workflows)"
    )
    config.addinivalue_line(
        "markers", "load: Load tests (performance testing)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 1 second"
    )
    config.addinivalue_line(
        "markers", "external: Tests that require internet access"
    )
    config.addinivalue_line(
        "markers", "database: Tests that require database access"
    )


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data after each test."""
    yield
    # Add any cleanup logic here if needed
    pass
