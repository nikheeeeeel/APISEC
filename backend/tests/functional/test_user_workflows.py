#!/usr/bin/env python3
"""
Functional tests for complete user workflows.
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


@pytest.mark.functional
@pytest.mark.database
class TestNewUserOnboardingWorkflow:
    """Test the complete workflow for a new user onboarding."""
    
    def test_new_user_complete_journey(self, test_client, test_database, sample_openapi_schema):
        """Test a new user's complete journey from signup to API monitoring."""
        
        # Step 1: User visits the application - health check
        health_response = test_client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}
        
        # Step 2: User discovers their first API
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.return_value = (sample_openapi_schema, "https://myapi.com/openapi.json")
            
            discovery_response = test_client.post(
                "/discover-schema",
                json={"url": "https://myapi.com"}
            )
            assert discovery_response.status_code == 200
            discovery_data = discovery_response.json()
            assert discovery_data["status"] == "success"
            assert discovery_data["schema"] == sample_openapi_schema
        
        # Step 3: User decides to monitor this API - creates it in registry
        api_create_response = test_client.post(
            "/api/apis",
            data={
                "name": "My First API",
                "base_url": "https://myapi.com",
                "description": "My first API that I want to monitor"
            }
        )
        assert api_create_response.status_code == 200
        api_data = api_create_response.json()
        assert api_data["status"] == "success"
        api_id = api_data["api"]["id"]
        
        # Step 4: User performs initial scan of the API
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://myapi.com/openapi.json")
            mock_pdf.return_value = b"initial_schema_pdf"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
            scan_data = scan_response.json()
            assert scan_data["status"] == "success"
            assert "New schema version stored" in scan_data["message"]
        
        # Step 5: User views their API dashboard
        apis_response = test_client.get("/api/apis")
        assert apis_response.status_code == 200
        apis_data = apis_response.json()
        assert len(apis_data["apis"]) == 1
        assert apis_data["apis"][0]["name"] == "My First API"
        
        # Step 6: User views schema details
        schemas_response = test_client.get(f"/api/apis/{api_id}/schemas")
        assert schemas_response.status_code == 200
        schemas_data = schemas_response.json()
        assert len(schemas_data["schemas"]) == 1
        
        # Step 7: User performs runtime validation
        with patch('main.create_runtime_validator') as mock_create:
            mock_result = Mock()
            mock_result.base_url = "https://myapi.com"
            mock_result.total_endpoints = len(sample_openapi_schema.get("paths", {}))
            mock_result.tested_endpoints = mock_result.total_endpoints
            mock_result.passed_endpoints = mock_result.total_endpoints - 1
            mock_result.failed_endpoints = 1
            mock_result.overall_status = "partial_success"
            mock_result.validation_timestamp = "2024-01-01T00:00:00Z"
            
            # Create mock endpoint test results
            mock_endpoint_test = Mock()
            mock_endpoint_test.method = "GET"
            mock_endpoint_test.path = "/users"
            mock_endpoint_test.url = "https://myapi.com/users"
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
            
            mock_validator = AsyncMock()
            mock_validator.validate_schema.return_value = mock_result
            mock_create.return_value = mock_validator
            
            validation_response = test_client.post(
                "/validate-runtime",
                json={
                    "base_url": "https://myapi.com",
                    "schema_info": sample_openapi_schema
                }
            )
            assert validation_response.status_code == 200
            validation_data = validation_response.json()
            assert validation_data["status"] == "success"
            assert validation_data["validation_result"]["overall_status"] == "partial_success"
        
        # Step 8: User checks the latest schema
        latest_response = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        assert latest_response.status_code == 200
        latest_data = latest_response.json()
        assert latest_data["schema"]["schema_json"] == sample_openapi_schema


