"""Validation utilities."""
import json
from typing import Optional, Dict, Any


def validate_openapi_spec(spec: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate OpenAPI 3.x specification.
    
    Args:
        spec: OpenAPI specification dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(spec, dict):
        return False, "Specification must be a JSON object"
    
    # Check for required OpenAPI fields
    if "openapi" not in spec:
        return False, "Missing 'openapi' field"
    
    openapi_version = spec.get("openapi", "")
    if not openapi_version.startswith("3."):
        return False, f"Unsupported OpenAPI version: {openapi_version}. Requires 3.x"
    
    if "info" not in spec:
        return False, "Missing 'info' field"
    
    if "paths" not in spec:
        return False, "Missing 'paths' field"
    
    return True, None


def parse_json_safe(content: bytes) -> Optional[Dict[str, Any]]:
    """
    Safely parse JSON content.
    
    Args:
        content: Bytes content to parse
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        return json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
