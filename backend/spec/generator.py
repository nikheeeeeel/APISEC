from typing import Dict, Any, List

def generate_spec(inference_result: dict) -> dict:
    """
    Generate synthetic OpenAPI 3.0 spec from inference results.
    
    Args:
        inference_result: Output from orchestrator inference
        
    Returns:
        OpenAPI 3.0 compatible Python dict
    """
    # Extract URL and method
    url = inference_result.get("url", "")
    method = inference_result.get("method", "POST").lower()
    parameters = inference_result.get("parameters", [])
    meta = inference_result.get("meta", {})
    
    # Extract path from URL
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    path = parsed_url.path or "/"
    
    # Build OpenAPI structure
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Inferred API Spec",
            "version": "0.1.0",
            "description": "Generated via automated parameter inference",
            "x-inference-meta": {
                "total_parameters": meta.get("total_parameters", 0),
                "partial_failures": meta.get("partial_failures", 0),
                "execution_time_ms": meta.get("execution_time_ms", 0),
                "confidence_threshold": 0.5
            }
        },
        "servers": [
            {
                "url": f"{parsed_url.scheme}://{parsed_url.netloc}",
                "description": "Inferred API server"
            }
        ],
        "paths": {}
    }
    
    # Group parameters by location
    query_params = []
    body_params = []
    path_params = []
    header_params = []
    unknown_params = []
    
    for param in parameters:
        param_name = param.get("name", "")
        param_location = param.get("location", "unknown")
        param_confidence = param.get("confidence", 0.0)
        param_required = param.get("required", False)
        param_type = param.get("type", "unknown")
        param_nullable = param.get("nullable", False)
        evidence_count = len(param.get("evidence", []))
        
        # Build parameter schema
        param_schema = {
            "name": param_name,
            "x-confidence": param_confidence,
            "x-evidence-count": evidence_count
        }
        
        # Add type information
        if param_type != "unknown":
            param_schema["type"] = param_type
        else:
            param_schema["type"] = "string"  # Default to string for unknown types
        
        # Add nullable information
        if param_nullable:
            param_schema["nullable"] = True
        
        # Add required information
        if param_required:
            param_schema["required"] = True
        
        # Add location-specific information
        if param_location == "query":
            param_schema["in"] = "query"
            query_params.append(param_schema)
        elif param_location == "body":
            body_params.append(param_schema)
        elif param_location == "path":
            param_schema["in"] = "path"
            path_params.append(param_schema)
        elif param_location == "header":
            param_schema["in"] = "header"
            header_params.append(param_schema)
        else:
            param_schema["x-location"] = "unknown"
            unknown_params.append(param_schema)
    
    # Build path item
    path_item = {
        method: {
            "summary": f"Inferred {method.upper()} endpoint",
            "description": f"Endpoint discovered via automated parameter inference",
            "parameters": [],
            "responses": {
                "200": {
                    "description": "Success (inferred)",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    }
                },
                "422": {
                    "description": "Validation error (inferred)",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Add parameters to path item
    all_params = query_params + path_params + header_params
    
    # Handle body parameters separately
    if body_params:
        if len(body_params) == 1:
            # Single body parameter
            path_item[method]["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                body_params[0]["name"]: _build_property_schema(body_params[0])
                            },
                            "required": [p["name"] for p in body_params if p.get("required", False)]
                        }
                    }
                }
            }
        else:
            # Multiple body parameters
            path_item[method]["requestBody"] = {
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                p["name"]: _build_property_schema(p) for p in body_params
                            },
                            "required": [p["name"] for p in body_params if p.get("required", False)]
                        }
                    }
                }
            }
    
    # Add other parameters
    if all_params:
        path_item[method]["parameters"].extend(all_params)
    
    # Add unknown parameters with special handling
    for param in unknown_params:
        param_copy = param.copy()
        param_copy["x-location"] = "unknown"
        path_item[method]["parameters"].append(param_copy)
    
    # Add to paths
    spec["paths"][path] = path_item
    
    return spec

def _build_property_schema(param: dict) -> dict:
    """Build OpenAPI property schema from parameter info."""
    schema = {
        "type": param.get("type", "string"),
        "x-confidence": param.get("confidence", 0.0),
        "x-evidence-count": len(param.get("evidence", []))
    }
    
    if param.get("nullable", False):
        schema["nullable"] = True
    
    return schema
