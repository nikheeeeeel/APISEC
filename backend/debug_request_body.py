#!/usr/bin/env python3
import sys
sys.path.append('.')
from runtime_validator import RuntimeValidator

def test_request_body_generation():
    """Test request body generation directly"""
    schema_info = {
        "swagger": "2.0",
        "paths": {
            "/pet": {
                "post": {
                    "parameters": [
                        {
                            "in": "body",
                            "name": "body",
                            "required": True,
                            "schema": {"$ref": "#/definitions/Pet"}
                        }
                    ]
                }
            }
        },
        "definitions": {
            "Pet": {
                "type": "object",
                "required": ["name", "photoUrls"],
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "photoUrls": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
    
    validator = RuntimeValidator()
    endpoints = validator._extract_endpoints_from_schema(schema_info)
    
    print(f"Found {len(endpoints)} endpoints")
    for endpoint in endpoints:
        print(f"\nEndpoint: {endpoint.method} {endpoint.path}")
        print(f"Request body: {endpoint.request_body}")
        print(f"Parameters: {endpoint.parameters}")

if __name__ == "__main__":
    test_request_body_generation()
