#!/usr/bin/env python3
"""
Unit tests for FastAPI endpoints.
"""

import pytest
import json
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
from main import app


@pytest.mark.unit
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, test_client):
        """Test health check returns correct response."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.unit
class TestSchemaDiscoveryEndpoint:
    """Test schema discovery endpoint."""
    
    def test_discover_schema_success(self, test_client, sample_openapi_schema):
        """Test successful schema discovery."""
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.return_value = (sample_openapi_schema, "https://api.example.com/openapi.json")
            
            response = test_client.post(
                "/discover-schema",
                json={"url": "https://api.example.com"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["schema"] == sample_openapi_schema
            assert data["schema_url"] == "https://api.example.com/openapi.json"
            mock_crawl.assert_called_once_with("https://api.example.com")
    
    def test_discover_schema_not_found(self, test_client):
        """Test schema discovery when no schema is found."""
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.return_value = (None, None)
            
            response = test_client.post(
                "/discover-schema",
                json={"url": "https://api.example.com"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"
            assert "No schema found" in data["message"]
    
    def test_discover_schema_exception(self, test_client):
        """Test schema discovery with exception."""
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.side_effect = Exception("Network error")
            
            response = test_client.post(
                "/discover-schema",
                json={"url": "https://api.example.com"}
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            assert "Schema discovery failed" in data["error"]


@pytest.mark.unit
class TestRuntimeValidationEndpoint:
    """Test runtime validation endpoint."""
    
    @pytest.mark.asyncio
    async def test_validate_runtime_success(self, test_client, sample_openapi_schema):
        """Test successful runtime validation."""
        # Mock the runtime validator
        mock_result = Mock()
        mock_result.base_url = "https://api.example.com"
        mock_result.total_endpoints = 3
        mock_result.tested_endpoints = 3
        mock_result.passed_endpoints = 2
        mock_result.failed_endpoints = 1
        mock_result.overall_status = "partial_success"
        mock_result.validation_timestamp = "2024-01-01T00:00:00Z"
        
        mock_endpoint_test = Mock()
        mock_endpoint_test.method = "GET"
        mock_endpoint_test.path = "/users"
        mock_endpoint_test.url = "https://api.example.com/users"
        mock_endpoint_test.expected_status = 200
        mock_endpoint_test.actual_status = 200
        mock_endpoint_test.expected_response_schema = {}
        mock_endpoint_test.actual_response = {"users": []}
        mock_endpoint_test.response_time_ms = 150.5
        mock_endpoint_test.error = None
        mock_endpoint_test.status_mismatch = False
        mock_endpoint_test.schema_mismatch = False
        mock_endpoint_test.validation_passed = True
        
        mock_result.endpoint_tests = [mock_endpoint_test]
        
        with patch('main.create_runtime_validator') as mock_create:
            mock_validator = AsyncMock()
            mock_validator.validate_schema.return_value = mock_result
            mock_create.return_value = mock_validator
            
            response = test_client.post(
                "/validate-runtime",
                json={
                    "base_url": "https://api.example.com",
                    "schema_info": sample_openapi_schema
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "validation_result" in data
            
            result = data["validation_result"]
            assert result["base_url"] == "https://api.example.com"
            assert result["total_endpoints"] == 3
            assert result["passed_endpoints"] == 2
            assert result["failed_endpoints"] == 1
    
    def test_validate_runtime_exception(self, test_client, sample_openapi_schema):
        """Test runtime validation with exception."""
        with patch('main.create_runtime_validator') as mock_create:
            mock_create.side_effect = Exception("Validation error")
            
            response = test_client.post(
                "/validate-runtime",
                json={
                    "base_url": "https://api.example.com",
                    "schema_info": sample_openapi_schema
                }
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            assert "Runtime validation failed" in data["error"]


@pytest.mark.unit
@pytest.mark.database
class TestApiRegistryEndpoints:
    """Test API registry endpoints."""
    
    def test_get_apis_success(self, test_client, test_database, test_api_data):
        """Test getting all APIs."""
        # Create a test API first
        from tests.conftest import create_test_api
        create_test_api(test_database, test_api_data)
        
        response = test_client.get("/api/apis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "apis" in data
        assert len(data["apis"]) >= 1
    
    def test_get_apis_empty(self, test_client, test_database):
        """Test getting APIs when none exist."""
        response = test_client.get("/api/apis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["apis"] == []
    
    def test_create_api_success(self, test_client, test_database):
        """Test creating a new API."""
        response = test_client.post(
            "/api/apis",
            data={
                "name": "Test API",
                "base_url": "https://api.example.com",
                "description": "A test API"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "api" in data
        assert data["api"]["name"] == "Test API"
        assert data["api"]["base_url"] == "https://api.example.com"
    
    def test_create_api_duplicate(self, test_client, test_database, test_api_data):
        """Test creating a duplicate API."""
        # Create first API
        from tests.conftest import create_test_api
        create_test_api(test_database, test_api_data)
        
        # Try to create duplicate
        response = test_client.post(
            "/api/apis",
            data=test_api_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "exists"
        assert "already exists" in data["message"]
    
    def test_get_api_schemas_success(self, test_client, test_database, test_api_data, sample_openapi_schema):
        """Test getting schemas for an API."""
        # Create API and schema
        from tests.conftest import create_test_api, create_test_schema_snapshot
        api = create_test_api(test_database, test_api_data)
        create_test_schema_snapshot(test_database, api["id"], sample_openapi_schema)
        
        response = test_client.get(f"/api/apis/{api['id']}/schemas")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "schemas" in data
        assert len(data["schemas"]) >= 1
    
    def test_get_api_schemas_not_found(self, test_client):
        """Test getting schemas for non-existent API."""
        response = test_client.get("/api/apis/999/schemas")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["schemas"] == []
    
    def test_get_latest_schema_success(self, test_client, test_database, test_api_data, sample_openapi_schema):
        """Test getting latest schema for an API."""
        # Create API and schema
        from tests.conftest import create_test_api, create_test_schema_snapshot
        api = create_test_api(test_database, test_api_data)
        create_test_schema_snapshot(test_database, api["id"], sample_openapi_schema)
        
        response = test_client.get(f"/api/apis/{api['id']}/schemas/latest")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "schema" in data
    
    def test_get_latest_schema_not_found(self, test_client):
        """Test getting latest schema for API with no schemas."""
        response = test_client.get("/api/apis/999/schemas/latest")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "No schemas found" in data["error"]
    
    def test_delete_api_success(self, test_client, test_database, test_api_data):
        """Test deleting an API."""
        # Create API first
        from tests.conftest import create_test_api
        api = create_test_api(test_database, test_api_data)
        
        response = test_client.delete(f"/api/apis/{api['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "deleted successfully" in data["message"]
    
    def test_delete_api_not_found(self, test_client):
        """Test deleting non-existent API."""
        response = test_client.delete("/api/apis/999")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "API not found" in data["error"]


@pytest.mark.unit
@pytest.mark.database
class TestSchemaComparisonEndpoints:
    """Test schema comparison endpoints."""
    
    def test_compare_schema_versions_success(self, test_client, test_database, test_api_data, sample_openapi_schema, sample_swagger_schema):
        """Test comparing two schema versions."""
        # Create API and two schema versions
        from tests.conftest import create_test_api, create_test_schema_snapshot
        api = create_test_api(test_database, test_api_data)
        schema1 = create_test_schema_snapshot(test_database, api["id"], sample_openapi_schema)
        schema2 = create_test_schema_snapshot(test_database, api["id"], sample_swagger_schema)
        
        response = test_client.get(
            f"/api/schemas/{api['id']}/compare/{schema1['version']}/{schema2['version']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "changes" in data
        assert "schema1" in data
        assert "schema2" in data
    
    def test_compare_schema_versions_structured(self, test_client, test_database, test_api_data, sample_openapi_schema, sample_swagger_schema):
        """Test comparing schemas with structured output."""
        # Create API and two schema versions
        from tests.conftest import create_test_api, create_test_schema_snapshot
        api = create_test_api(test_database, test_api_data)
        schema1 = create_test_schema_snapshot(test_database, api["id"], sample_openapi_schema)
        schema2 = create_test_schema_snapshot(test_database, api["id"], sample_swagger_schema)
        
        response = test_client.get(
            f"/api/schemas/{api['id']}/compare/{schema1['version']}/{schema2['version']}?structured=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "summary" in data
        assert "changes" in data
    
    def test_compare_schema_versions_not_found(self, test_client, test_database, test_api_data):
        """Test comparing non-existent schema versions."""
        from tests.conftest import create_test_api
        api = create_test_api(test_database, test_api_data)
        
        response = test_client.get(
            f"/api/schemas/{api['id']}/compare/1/999"
        )
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["error"]


@pytest.mark.unit
class TestDifferentialAnalysisEndpoint:
    """Test differential analysis endpoint."""
    
    def test_analyze_diff_placeholder(self, test_client):
        """Test differential analysis endpoint (placeholder implementation)."""
        response = test_client.post(
            "/analyze-diff",
            params={
                "base_url": "https://api.example.com/v1",
                "new_url": "https://api.example.com/v2"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["base_url"] == "https://api.example.com/v1"
        assert data["new_url"] == "https://api.example.com/v2"
        assert "needs implementation" in data["message"]


@pytest.mark.unit
@pytest.mark.database
class TestApiScanningEndpoint:
    """Test API scanning endpoint."""
    
    def test_scan_api_success(self, test_client, test_database, test_api_data, sample_openapi_schema):
        """Test successful API scanning."""
        # Create API first
        from tests.conftest import create_test_api
        api = create_test_api(test_database, test_api_data)
        
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://api.example.com/openapi.json")
            mock_pdf.return_value = b"fake_pdf_content"
            
            response = test_client.post(f"/api/apis/{api['id']}/scan")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "New schema version stored" in data["message"]
    
    def test_scan_api_not_found(self, test_client):
        """Test scanning non-existent API."""
        response = test_client.post("/api/apis/999/scan")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "API not found" in data["error"]
    
    def test_scan_api_no_schema(self, test_client, test_database, test_api_data):
        """Test scanning API when no schema is found."""
        # Create API first
        from tests.conftest import create_test_api
        api = create_test_api(test_database, test_api_data)
        
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.return_value = (None, None)
            
            response = test_client.post(f"/api/apis/{api['id']}/scan")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "no_schema"
            assert "No schema found" in data["message"]


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def test_invalid_json_request(self, test_client):
        """Test handling of invalid JSON requests."""
        response = test_client.post(
            "/discover-schema",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, test_client):
        """Test handling of missing required fields."""
        response = test_client.post(
            "/discover-schema",
            json={}
        )
        assert response.status_code == 422
    
    def test_invalid_url_format(self, test_client):
        """Test handling of invalid URL format."""
        response = test_client.post(
            "/discover-schema",
            json={"url": "not-a-valid-url"}
        )
        # This should still work as URL validation is minimal
        assert response.status_code in [200, 422]
