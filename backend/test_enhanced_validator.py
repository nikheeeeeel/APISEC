#!/usr/bin/env python3
"""
Test script for the enhanced runtime validator with parameter handling.
"""

import asyncio
import json
from runtime_validator import create_runtime_validator


async def test_petstore_api():
    """Test the enhanced runtime validator with Petstore API."""
    
    # Petstore API schema
    petstore_schema = {
        "swagger": "2.0",
        "info": {"title": "Swagger Petstore", "version": "1.0.0"},
        "host": "petstore.swagger.io",
        "basePath": "/v2",
        "schemes": ["https"],
        "paths": {
            "/pet": {
                "post": {
                    "tags": ["pet"],
                    "summary": "Add a new pet to the store",
                    "description": "",
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
            "/pet/findByStatus": {
                "get": {
                    "tags": ["pet"],
                    "summary": "Finds Pets by status",
                    "description": "Multiple status values can be provided with comma separated strings",
                    "operationId": "findPetsByStatus",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "description": "Status values that need to be considered for filter",
                            "required": True,
                            "type": "string",
                            "enum": ["available", "pending", "sold"]
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "successful operation",
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/definitions/Pet"}
                            }
                        },
                        "400": {"description": "Invalid status value"}
                    }
                }
            },
            "/pet/{petId}": {
                "get": {
                    "tags": ["pet"],
                    "summary": "Find pet by ID",
                    "description": "Returns a single pet",
                    "operationId": "getPetById",
                    "produces": ["application/json"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "description": "ID of pet to return",
                            "required": True,
                            "type": "integer",
                            "format": "int64",
                            "minimum": 1,
                            "maximum": 10
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
            },
            "/store/inventory": {
                "get": {
                    "tags": ["store"],
                    "summary": "Returns pet inventories by status",
                    "description": "Returns a map of status codes to quantities",
                    "operationId": "getInventory",
                    "produces": ["application/json"],
                    "parameters": [],
                    "responses": {
                        "200": {
                            "description": "successful operation",
                            "schema": {
                                "type": "object",
                                "additionalProperties": {"type": "integer", "format": "int32"}
                            }
                        }
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
    
    base_url = "https://petstore.swagger.io/v2"
    
    print(f"Testing enhanced runtime validator with {base_url}")
    print("=" * 60)
    
    try:
        # Create validator
        validator = create_runtime_validator(timeout=15, max_concurrent=3)
        
        # Run validation
        result = await validator.validate_schema(base_url, petstore_schema)
        
        # Print results
        print(f"Base URL: {result.base_url}")
        print(f"Total endpoints: {result.total_endpoints}")
        print(f"Tested endpoints: {result.tested_endpoints}")
        print(f"Passed endpoints: {result.passed_endpoints}")
        print(f"Failed endpoints: {result.failed_endpoints}")
        print(f"Overall status: {result.overall_status}")
        print(f"Validation timestamp: {result.validation_timestamp}")
        
        print("\nEndpoint Test Results:")
        print("-" * 40)
        
        for i, test in enumerate(result.endpoint_tests, 1):
            print(f"{i}. {test.method} {test.path}")
            print(f"   URL: {test.url}")
            print(f"   Expected status: {test.expected_status}")
            print(f"   Actual status: {test.actual_status}")
            if test.response_time_ms:
                print(f"   Response time: {test.response_time_ms:.2f}ms")
            print(f"   Status mismatch: {test.status_mismatch}")
            print(f"   Schema mismatch: {test.schema_mismatch}")
            print(f"   Validation passed: {test.validation_passed}")
            
            if test.error:
                print(f"   Error: {test.error}")
            
            print()
        
        print("Enhanced validation completed!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_petstore_api())
