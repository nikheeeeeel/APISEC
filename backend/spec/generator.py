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
    
    # Extract adaptive inference metadata if available
    adaptive_meta = meta.get("adaptive_inference", {})
    endpoint_type = adaptive_meta.get("endpoint_classification", {}).get("endpoint_type", "json_crud")
    content_type = adaptive_meta.get("content_type_detection", {}).get("preferred_strategy", "json")
    
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
                "confidence_threshold": 0.5,
                "endpoint_type": endpoint_type,
                "content_type": content_type,
                "adaptive_inference": adaptive_meta
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
    
    # Group parameters by location and type
    query_params = []
    body_params = []
    path_params = []
    header_params = []
    file_params = []
    form_data_params = []
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
        elif param_location == "form_file":
            file_params.append(param_schema)
        elif param_location == "form_data":
            form_data_params.append(param_schema)
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
    
    # Handle different content types based on endpoint classification
    if endpoint_type == "upload" and (file_params or form_data_params):
        # Multipart form data for upload endpoints
        path_item[method]["requestBody"] = generate_multipart_schema(file_params, form_data_params)
    elif body_params:
        # Regular JSON body parameters
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

def generate_multipart_schema(file_params: List[Dict], metadata_params: List[Dict]) -> Dict[str, Any]:
    """
    Generate OpenAPI schema for multipart/form-data requests.
    
    Args:
        file_params: List of file parameters
        metadata_params: List of metadata parameters
        
    Returns:
        OpenAPI requestBody schema for multipart
    """
    print(f"📋 Generating multipart schema for {len(file_params)} files and {len(metadata_params)} metadata fields")
    
    # Build multipart schema
    multipart_schema = {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    }
    
    properties = multipart_schema["content"]["multipart/form-data"]["schema"]["properties"]
    required = multipart_schema["content"]["multipart/form-data"]["schema"]["required"]
    
    # Add file parameters
    for param in file_params:
        param_name = param["name"]
        properties[param_name] = {
            "type": "string",
            "format": "binary",
            "x-confidence": param.get("confidence", 0.0),
            "x-evidence-count": len(param.get("evidence", []))
        }
        
        # Add file type information if available
        if param.get("accepted_types"):
            properties[param_name]["x-accepted-types"] = param["accepted_types"]
        
        if param.get("required", False):
            required.append(param_name)
    
    # Add metadata parameters
    for param in metadata_params:
        param_name = param["name"]
        properties[param_name] = _build_property_schema(param)
        
        if param.get("required", False):
            required.append(param_name)
    
    return multipart_schema

def infer_nested_structure(parameters: List[Dict]) -> Dict[str, Any]:
    """
    Infer nested object structures from flat parameter lists.
    
    Args:
        parameters: List of parameter dictionaries
        
    Returns:
        Nested structure dictionary
    """
    print("🔍 Inferring nested object structure...")
    
    nested_structure = {}
    
    # Look for patterns that suggest nesting
    for param in parameters:
        param_name = param["name"]
        
        # Check for dot notation (e.g., "user.name", "address.city")
        if "." in param_name:
            parts = param_name.split(".")
            current = nested_structure
            
            # Navigate/create nested structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {"type": "object", "properties": {}}
                current = current[part]["properties"]
            
            # Add the final property
            current[parts[-1]] = _build_property_schema(param)
        else:
            # Add to root level
            nested_structure[param_name] = _build_property_schema(param)
    
    return nested_structure

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
