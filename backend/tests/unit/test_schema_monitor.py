#!/usr/bin/env python3
"""
Unit tests for schema monitoring functionality.
"""

import pytest
import json
from unittest.mock import patch, Mock, mock_open
import tempfile
from pathlib import Path

# Import the modules we're testing
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from schema_monitor import (
    crawl_for_schema,
    normalize_schema,
    extract_endpoint_signature,
    compare_endpoint_signatures,
    generate_pdf_from_json
)


@pytest.mark.unit
class TestSchemaCrawling:
    """Test schema crawling functionality."""
    
    @patch('schema_monitor.requests.get')
    def test_crawl_for_schema_openapi_success(self, mock_get, sample_openapi_schema):
        """Test successful OpenAPI schema discovery."""
        # Mock the response for the base URL
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><link rel="alternate" href="/openapi.json" type="application/json"></link></head>
        </html>
        """
        mock_response.json.return_value = sample_openapi_schema
        
        mock_get.side_effect = [mock_response, mock_response]
        
        result = crawl_for_schema("https://api.example.com")
        
        assert result is not None
        schema, schema_url = result
        assert schema == sample_openapi_schema
        assert schema_url == "https://api.example.com/openapi.json"
        assert mock_get.call_count == 2
    
    @patch('schema_monitor.requests.get')
    def test_crawl_for_schema_swagger_success(self, mock_get, sample_swagger_schema):
        """Test successful Swagger schema discovery."""
        # Mock the response for the base URL
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><link rel="alternate" href="/swagger.json" type="application/json"></link></head>
        </html>
        """
        mock_response.json.return_value = sample_swagger_schema
        
        mock_get.side_effect = [mock_response, mock_response]
        
        result = crawl_for_schema("https://api.example.com")
        
        assert result is not None
        schema, schema_url = result
        assert schema == sample_swagger_schema
        assert schema_url == "https://api.example.com/swagger.json"
    
    @patch('schema_monitor.requests.get')
    def test_crawl_for_schema_direct_json(self, mock_get, sample_openapi_schema):
        """Test direct JSON schema URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_openapi_schema
        
        mock_get.return_value = mock_response
        
        result = crawl_for_schema("https://api.example.com/openapi.json")
        
        assert result is not None
        schema, schema_url = result
        assert schema == sample_openapi_schema
        assert schema_url == "https://api.example.com/openapi.json"
    
    @patch('schema_monitor.requests.get')
    def test_crawl_for_schema_not_found(self, mock_get):
        """Test schema discovery when no schema is found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>No schema here</body></html>"
        
        mock_get.return_value = mock_response
        
        result = crawl_for_schema("https://api.example.com")
        
        assert result is None
    
    @patch('schema_monitor.requests.get')
    def test_crawl_for_schema_network_error(self, mock_get):
        """Test schema discovery with network error."""
        mock_get.side_effect = Exception("Network error")
        
        with pytest.raises(Exception):
            crawl_for_schema("https://api.example.com")
    
    @patch('schema_monitor.requests.get')
    def test_crawl_for_schema_invalid_json(self, mock_get):
        """Test schema discovery with invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        mock_get.return_value = mock_response
        
        result = crawl_for_schema("https://api.example.com/openapi.json")
        
        assert result is None


@pytest.mark.unit
class TestSchemaNormalization:
    """Test schema normalization functionality."""
    
    def test_normalize_openapi_schema(self, sample_openapi_schema):
        """Test OpenAPI schema normalization."""
        normalized = normalize_schema(sample_openapi_schema)
        
        # Check that essential structure is preserved
        assert "openapi" in normalized
        assert "info" in normalized
        assert "paths" in normalized
        
        # Check that non-essential fields are removed
        assert "description" not in normalized["info"]
        
        # Check that paths are normalized
        assert "/users" in normalized["paths"]
        assert "get" in normalized["paths"]["/users"]
    
    def test_normalize_swagger_schema(self, sample_swagger_schema):
        """Test Swagger schema normalization."""
        normalized = normalize_schema(sample_swagger_schema)
        
        # Check that essential structure is preserved
        assert "swagger" in normalized
        assert "info" in normalized
        assert "paths" in normalized
        
        # Check that non-essential fields are removed
        assert "description" not in normalized["info"]
        
        # Check that paths are normalized
        assert "/pet" in normalized["paths"]
        assert "post" in normalized["paths"]["/pet"]
    
    def test_normalize_schema_key_sorting(self):
        """Test that dictionary keys are sorted deterministically."""
        unsorted_schema = {
            "z_field": "last",
            "a_field": "first", 
            "m_field": "middle",
            "paths": {
                "z_path": {"get": {"summary": "Z path"}},
                "a_path": {"get": {"summary": "A path"}}
            }
        }
        
        normalized = normalize_schema(unsorted_schema)
        keys = list(normalized.keys())
        
        # Keys should be in alphabetical order
        assert keys[0] == 'a_field'
        assert keys[1] == 'm_field'
        assert keys[2] == 'paths'
        assert keys[3] == 'z_field'
    
    def test_normalize_schema_filter_non_contract_fields(self):
        """Test removal of non-contract fields."""
        schema_with_docs = {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "description": "This should stay",
                "summary": "This should be removed",
                "termsOfService": "This should be removed"
            }
        }
        
        normalized = normalize_schema(schema_with_docs)
        info = normalized['info']
        
        # Contract fields should remain
        assert 'title' in info
        assert 'description' in info
        
        # Non-contract fields should be removed
        assert 'summary' not in info
        assert 'termsOfService' not in info


@pytest.mark.unit
class TestEndpointSignatureExtraction:
    """Test endpoint signature extraction functionality."""
    
    def test_extract_openapi_signature(self, sample_openapi_schema):
        """Test extracting signature from OpenAPI schema."""
        signatures = extract_endpoint_signature(sample_openapi_schema)
        
        assert len(signatures) > 0
        
        # Check GET /users signature
        get_users_sig = next((s for s in signatures if s['method'] == 'GET' and s['path'] == '/users'), None)
        assert get_users_sig is not None
        assert get_users_sig['operationId'] is None or isinstance(get_users_sig['operationId'], str)
        assert 'parameters' in get_users_sig
        assert 'responses' in get_users_sig
    
    def test_extract_swagger_signature(self, sample_swagger_schema):
        """Test extracting signature from Swagger schema."""
        signatures = extract_endpoint_signature(sample_swagger_schema)
        
        assert len(signatures) > 0
        
        # Check POST /pet signature
        post_pet_sig = next((s for s in signatures if s['method'] == 'POST' and s['path'] == '/pet'), None)
        assert post_pet_sig is not None
        assert 'parameters' in post_pet_sig
        assert 'responses' in post_pet_sig
    
    def test_extract_signature_with_parameters(self, sample_swagger_schema):
        """Test extracting signature with parameters."""
        signatures = extract_endpoint_signature(sample_swagger_schema)
        
        # Check GET /pet/{petId} signature
        get_pet_sig = next((s for s in signatures if s['method'] == 'GET' and s['path'] == '/pet/{petId}'), None)
        assert get_pet_sig is not None
        assert len(get_pet_sig['parameters']) > 0
        
        param = get_pet_sig['parameters'][0]
        assert param['name'] == 'petId'
        assert param['in'] == 'path'
        assert param['required'] is True


@pytest.mark.unit
class TestEndpointSignatureComparison:
    """Test endpoint signature comparison functionality."""
    
    def test_compare_identical_signatures(self, sample_openapi_schema):
        """Test comparing identical endpoint signatures."""
        signatures = extract_endpoint_signature(sample_openapi_schema)
        
        if signatures:
            sig1 = signatures[0]
            sig2 = signatures.copy()[0]  # Make a copy
            
            result = compare_endpoint_signatures(sig1, sig2)
            
            assert result['identical'] is True
            assert len(result['differences']) == 0
    
    def test_compare_different_signatures(self, sample_openapi_schema):
        """Test comparing different endpoint signatures."""
        signatures = extract_endpoint_signature(sample_openapi_schema)
        
        if len(signatures) >= 2:
            sig1 = signatures[0]
            sig2 = signatures[1]
            
            result = compare_endpoint_signatures(sig1, sig2)
            
            # Should detect differences
            assert result['identical'] is False
            assert len(result['differences']) > 0
    
    def test_compare_signature_parameter_changes(self):
        """Test comparing signatures with parameter changes."""
        sig1 = {
            'method': 'GET',
            'path': '/users',
            'parameters': [
                {'name': 'limit', 'in': 'query', 'required': False, 'type': 'integer'}
            ],
            'responses': {'200': {'description': 'Success'}}
        }
        
        sig2 = {
            'method': 'GET',
            'path': '/users',
            'parameters': [
                {'name': 'limit', 'in': 'query', 'required': True, 'type': 'integer'}
            ],
            'responses': {'200': {'description': 'Success'}}
        }
        
        result = compare_endpoint_signatures(sig1, sig2)
        
        assert result['identical'] is False
        assert any('required' in diff.get('details', '') for diff in result['differences'])


@pytest.mark.unit
class TestPDFGeneration:
    """Test PDF generation functionality."""
    
    def test_generate_pdf_from_json(self, sample_openapi_schema):
        """Test PDF generation from JSON schema."""
        with patch('schema_monitor.Canvas') as mock_canvas:
            mock_pdf = Mock()
            mock_canvas.return_value = mock_pdf
            
            result = generate_pdf_from_json(sample_openapi_schema)
            
            assert result is not None
            assert isinstance(result, bytes)
            mock_canvas.assert_called_once()
    
    def test_generate_pdf_with_empty_schema(self):
        """Test PDF generation with empty schema."""
        with patch('schema_monitor.Canvas') as mock_canvas:
            mock_pdf = Mock()
            mock_canvas.return_value = mock_pdf
            
            result = generate_pdf_from_json({})
            
            assert result is not None
            assert isinstance(result, bytes)
    
    def test_generate_pdf_error_handling(self, sample_openapi_schema):
        """Test PDF generation error handling."""
        with patch('schema_monitor.Canvas') as mock_canvas:
            mock_canvas.side_effect = Exception("PDF generation error")
            
            with pytest.raises(Exception):
                generate_pdf_from_json(sample_openapi_schema)


@pytest.mark.unit
class TestSchemaValidation:
    """Test schema validation functionality."""
    
    def test_validate_openapi_schema_structure(self, sample_openapi_schema):
        """Test OpenAPI schema structure validation."""
        # This is a basic validation test
        assert "openapi" in sample_openapi_schema
        assert "info" in sample_openapi_schema
        assert "paths" in sample_openapi_schema
        assert sample_openapi_schema["openapi"].startswith("3.0")
    
    def test_validate_swagger_schema_structure(self, sample_swagger_schema):
        """Test Swagger schema structure validation."""
        # This is a basic validation test
        assert "swagger" in sample_swagger_schema
        assert "info" in sample_swagger_schema
        assert "paths" in sample_swagger_schema
        assert sample_swagger_schema["swagger"].startswith("2.0")
    
    def test_validate_schema_with_missing_required_fields(self):
        """Test schema validation with missing required fields."""
        invalid_schema = {
            "openapi": "3.0.0",
            # Missing "info" and "paths"
        }
        
        # This should be handled gracefully by the normalization
        normalized = normalize_schema(invalid_schema)
        assert "openapi" in normalized
    
    def test_validate_schema_with_invalid_paths(self):
        """Test schema validation with invalid paths."""
        schema_with_invalid_paths = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "invalid-path": {  # Missing leading slash
                    "get": {
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        # Should handle gracefully
        normalized = normalize_schema(schema_with_invalid_paths)
        assert "paths" in normalized


@pytest.mark.unit
class TestSchemaDiffingUtilities:
    """Test utility functions for schema diffing."""
    
    def test_extract_components_from_openapi(self, sample_openapi_schema):
        """Test extracting components from OpenAPI schema."""
        components = sample_openapi_schema.get("components", {}).get("schemas", {})
        
        assert "User" in components
        assert "UserCreate" in components
        
        user_schema = components["User"]
        assert "properties" in user_schema
        assert "id" in user_schema["properties"]
    
    def test_extract_definitions_from_swagger(self, sample_swagger_schema):
        """Test extracting definitions from Swagger schema."""
        definitions = sample_swagger_schema.get("definitions", {})
        
        assert "Pet" in definitions
        assert "Category" in definitions
        assert "Tag" in definitions
        
        pet_schema = definitions["Pet"]
        assert "properties" in pet_schema
        assert "name" in pet_schema["properties"]
    
    def test_normalize_response_schemas(self, sample_openapi_schema):
        """Test normalization of response schemas."""
        normalized = normalize_schema(sample_openapi_schema)
        
        # Check that response schemas are properly handled
        users_path = normalized["paths"]["/users"]
        get_response = users_path["get"]["responses"]["200"]
        
        assert "content" in get_response
        assert "application/json" in get_response["content"]
        assert "schema" in get_response["content"]["application/json"]
    
    def test_normalize_parameter_schemas(self, sample_swagger_schema):
        """Test normalization of parameter schemas."""
        normalized = normalize_schema(sample_swagger_schema)
        
        # Check that parameter schemas are properly handled
        pet_path = normalized["paths"]["/pet/{petId}"]
        get_parameters = pet_path["get"]["parameters"]
        
        assert len(get_parameters) > 0
        param = get_parameters[0]
        assert "name" in param
        assert "in" in param
        assert "required" in param
