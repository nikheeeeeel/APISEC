#!/usr/bin/env python3
"""
Integration tests for complete API workflows.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
import tempfile
import os

# Import the modules we're testing
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from main import app
from runtime_validator import create_runtime_validator
from schema_monitor import crawl_for_schema, compare_schemas


@pytest.mark.integration
@pytest.mark.database
class TestCompleteApiWorkflow:
    """Test complete API monitoring workflow."""
    
    def test_full_workflow_schema_discovery_to_monitoring(self, test_client, test_database, sample_openapi_schema):
        """Test complete workflow from schema discovery to monitoring."""
        # Step 1: Create API
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Test API",
                "base_url": "https://api.example.com",
                "description": "A test API for integration testing"
            }
        )
        assert api_response.status_code == 200
        api_data = api_response.json()
        api_id = api_data["api"]["id"]
        
        # Step 2: Discover schema
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://api.example.com/openapi.json")
            mock_pdf.return_value = b"fake_pdf_content"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
            scan_data = scan_response.json()
            assert scan_data["status"] == "success"
        
        # Step 3: Get all schemas for the API
        schemas_response = test_client.get(f"/api/apis/{api_id}/schemas")
        assert schemas_response.status_code == 200
        schemas_data = schemas_response.json()
        assert len(schemas_data["schemas"]) == 1
        
        # Step 4: Get latest schema
        latest_response = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        assert latest_response.status_code == 200
        latest_data = latest_response.json()
        assert latest_data["schema"]["schema_json"] == sample_openapi_schema
        
        # Step 5: Perform runtime validation
        with patch('main.create_runtime_validator') as mock_create:
            mock_result = Mock()
            mock_result.base_url = "https://api.example.com"
            mock_result.total_endpoints = len(sample_openapi_schema.get("paths", {}))
            mock_result.tested_endpoints = mock_result.total_endpoints
            mock_result.passed_endpoints = mock_result.total_endpoints
            mock_result.failed_endpoints = 0
            mock_result.overall_status = "success"
            mock_result.validation_timestamp = "2024-01-01T00:00:00Z"
            mock_result.endpoint_tests = []
            
            mock_validator = AsyncMock()
            mock_validator.validate_schema.return_value = mock_result
            mock_create.return_value = mock_validator
            
            validation_response = test_client.post(
                "/validate-runtime",
                json={
                    "base_url": "https://api.example.com",
                    "schema_info": sample_openapi_schema
                }
            )
            assert validation_response.status_code == 200
            validation_data = validation_response.json()
            assert validation_data["status"] == "success"
        
        # Step 6: Get all APIs to verify persistence
        all_apis_response = test_client.get("/api/apis")
        assert all_apis_response.status_code == 200
        all_apis_data = all_apis_response.json()
        assert len(all_apis_data["apis"]) == 1
        assert all_apis_data["apis"][0]["id"] == api_id


@pytest.mark.integration
@pytest.mark.database
class TestSchemaVersioningWorkflow:
    """Test schema versioning and comparison workflow."""
    
    def test_schema_evolution_workflow(self, test_client, test_database, sample_openapi_schema, sample_swagger_schema):
        """Test workflow of schema evolution and comparison."""
        # Step 1: Create API
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Evolving API",
                "base_url": "https://api.example.com",
                "description": "An API that evolves over time"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Add first schema version
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://api.example.com/v1/openapi.json")
            mock_pdf.return_value = b"pdf_v1"
            
            scan1_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan1_response.status_code == 200
        
        # Step 3: Add second schema version
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_swagger_schema, "https://api.example.com/v2/swagger.json")
            mock_pdf.return_value = b"pdf_v2"
            
            scan2_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan2_response.status_code == 200
        
        # Step 4: Get all schema versions
        schemas_response = test_client.get(f"/api/apis/{api_id}/schemas")
        schemas_data = schemas_response.json()
        assert len(schemas_data["schemas"]) == 2
        
        # Step 5: Compare schema versions
        schemas = schemas_data["schemas"]
        v1_id = schemas[0]["version"]
        v2_id = schemas[1]["version"]
        
        compare_response = test_client.get(
            f"/api/schemas/{api_id}/compare/{v1_id}/{v2_id}"
        )
        assert compare_response.status_code == 200
        compare_data = compare_response.json()
        assert compare_data["status"] == "success"
        assert "changes" in compare_data
        
        # Step 6: Compare with structured output
        structured_response = test_client.get(
            f"/api/schemas/{api_id}/compare/{v1_id}/{v2_id}?structured=true"
        )
        assert structured_response.status_code == 200
        structured_data = structured_response.json()
        assert structured_data["status"] == "success"
        assert "summary" in structured_data
        assert "changes" in structured_data


@pytest.mark.integration
@pytest.mark.external
class TestExternalApiIntegration:
    """Test integration with external APIs."""
    
    @pytest.mark.slow
    def test_real_api_discovery_and_validation(self, test_client, test_database):
        """Test workflow with real external API (if available)."""
        # This test requires internet access and may be slow
        # Use a known stable API like JSONPlaceholder
        
        # Step 1: Create API entry
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "JSONPlaceholder API",
                "base_url": "https://jsonplaceholder.typicode.com",
                "description": "Free fake API for testing"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Try to discover schema (may not find one)
        discovery_response = test_client.post(
            "/discover-schema",
            json={"url": "https://jsonplaceholder.typicode.com"}
        )
        
        # JSONPlaceholder doesn't have OpenAPI/Swagger, so this should return not_found
        assert discovery_response.status_code == 200
        discovery_data = discovery_response.json()
        assert discovery_data["status"] in ["not_found", "success"]  # Allow both outcomes
        
        # Step 3: If schema was found, try validation
        if discovery_data["status"] == "success":
            schema = discovery_data["schema"]
            
            # Create a minimal runtime validator mock since we can't actually validate
            with patch('main.create_runtime_validator') as mock_create:
                mock_result = Mock()
                mock_result.base_url = "https://jsonplaceholder.typicode.com"
                mock_result.total_endpoints = 1
                mock_result.tested_endpoints = 1
                mock_result.passed_endpoints = 1
                mock_result.failed_endpoints = 0
                mock_result.overall_status = "success"
                mock_result.validation_timestamp = "2024-01-01T00:00:00Z"
                mock_result.endpoint_tests = []
                
                mock_validator = AsyncMock()
                mock_validator.validate_schema.return_value = mock_result
                mock_create.return_value = mock_validator
                
                validation_response = test_client.post(
                    "/validate-runtime",
                    json={
                        "base_url": "https://jsonplaceholder.typicode.com",
                        "schema_info": schema
                    }
                )
                assert validation_response.status_code == 200


@pytest.mark.integration
@pytest.mark.database
class TestConcurrentOperations:
    """Test concurrent API operations."""
    
    def test_concurrent_api_creation(self, test_client, test_database):
        """Test creating multiple APIs concurrently."""
        import threading
        import time
        
        results = []
        errors = []
        
        def create_api(index):
            try:
                response = test_client.post(
                    "/api/apis",
                    data={
                        "name": f"Concurrent API {index}",
                        "base_url": f"https://api{index}.example.com",
                        "description": f"API number {index}"
                    }
                )
                results.append((index, response.status_code, response.json()))
            except Exception as e:
                errors.append((index, str(e)))
        
        # Create 5 APIs concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_api, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # All should succeed
        for index, status_code, data in results:
            assert status_code == 200, f"API {index} creation failed with status {status_code}"
            assert data["status"] == "success"
        
        # Verify all APIs were created
        all_apis_response = test_client.get("/api/apis")
        all_apis_data = all_apis_response.json()
        assert len(all_apis_data["apis"]) == 5
    
    def test_concurrent_schema_scanning(self, test_client, test_database, sample_openapi_schema, sample_swagger_schema):
        """Test scanning multiple APIs concurrently."""
        import threading
        
        # Create multiple APIs first
        api_ids = []
        for i in range(3):
            response = test_client.post(
                "/api/apis",
                data={
                    "name": f"Scan Test API {i}",
                    "base_url": f"https://scanapi{i}.example.com",
                    "description": f"API for scanning test {i}"
                }
            )
            api_ids.append(response.json()["api"]["id"])
        
        results = []
        errors = []
        
        def scan_api(api_id, schema):
            try:
                with patch('main.crawl_for_schema') as mock_crawl, \
                     patch('main.generate_pdf_from_json') as mock_pdf:
                    
                    mock_crawl.return_value = (schema, f"https://scanapi{api_id}.example.com/schema.json")
                    mock_pdf.return_value = f"pdf_content_{api_id}".encode()
                    
                    response = test_client.post(f"/api/apis/{api_id}/scan")
                    results.append((api_id, response.status_code, response.json()))
            except Exception as e:
                errors.append((api_id, str(e)))
        
        # Scan APIs concurrently
        threads = []
        schemas = [sample_openapi_schema, sample_swagger_schema, sample_openapi_schema]
        
        for i, api_id in enumerate(api_ids):
            thread = threading.Thread(target=scan_api, args=(api_id, schemas[i]))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3
        
        for api_id, status_code, data in results:
            assert status_code == 200
            assert data["status"] == "success"


@pytest.mark.integration
@pytest.mark.database
class TestErrorRecoveryWorkflows:
    """Test error recovery in workflows."""
    
    def test_workflow_recovery_after_database_error(self, test_client, test_database, sample_openapi_schema):
        """Test workflow recovery after database errors."""
        # Step 1: Create API successfully
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Recovery Test API",
                "base_url": "https://recovery.example.com",
                "description": "API for testing recovery"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Simulate database error during schema scan
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf, \
             patch('registry_db.SchemaSnapshot.create') as mock_create:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://recovery.example.com/schema.json")
            mock_pdf.return_value = b"pdf_content"
            mock_create.side_effect = Exception("Database error")
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 500
        
        # Step 3: Verify API still exists and can be queried
        api_get_response = test_client.get("/api/apis")
        apis_data = api_get_response.json()
        assert len(apis_data["apis"]) == 1
        assert apis_data["apis"][0]["id"] == api_id
        
        # Step 4: Retry schema scan successfully
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://recovery.example.com/schema.json")
            mock_pdf.return_value = b"pdf_content"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
            scan_data = scan_response.json()
            assert scan_data["status"] == "success"
    
    def test_workflow_recovery_after_network_error(self, test_client, test_database):
        """Test workflow recovery after network errors."""
        # Step 1: Create API
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Network Test API",
                "base_url": "https://network.example.com",
                "description": "API for testing network errors"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Simulate network error during schema discovery
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.side_effect = Exception("Network timeout")
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 500
        
        # Step 3: Verify API still exists
        api_get_response = test_client.get(f"/api/apis/{api_id}/schemas")
        assert api_get_response.status_code == 200
        schemas_data = api_get_response.json()
        assert schemas_data["schemas"] == []  # No schemas due to error
        
        # Step 4: Retry with successful network call
        sample_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {"/test": {"get": {"responses": {"200": {"description": "Success"}}}}}
        }
        
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_schema, "https://network.example.com/schema.json")
            mock_pdf.return_value = b"pdf_content"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
            scan_data = scan_response.json()
            assert scan_data["status"] == "success"


@pytest.mark.integration
@pytest.mark.database
class TestDataIntegrityWorkflows:
    """Test data integrity throughout workflows."""
    
    def test_schema_data_integrity_through_workflow(self, test_client, test_database, sample_openapi_schema):
        """Test that schema data remains intact through the workflow."""
        # Step 1: Create API
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Integrity Test API",
                "base_url": "https://integrity.example.com",
                "description": "API for testing data integrity"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Store schema
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://integrity.example.com/schema.json")
            mock_pdf.return_value = b"pdf_content"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
        
        # Step 3: Retrieve schema and verify integrity
        latest_response = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        latest_data = latest_response.json()
        retrieved_schema = latest_data["schema"]["schema_json"]
        
        # Verify schema is identical
        assert retrieved_schema == sample_openapi_schema
        
        # Step 4: Update API and verify schema is unaffected
        update_response = test_client.post(
            "/api/apis",
            data={
                "name": "Updated Integrity Test API",
                "base_url": "https://integrity.example.com",
                "description": "Updated description"
            }
        )
        # This should create a new API, not update existing one
        
        # Step 5: Verify original schema is still intact
        latest_response2 = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        latest_data2 = latest_response2.json()
        retrieved_schema2 = latest_data2["schema"]["schema_json"]
        
        assert retrieved_schema2 == sample_openapi_schema
    
    def test_large_schema_handling_integrity(self, test_client, test_database):
        """Test integrity of large schema handling."""
        # Create a large schema
        large_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Large API", "version": "1.0.0"},
            "paths": {
                f"/endpoint_{i}": {
                    "get": {
                        "summary": f"Get endpoint {i}",
                        "description": f"This is endpoint number {i} with lots of details",
                        "parameters": [
                            {
                                "name": f"param_{j}",
                                "in": "query",
                                "required": j == 0,
                                "schema": {"type": "string"},
                                "description": f"Parameter {j} for endpoint {i}"
                            }
                            for j in range(5)
                        ],
                        "responses": {
                            "200": {
                                "description": f"Success response for endpoint {i}",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                f"field_{j}": {
                                                    "type": "string",
                                                    "description": f"Field {j} in response {i}"
                                                }
                                                for j in range(10)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                for i in range(50)  # 50 endpoints
            }
        }
        
        # Step 1: Create API
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Large Schema API",
                "base_url": "https://large.example.com",
                "description": "API with large schema"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Store large schema
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (large_schema, "https://large.example.com/schema.json")
            mock_pdf.return_value = b"large_pdf_content"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
        
        # Step 3: Retrieve and verify large schema integrity
        latest_response = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        latest_data = latest_response.json()
        retrieved_schema = latest_data["schema"]["schema_json"]
        
        # Verify key structure is preserved
        assert retrieved_schema["openapi"] == large_schema["openapi"]
        assert len(retrieved_schema["paths"]) == len(large_schema["paths"])
        
        # Verify specific endpoint structure
        for endpoint_path in large_schema["paths"]:
            assert endpoint_path in retrieved_schema["paths"]
            original_endpoint = large_schema["paths"][endpoint_path]["get"]
            retrieved_endpoint = retrieved_schema["paths"][endpoint_path]["get"]
            
            assert original_endpoint["summary"] == retrieved_endpoint["summary"]
            assert len(original_endpoint["parameters"]) == len(retrieved_endpoint["parameters"])
