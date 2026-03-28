import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from schema_monitor import compare_schemas

base_schema = {
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
                                            "address": {
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

changes = compare_schemas(base_schema, new_schema)
nested_changes = [c for c in changes if 'address' in c['details']]

print(f"Total changes: {len(changes)}")
print(f"Nested changes count: {len(nested_changes)}")
for i, c in enumerate(nested_changes):
    print(f"Change {i}: {json.dumps(c, indent=2)}")

# Also print all changes to see if there's any bleed
print("\nAll changes:")
for i, c in enumerate(changes):
    print(f"Change {i}: {json.dumps(c, indent=2)}")
