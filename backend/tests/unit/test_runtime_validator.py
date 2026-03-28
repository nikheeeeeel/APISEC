#!/usr/bin/env python3
"""
Test script for the runtime validator module.
"""

import asyncio
import json
from runtime_validator import create_runtime_validator


async def test_runtime_validator():
    """Test the runtime validator with a sample schema."""
    
    # Sample schema for testing
    sample_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get users",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "users": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "name": {"type": "string"},
                                                        "email": {"type": "string"}
                                                    },
                                                    "required": ["id", "name"]
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create user",
                    "responses": {
                        "201": {
                            "description": "User created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "message": {"type": "string"}
                                        },
                                        "required": ["id"]
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/health": {
                "get": {
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"}
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
    
    # Test with a real API (JSONPlaceholder)
    base_url = "https://jsonplaceholder.typicode.com"
    
    print(f"Testing runtime validator with {base_url}")
    print("=" * 50)
    
    try:
        # Create validator
        validator = create_runtime_validator(timeout=10, max_concurrent=5)
        
        # Run validation
        result = await validator.validate_schema(base_url, sample_schema)
        
        # Print results
        print(f"Base URL: {result.base_url}")
        print(f"Total endpoints: {result.total_endpoints}")
        print(f"Tested endpoints: {result.tested_endpoints}")
        print(f"Passed endpoints: {result.passed_endpoints}")
        print(f"Failed endpoints: {result.failed_endpoints}")
        print(f"Overall status: {result.overall_status}")
        print(f"Validation timestamp: {result.validation_timestamp}")
        
        print("\nEndpoint Test Results:")
        print("-" * 30)
        
        for i, test in enumerate(result.endpoint_tests, 1):
            print(f"{i}. {test.method} {test.path}")
            print(f"   URL: {test.url}")
            print(f"   Expected status: {test.expected_status}")
            print(f"   Actual status: {test.actual_status}")
            print(f"   Response time: {test.response_time_ms:.2f}ms" if test.response_time_ms else "   Response time: N/A")
            print(f"   Status mismatch: {test.status_mismatch}")
            print(f"   Schema mismatch: {test.schema_mismatch}")
            print(f"   Validation passed: {test.validation_passed}")
            
            if test.error:
                print(f"   Error: {test.error}")
            
            if test.actual_response:
                # Truncate response for display
                response_str = json.dumps(test.actual_response, indent=2)
                if len(response_str) > 200:
                    response_str = response_str[:200] + "..."
                print(f"   Response: {response_str}")
            
            print()
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_runtime_validator())