@pytest.mark.functional
@pytest.mark.database
class TestApiEvolutionWorkflow:
    """Test workflow of API evolution and change detection."""
    
    def test_api_evolution_complete_workflow(self, test_client, test_database, 
                                           sample_openapi_schema, sample_swagger_schema):
        """Test the complete workflow of API evolution monitoring."""
        
        # Step 1: User creates an API for monitoring
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Evolving API",
                "base_url": "https://evolving.example.com",
                "description": "An API that evolves over time"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Initial schema scan (v1)
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://evolving.example.com/v1/openapi.json")
            mock_pdf.return_value = b"schema_v1_pdf"
            
            scan1_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan1_response.status_code == 200
            scan1_data = scan1_response.json()
            assert scan1_data["status"] == "success"
        
        # Step 3: User views initial state
        schemas_v1_response = test_client.get(f"/api/apis/{api_id}/schemas")
        schemas_v1_data = schemas_v1_response.json()
        assert len(schemas_v1_data["schemas"]) == 1
        v1_version = schemas_v1_data["schemas"][0]["version"]
        
        # Step 4: API evolves - new schema version (v2)
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_swagger_schema, "https://evolving.example.com/v2/swagger.json")
            mock_pdf.return_value = b"schema_v2_pdf"
            
            scan2_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan2_response.status_code == 200
            scan2_data = scan2_response.json()
            assert scan2_data["status"] == "success"
        
        # Step 5: User views updated state
        schemas_v2_response = test_client.get(f"/api/apis/{api_id}/schemas")
        schemas_v2_data = schemas_v2_response.json()
        assert len(schemas_v2_data["schemas"]) == 2
        
        # Step 6: User compares versions to see what changed
        compare_response = test_client.get(
            f"/api/schemas/{api_id}/compare/{v1_version}/2"
        )
        assert compare_response.status_code == 200
        compare_data = compare_response.json()
        assert compare_data["status"] == "success"
        assert "changes" in compare_data
        
        # Step 7: User gets structured comparison with summary
        structured_response = test_client.get(
            f"/api/schemas/{api_id}/compare/{v1_version}/2?structured=true"
        )
        assert structured_response.status_code == 200
        structured_data = structured_response.json()
        assert structured_data["status"] == "success"
        assert "summary" in structured_data
        assert "changes" in structured_data
        
        # Verify summary contains expected information
        summary = structured_data["summary"]
        assert "total_changes" in summary
        assert "breaking_changes" in summary
        assert "non_breaking_changes" in summary
        
        # Step 8: User validates the new version
        with patch('main.create_runtime_validator') as mock_create:
            mock_result = Mock()
            mock_result.base_url = "https://evolving.example.com"
            mock_result.total_endpoints = len(sample_swagger_schema.get("paths", {}))
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
                    "base_url": "https://evolving.example.com",
                    "schema_info": sample_swagger_schema
                }
            )
            assert validation_response.status_code == 200
            validation_data = validation_response.json()
            assert validation_data["status"] == "success"
            assert validation_data["validation_result"]["overall_status"] == "success"


@pytest.mark.functional
@pytest.mark.database
class TestApiManagementWorkflow:
    """Test API management workflows."""
    
    def test_complete_api_lifecycle(self, test_client, test_database, sample_openapi_schema):
        """Test the complete lifecycle of an API from creation to deletion."""
        
        # Step 1: Create multiple APIs
        api_ids = []
        for i in range(3):
            response = test_client.post(
                "/api/apis",
                data={
                    "name": f"Lifecycle Test API {i}",
                    "base_url": f"https://lifecycle{i}.example.com",
                    "description": f"API {i} for lifecycle testing"
                }
            )
            api_id = response.json()["api"]["id"]
            api_ids.append(api_id)
        
        # Step 2: Add schemas to all APIs
        for i, api_id in enumerate(api_ids):
            with patch('main.crawl_for_schema') as mock_crawl, \
                 patch('main.generate_pdf_from_json') as mock_pdf:
                
                mock_crawl.return_value = (sample_openapi_schema, f"https://lifecycle{i}.example.com/schema.json")
                mock_pdf.return_value = f"pdf_content_{i}".encode()
                
                scan_response = test_client.post(f"/api/apis/{api_id}/scan")
                assert scan_response.status_code == 200
        
        # Step 3: View all APIs
        all_apis_response = test_client.get("/api/apis")
        all_apis_data = all_apis_response.json()
        assert len(all_apis_data["apis"]) == 3
        
        # Step 4: Update one API
        update_response = test_client.post(
            "/api/apis",
            data={
                "name": "Updated Lifecycle Test API 1",
                "base_url": "https://lifecycle1.example.com",
                "description": "Updated description"
            }
        )
        # This should create a new API since we don't have an update endpoint
        
        # Step 5: Delete one API
        delete_response = test_client.delete(f"/api/apis/{api_ids[1]}")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["status"] == "success"
        
        # Step 6: Verify deletion
        remaining_apis_response = test_client.get("/api/apis")
        remaining_apis_data = remaining_apis_response.json()
        assert len(remaining_apis_data["apis"]) == 2
        
        # Step 7: Verify schemas for deleted API are also deleted
        deleted_schemas_response = test_client.get(f"/api/apis/{api_ids[1]}/schemas")
        deleted_schemas_data = deleted_schemas_response.json()
        assert deleted_schemas_data["schemas"] == []
        
        # Step 8: Delete remaining APIs
        for api_id in [api_ids[0], api_ids[2]]:
            delete_response = test_client.delete(f"/api/apis/{api_id}")
            assert delete_response.status_code == 200
        
        # Step 9: Verify all are deleted
        final_apis_response = test_client.get("/api/apis")
        final_apis_data = final_apis_response.json()
        assert len(final_apis_data["apis"]) == 0


