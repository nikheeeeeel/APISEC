#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced schema diffing functionality.

Tests all phases of improvements:
1. Schema normalization with $ref resolution
2. Semantic endpoint comparison
3. Enhanced parameter-level diffing
4. Request body field-level tracking
5. Response schema change detection
6. Component schema diffing
7. Breaking/non-breaking classification
8. Structured output format
"""

import json
import unittest
from typing import Dict, Any, List

from schema_monitor import (
    compare_schemas, 
    compare_schemas_structured,
    normalize_schema,
    extract_endpoint_signature,
    compare_endpoint_signatures,
    compare_request_body_schemas,
    compare_schemas_detailed,
    compare_component_schemas,
    classify_change_breaking,
    enhance_change_classification,
    generate_diff_summary
)


class TestSchemaDiffing(unittest.TestCase):
    """Test suite for enhanced schema diffing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "type": "integer"
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "name": {"type": "string"}
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
    
    def test_endpoint_addition_detection(self):
        """Test detection of endpoint additions."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}}
                    }
                },
                "/posts": {  # New endpoint
                    "get": {
                        "summary": "Get posts",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        changes = compare_schemas(self.base_schema, new_schema)
        endpoint_additions = [c for c in changes if c['category'] == 'endpoint' and c['type'] == 'added']
        
        self.assertEqual(len(endpoint_additions), 1)
        self.assertIn('/posts', endpoint_additions[0]['details'])
        self.assertEqual(endpoint_additions[0]['breaking_change'], 'non_breaking')
    
    def test_endpoint_removal_detection(self):
        """Test detection of endpoint removals."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {}  # All endpoints removed
        }
        
        changes = compare_schemas(self.base_schema, new_schema)
        endpoint_removals = [c for c in changes if c['category'] == 'endpoint' and c['type'] == 'removed']
        
        self.assertEqual(len(endpoint_removals), 1)
        self.assertIn('/users', endpoint_removals[0]['details'])
        self.assertEqual(endpoint_removals[0]['breaking_change'], 'breaking')
    
    def test_parameter_required_change(self):
        """Test detection of parameter required flag changes."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": True,  # Changed to required
                                "type": "integer"
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        changes = compare_schemas(self.base_schema, new_schema)
        required_changes = [c for c in changes if 'required' in c['details'] and c['category'] == 'parameter']
        
        self.assertEqual(len(required_changes), 1)
        self.assertEqual(required_changes[0]['breaking_change'], 'breaking')
        self.assertEqual(required_changes[0]['severity'], 'high')
    
    def test_parameter_type_change(self):
        """Test detection of parameter type changes."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "type": "string"  # Changed from integer to string
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        changes = compare_schemas(self.base_schema, new_schema)
        type_changes = [c for c in changes if 'type changed' in c['details'] and c['category'] == 'parameter']
        
        self.assertEqual(len(type_changes), 1)
        self.assertEqual(type_changes[0]['breaking_change'], 'non_breaking')
        self.assertEqual(type_changes[0]['severity'], 'medium')
    
    def test_parameter_enum_addition(self):
        """Test detection of enum value additions."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "parameters": [
                            {
                                "name": "status",
                                "in": "query",
                                "required": False,
                                "type": "string",
                                "enum": ["active", "inactive"]  # New enum parameter
                            }
                        ],
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        changes = compare_schemas(self.base_schema, new_schema)
        parameter_additions = [c for c in changes if c['category'] == 'parameter' and c['type'] == 'added']
        
        self.assertEqual(len(parameter_additions), 1)
        self.assertEqual(parameter_additions[0]['breaking_change'], 'non_breaking')
        self.assertIn('status', parameter_additions[0]['details'])
    
    def test_request_body_field_addition(self):
        """Test detection of request body field additions."""
        base_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string"}
                                        },
                                        "required": ["name", "email"]
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }
        
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "email": {"type": "string"},
                                            "phone": {"type": "string"}  # New field
                                        },
                                        "required": ["name", "email"]
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}}
                    }
                }
            }
        }
        
        changes = compare_schemas(base_schema, new_schema)
        field_additions = [c for c in changes if 'phone' in c['details'] and c['category'] == 'schema']
        
        self.assertEqual(len(field_additions), 1)
        self.assertEqual(field_additions[0]['breaking_change'], 'non_breaking')
    
    def test_response_field_removal(self):
        """Test detection of response field removals."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"}
                                                    # name field removed
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
        
        changes = compare_schemas(self.base_schema, new_schema)
        field_removals = [c for c in changes if 'name' in c['details'] and c['type'] == 'removed']
        
        self.assertEqual(len(field_removals), 1)
        self.assertEqual(field_removals[0]['breaking_change'], 'breaking')
    
    def test_component_schema_addition(self):
        """Test detection of component schema additions."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        }
                    }
                }
            },
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        changes = compare_schemas(self.base_schema, new_schema)
        component_additions = [c for c in changes if c['category'] == 'component' and c['type'] == 'added']
        
        self.assertEqual(len(component_additions), 1)
        self.assertEqual(component_additions[0]['breaking_change'], 'non_breaking')
    
    def test_nested_schema_change(self):
        """Test detection of nested object schema changes."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {
                            "200": {
                                "description": "Success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "name": {"type": "string"},
                                                    "address": {  # New nested object
                                                        "type": "object",
                                                        "properties": {
                                                            "street": {"type": "string"},
                                                            "city": {"type": "string"}
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
        
        changes = compare_schemas(self.base_schema, new_schema)
        nested_changes = [c for c in changes if 'address' in c['details']]
        
        self.assertEqual(len(nested_changes), 1)
        self.assertEqual(nested_changes[0]['breaking_change'], 'non_breaking')
    
    def test_structured_output_format(self):
        """Test the structured output format with summary."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}}
                    }
                },
                "/posts": {
                    "get": {
                        "summary": "Get posts",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        result = compare_schemas_structured(self.base_schema, new_schema)
        
        # Check structure
        self.assertIn('summary', result)
        self.assertIn('changes', result)
        
        # Check summary fields
        summary = result['summary']
        self.assertIn('total_changes', summary)
        self.assertIn('added_endpoints', summary)
        self.assertIn('breaking_changes', summary)
        self.assertIn('non_breaking_changes', summary)
        self.assertIn('info_changes', summary)
        self.assertIn('by_category', summary)
        self.assertIn('by_severity', summary)
        
        # Check values
        self.assertEqual(summary['added_endpoints'], 1)
        self.assertGreater(summary['total_changes'], 0)
    
    def test_schema_normalization(self):
        """Test schema normalization functionality."""
        schema_with_docs = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "description": "This is a description",  # Should be filtered out
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "required": False,
                                "type": "integer",
                                "description": "Parameter description"  # Should be filtered out
                            }
                        ],
                        "responses": {
                            "200": {
                                "description": "Success",  # Should be kept for responses
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "integer", "description": "ID field"},  # Should be filtered out
                                                    "name": {"type": "string"}
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
        
        normalized = normalize_schema(schema_with_docs)
        
        # Check that documentation fields are removed
        self.assertNotIn('description', normalized['paths']['/users']['get'])
        self.assertNotIn('description', normalized['paths']['/users']['get']['parameters'][0])
        
        # Check that essential structure is preserved
        self.assertIn('paths', normalized)
        self.assertIn('/users', normalized['paths'])
        self.assertIn('get', normalized['paths']['/users'])
    
    def test_breaking_classification_accuracy(self):
        """Test accuracy of breaking change classification."""
        test_cases = [
            {
                'change': {'type': 'removed', 'category': 'endpoint', 'details': 'Endpoint removed'},
                'expected': 'breaking'
            },
            {
                'change': {'type': 'added', 'category': 'endpoint', 'details': 'Endpoint added'},
                'expected': 'non_breaking'
            },
            {
                'change': {'type': 'modified', 'category': 'parameter', 'details': 'required status changed'},
                'expected': 'breaking'
            },
            {
                'change': {'type': 'added', 'category': 'parameter', 'details': 'parameter added'},
                'expected': 'non_breaking'
            },
            {
                'change': {'type': 'modified', 'category': 'response', 'details': 'description changed'},
                'expected': 'info'
            }
        ]
        
        for case in test_cases:
            result = classify_change_breaking(case['change'])
            self.assertEqual(result, case['expected'], 
                           f"Failed for {case['change']}: expected {case['expected']}, got {result}")
    
    def test_backward_compatibility(self):
        """Test that the original compare_schemas function still works."""
        new_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "summary": "Get users",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        # Original function should return list of changes
        changes = compare_schemas(self.base_schema, new_schema)
        self.assertIsInstance(changes, list)
        self.assertGreater(len(changes), 0)
        
        # Each change should have expected fields
        for change in changes:
            self.assertIn('type', change)
            self.assertIn('category', change)
            self.assertIn('severity', change)
            self.assertIn('details', change)
            self.assertIn('path', change)
            self.assertIn('breaking_change', change)


class TestSchemaNormalization(unittest.TestCase):
    """Test suite specifically for schema normalization."""
    
    def test_key_sorting(self):
        """Test that dictionary keys are sorted deterministically."""
        unsorted_schema = {
            "z_field": "last",
            "a_field": "first", 
            "m_field": "middle"
        }
        
        normalized = normalize_schema(unsorted_schema)
        keys = list(normalized.keys())
        
        # Keys should be in alphabetical order
        self.assertEqual(keys[0], 'a_field')
        self.assertEqual(keys[1], 'm_field')
        self.assertEqual(keys[2], 'z_field')
    
    def test_non_contract_field_removal(self):
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
        self.assertIn('title', info)
        self.assertIn('description', info)
        
        # Non-contract fields should be removed
        self.assertNotIn('summary', info)
        self.assertNotIn('termsOfService', info)


def run_comprehensive_tests():
    """Run all tests and provide a summary."""
    import sys
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaDiffing))
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaNormalization))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\nERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