@pytest.mark.functional
@pytest.mark.database
class TestErrorHandlingWorkflows:
    """Test error handling in user workflows."""
    
    def test_workflow_with_various_errors(self, test_client, test_database):
        """Test how workflows handle various error conditions."""
        
        # Step 1: Try to discover schema for non-existent URL
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.return_value = (None, None)
            
            discovery_response = test_client.post(
                "/discover-schema",
                json={"url": "https://nonexistent.example.com"}
            )
            assert discovery_response.status_code == 200
            discovery_data = discovery_response.json()
            assert discovery_data["status"] == "not_found"
        
        # Step 2: Create API successfully
        api_response = test_client.post(
            "/api/apis",
            data={
                "name": "Error Test API",
                "base_url": "https://errortest.example.com",
                "description": "API for testing error handling"
            }
        )
        api_id = api_response.json()["api"]["id"]
        
        # Step 3: Try to scan API with network error
        with patch('main.crawl_for_schema') as mock_crawl:
            mock_crawl.side_effect = Exception("Network timeout")
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 500
        
        # Step 4: Verify API still exists after failed scan
        api_check_response = test_client.get("/api/apis")
        api_check_data = api_check_response.json()
        assert len(api_check_data["apis"]) == 1
        assert api_check_data["apis"][0]["id"] == api_id
        
        # Step 5: Try to get schemas for API with no schemas
        schemas_response = test_client.get(f"/api/apis/{api_id}/schemas")
        schemas_data = schemas_response.json()
        assert schemas_data["schemas"] == []
        
        # Step 6: Try to get latest schema for API with no schemas
        latest_response = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        assert latest_response.status_code == 404
        
        # Step 7: Try to compare non-existent schema versions
        compare_response = test_client.get(f"/api/schemas/{api_id}/compare/1/2")
        assert compare_response.status_code == 404
        
        # Step 8: Try to delete non-existent API
        delete_response = test_client.delete("/api/apis/999")
        assert delete_response.status_code == 404
        
        # Step 9: Clean up - delete the test API
        delete_response = test_client.delete(f"/api/apis/{api_id}")
        assert delete_response.status_code == 200


@pytest.mark.functional
@pytest.mark.database
class TestConcurrentUserWorkflows:
    """Test concurrent user workflows."""
    
    def test_multiple_users_concurrent_operations(self, test_client, test_database, sample_openapi_schema):
        """Test multiple users performing operations concurrently."""
        import threading
        import time
        
        results = []
        errors = []
        
        def user_workflow(user_id):
            """Simulate a user workflow."""
            try:
                # Each user creates their own API
                api_response = test_client.post(
                    "/api/apis",
                    data={
                        "name": f"User {user_id} API",
                        "base_url": f"https://user{user_id}.example.com",
                        "description": f"API created by user {user_id}"
                    }
                )
                
                if api_response.status_code != 200:
                    errors.append(f"User {user_id}: API creation failed")
                    return
                
                api_id = api_response.json()["api"]["id"]
                
                # User scans their API
                with patch('main.crawl_for_schema') as mock_crawl, \
                     patch('main.generate_pdf_from_json') as mock_pdf:
                    
                    mock_crawl.return_value = (sample_openapi_schema, f"https://user{user_id}.example.com/schema.json")
                    mock_pdf.return_value = f"pdf_user_{user_id}".encode()
                    
                    scan_response = test_client.post(f"/api/apis/{api_id}/scan")
                    
                    if scan_response.status_code != 200:
                        errors.append(f"User {user_id}: Scan failed")
                        return
                
                # User views their API list
                apis_response = test_client.get("/api/apis")
                
                if apis_response.status_code != 200:
                    errors.append(f"User {user_id}: Get APIs failed")
                    return
                
                # User views their schemas
                schemas_response = test_client.get(f"/api/apis/{api_id}/schemas")
                
                if schemas_response.status_code != 200:
                    errors.append(f"User {user_id}: Get schemas failed")
                    return
                
                results.append(f"User {user_id}: Workflow completed successfully")
                
            except Exception as e:
                errors.append(f"User {user_id}: {str(e)}")
        
        # Start multiple user workflows concurrently
        threads = []
        for user_id in range(5):
            thread = threading.Thread(target=user_workflow, args=(user_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all workflows to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Concurrent workflow errors: {errors}"
        assert len(results) == 5
        
        # Verify all APIs were created
        final_apis_response = test_client.get("/api/apis")
        final_apis_data = final_apis_response.json()
        assert len(final_apis_data["apis"]) == 5


@pytest.mark.functional
@pytest.mark.database
class TestDataIntegrityWorkflows:
    """Test data integrity throughout user workflows."""
    
    def test_data_integrity_across_operations(self, test_client, test_database, sample_openapi_schema):
        """Test that data integrity is maintained across all operations."""
        
        # Step 1: Create API with specific data
        original_api_data = {
            "name": "Integrity Test API",
            "base_url": "https://integrity.example.com",
            "description": "API for testing data integrity with special chars: !@#$%^&*()"
        }
        
        api_response = test_client.post("/api/apis", data=original_api_data)
        api_id = api_response.json()["api"]["id"]
        
        # Step 2: Store complex schema
        complex_schema = {
            "openapi": "3.0.0",
            "info": {
                "title": "Complex API",
                "version": "1.0.0",
                "description": "API with complex data structures"
            },
            "paths": {
                "/complex": {
                    "get": {
                        "summary": "Get complex data",
                        "description": "Returns complex nested data",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "nested": {
                                                    "type": "object",
                                                    "properties": {
                                                        "array": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "unicode": {"type": "string", "example": "Hello 世界 🌍"},
                                                                    "special": {"type": "string", "example": "Special chars: !@#$%^&*()"}
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Step 3: Store the complex schema
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (complex_schema, "https://integrity.example.com/complex-schema.json")
            mock_pdf.return_value = b"complex_pdf_with_special_data_!@#$%"
            
            scan_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan_response.status_code == 200
        
        # Step 4: Retrieve and verify API data integrity
        apis_response = test_client.get("/api/apis")
        apis_data = apis_response.json()
        api = next(a for a in apis_data["apis"] if a["id"] == api_id)
        
        assert api["name"] == original_api_data["name"]
        assert api["base_url"] == original_api_data["base_url"]
        assert api["description"] == original_api_data["description"]
        
        # Step 5: Retrieve and verify schema data integrity
        latest_response = test_client.get(f"/api/apis/{api_id}/schemas/latest")
        latest_data = latest_response.json()
        retrieved_schema = latest_data["schema"]["schema_json"]
        
        assert retrieved_schema == complex_schema
        
        # Step 6: Verify specific complex data elements
        nested_path = retrieved_schema["paths"]["/complex"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        array_schema = nested_path["properties"]["nested"]["properties"]["array"]["items"]
        unicode_field = array_schema["properties"]["unicode"]
        special_field = array_schema["properties"]["special"]
        
        assert unicode_field["example"] == "Hello 世界 🌍"
        assert special_field["example"] == "Special chars: !@#$%^&*()"
        
        # Step 7: Add another schema version and verify both are preserved
        with patch('main.crawl_for_schema') as mock_crawl, \
             patch('main.generate_pdf_from_json') as mock_pdf:
            
            mock_crawl.return_value = (sample_openapi_schema, "https://integrity.example.com/v2-schema.json")
            mock_pdf.return_value = b"v2_pdf_content"
            
            scan2_response = test_client.post(f"/api/apis/{api_id}/scan")
            assert scan2_response.status_code == 200
        
        # Step 8: Verify both schema versions are preserved with integrity
        all_schemas_response = test_client.get(f"/api/apis/{api_id}/schemas")
        all_schemas_data = all_schemas_response.json()
        assert len(all_schemas_data["schemas"]) == 2
        
        # Verify v1 (complex schema) is still intact
        v1_schema = next(s for s in all_schemas_data["schemas"] if s["version"] == 1)
        assert v1_schema["schema_json"] == complex_schema
        
        # Verify v2 (simple schema) is stored correctly
        v2_schema = next(s for s in all_schemas_data["schemas"] if s["version"] == 2)
        assert v2_schema["schema_json"] == sample_openapi_schema
        
        # Step 9: Compare versions and verify comparison integrity
        compare_response = test_client.get(f"/api/schemas/{api_id}/compare/1/2")
        compare_data = compare_response.json()
        assert compare_data["status"] == "success"
        assert "changes" in compare_data
        assert len(compare_data["changes"]) > 0  # Should detect differences between complex and simple schemas
