import requests
import json
import re
from typing import Dict, List, Any
from urllib.parse import urlencode, urlparse

def infer_parameters(url: str, method: str = "POST", max_rounds: int = 5, content_type: str = "application/json") -> Dict[str, Dict[str, Any]]:
    """
    Infer API parameters by analyzing error responses to malformed requests.
    
    Args:
        url: Target API endpoint
        method: HTTP method to test (default: POST)
        max_rounds: Maximum number of inference rounds
        content_type: Content type for requests (application/json, multipart/form-data, etc.)
        
    Returns:
        Dictionary of discovered parameters with metadata
    """
    discovered_params = {}
    tested_params = set()
    round_num = 1
    
    print(f"Starting error-based parameter inference for {url}")
    print(f"Method: {method}, Max rounds: {max_rounds}, Content-Type: {content_type}")
    
    while round_num <= max_rounds:
        print(f"\n--- Round {round_num} ---")
        new_params_found = False
        
        # Test with current parameter set
        if not discovered_params:
            # First round: test with empty payload
            response = _send_probe_request(url, method, {}, content_type)
            new_params = _extract_params_from_error(response, tested_params, content_type)
        else:
            # Subsequent rounds: test with discovered parameters
            payload = {name: "test_value" for name in discovered_params.keys()}
            response = _send_probe_request(url, method, payload, content_type)
            new_params = _extract_params_from_error(response, tested_params, content_type)
        
        # Add newly discovered parameters
        for param_name, param_info in new_params.items():
            if param_name not in discovered_params:
                discovered_params[param_name] = param_info
                tested_params.add(param_name)
                new_params_found = True
                print(f"✓ New parameter: {param_name} (confidence: {param_info['confidence']:.2f})")
        
        if not new_params_found:
            print(f"No new parameters discovered in round {round_num}")
            if round_num > 2:  # Stop after 2 consecutive rounds with no new params
                print("Stopping inference - no new parameters found")
                break
        else:
            print(f"Round {round_num} completed. Total parameters: {len(discovered_params)}")
        
        round_num += 1
    
    print(f"\nInference complete. Discovered {len(discovered_params)} parameters.")
    return discovered_params

def _send_probe_request(url: str, method: str, payload: Dict[str, str], content_type: str = "application/json") -> requests.Response:
    """
    Send a probe request to the target endpoint.
    """
    try:
        if method.upper() == "GET":
            # For GET, add parameters to URL
            parsed_url = urlparse(url)
            query_params = {**dict(q.split('=') for q in parsed_url.query.split('&') if '=' in q), **payload}
            new_query = urlencode(query_params)
            probe_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
            response = requests.get(probe_url, timeout=10, headers={'Content-Type': content_type})
        else:
            # For POST, send based on content type
            if content_type == "multipart/form-data":
                # Handle multipart form data
                files = {}
                data = {}
                
                for key, value in payload.items():
                    # Simple heuristic: if value looks like a file path or has file-like name, treat as file
                    if any(file_indicator in key.lower() for file_indicator in ['file', 'upload', 'image', 'document']):
                        # Create a small test file
                        files[key] = (f"{key}.txt", value, "text/plain")
                    else:
                        data[key] = value
                
                response = requests.post(url, data=data, files=files, timeout=10)
            elif content_type == "application/x-www-form-urlencoded":
                response = requests.post(url, data=payload, timeout=10, headers={'Content-Type': content_type})
            else:
                # Default to JSON
                response = requests.post(url, json=payload, timeout=10, headers={'Content-Type': content_type})
        
        return response
    except Exception as e:
        # Return a mock response for connection errors
        class MockResponse:
            def __init__(self):
                self.status_code = 0
                self.text = f"Connection error: {str(e)}"
                self.content = self.text.encode()
        return MockResponse()

def _extract_params_from_error(response: requests.Response, tested_params: set, content_type: str = "application/json") -> Dict[str, Dict[str, Any]]:
    """
    Extract parameter names from error response using regex patterns.
    """
    new_params = {}
    error_text = response.text
    status_code = response.status_code
    
    # Choose patterns based on content type
    if content_type == "multipart/form-data":
        patterns = _get_multipart_patterns()
    elif content_type == "application/x-www-form-urlencoded":
        patterns = _get_form_patterns()
    else:
        patterns = _get_json_patterns()
    
    # Common non-parameter words to filter out
    NON_PARAM_WORDS = {
        'error', 'message', 'status', 'code', 'type', 'detail', 'success', 'failed',
        'field', 'required', 'missing', 'invalid', 'parameter', 'is', 'not', 'in',
        'loc', 'input', 'form', 'data', 'payload', 'body', 'get', 'post'
    }
    
    # Extract parameters using regex patterns
    for pattern in patterns:
        matches = re.finditer(pattern, error_text, re.IGNORECASE)
        for match in matches:
            param_name = match.group(1)
            
            # Skip if already tested or if it's a common non-parameter word
            if (param_name.lower() in tested_params or 
                param_name.lower() in NON_PARAM_WORDS):
                continue
            
            # Calculate confidence based on pattern specificity and error type
            confidence = _calculate_confidence(pattern, error_text, status_code)
            
            # Store parameter info
            if param_name not in new_params or confidence > new_params[param_name]['confidence']:
                new_params[param_name] = {
                    "required": _is_required_param(error_text, param_name),
                    "evidence": [
                        {
                            "error_text": error_text[:200] + "..." if len(error_text) > 200 else error_text,
                            "status_code": status_code,
                            "pattern": pattern,
                            "content_type": content_type
                        }
                    ],
                    "confidence": confidence,
                    "location": _infer_location_from_content_type(content_type, param_name)
                }
    
    return new_params

def _get_multipart_patterns() -> List[str]:
    """Get error patterns specific to multipart/form-data."""
    return [
        # File field patterns
        r'"([^"]+)"\s*:\s*["\']?required["\']?.*file',
        r'file\s+field\s*["\']?([^"\']+)["\']?\s+is\s+required',
        r'no\s+file\s+uploaded\s+for\s+["\']?([^"\']+)["\']?',
        
        # Metadata field patterns
        r'"([^"]+)"\s*:\s*["\']?required["\']?.*metadata',
        r'metadata\s+field\s*["\']?([^"\']+)["\']?\s+is\s+required',
        r'"([^"]+)"\s*:\s*["\']?missing["\']?.*upload',
        
        # General multipart patterns
        r'multipart\s+field\s*["\']?([^"\']+)["\']?',
        r'form\s+field\s*["\']?([^"\']+)["\']?\s+is\s+required',
        r'"([^"]+)"\s*:\s*["\']?not provided["\']?.*form',
        
        # Wiki.js specific patterns
        r'folderId\s+is\s+required',
        r'folderId\s+parameter\s+missing',
        r'upload\s+folder\s+not\s+specified',
        
        # Generic patterns (fallback)
        r'"(\w+)"\s*:\s*["\']?required["\']?',
        r'(\w+)\s+(?:parameter|field)\s+(?:is\s+)?(?:required|missing|invalid)',
    ]

def _get_form_patterns() -> List[str]:
    """Get error patterns specific to application/x-www-form-urlencoded."""
    return [
        # Form field patterns
        r'form\s+field\s*["\']?([^"\']+)["\']?\s+is\s+required',
        r'"([^"]+)"\s*:\s*["\']?required["\']?.*form',
        r'(\w+)\s+(?:parameter|field)\s+(?:is\s+)?(?:required|missing|invalid)',
        
        # URL-encoded specific
        r'url\s+parameter\s*["\']?([^"\']+)["\']?',
        r'form\s+parameter\s*["\']?([^"\']+)["\']?',
        
        # Generic patterns
        r'"(\w+)"\s*:\s*["\']?required["\']?',
        r'"(\w+)"\s*:\s*["\']?missing["\']?',
    ]

def _get_json_patterns() -> List[str]:
    """Get error patterns specific to JSON."""
    return [
        # FastAPI/Pydantic specific patterns
        r'"loc"\s*:\s*\["[^"]*",\s*"([^"]+)"\]',  # "loc": ["body","param_name"]
        r'"(\w+)"\s*:\s*["\']?required["\']?',  # "param_name": required
        r'"(\w+)"\s*:\s*["\']?missing["\']?',   # "param_name": missing
        r'"(\w+)"\s*:\s*["\']?invalid["\']?',   # "param_name": invalid
        r'"(\w+)"\s*:\s*["\']?not provided["\']?',  # "param_name": not provided
        r'"(\w+)"\s*:\s*["\']?undefined["\']?',  # "param_name": undefined
        r'"(\w+)"\s*:\s*["\']?null["\']?',     # "param_name": null
        
        # Form validation errors
        r'parameter\s*["\']?(\w+)["\']?\s+is\s+(?:required|missing|invalid)',
        r'(\w+)\s+(?:parameter|field)\s+(?:is\s+)?(?:required|missing|invalid)',
        r'(\w+)\s+(?:is\s+)?(?:required|missing|invalid)',
        
        # SQL and database errors
        r'column\s*["\']?(\w+)["\']?\s+not\s+found',
        r'unknown\s+column\s*["\']?(\w+)["\']?',
        r'field\s*["\']?(\w+)["\']?\s+doesn\'t\s+exist',
        
        # Python/Flask errors
        r'KeyError\s*["\']?(\w+)["\']?',
        r'(\w+)\s+not\s+in\s+(?:form|data|payload)',
        
        # Generic parameter references
        r'parameter\s*["\']?(\w+)["\']?',
        r'field\s*["\']?(\w+)["\']?',
        r'(\w+)\s+parameter',
        r'(\w+)\s+field',
        
        # URL/query parameter errors
        r'query\s+parameter\s*["\']?(\w+)["\']?',
        r'GET\s+parameter\s*["\']?(\w+)["\']?',
    ]

def _infer_location_from_content_type(content_type: str, param_name: str) -> str:
    """Infer parameter location based on content type and parameter name."""
    if content_type == "multipart/form-data":
        if any(file_indicator in param_name.lower() for file_indicator in ['file', 'upload', 'image', 'document']):
            return "form_file"
        else:
            return "form_data"
    elif content_type == "application/x-www-form-urlencoded":
        return "form_data"
    else:
        return "body"  # Default for JSON

def _calculate_confidence(pattern: str, error_text: str, status_code: int) -> float:
    """
    Calculate confidence score for a discovered parameter.
    """
    base_confidence = 0.5
    
    # Higher confidence for specific error patterns
    if 'required' in pattern.lower() or 'missing' in pattern.lower():
        base_confidence += 0.3
    elif 'invalid' in pattern.lower():
        base_confidence += 0.2
    
    # Higher confidence for JSON structure errors
    if '"' in pattern and ':' in pattern:
        base_confidence += 0.1
    
    # Higher confidence for client errors (4xx)
    if 400 <= status_code < 500:
        base_confidence += 0.1
    
    # Adjust based on error text specificity
    if len(error_text) < 100:  # Short, specific errors
        base_confidence += 0.1
    elif len(error_text) > 500:  # Long, generic errors
        base_confidence -= 0.1
    
    return min(1.0, max(0.1, base_confidence))

def _is_required_param(error_text: str, param_name: str) -> bool:
    """
    Determine if a parameter is required based on error message.
    """
    required_indicators = [
        'required',
        'missing',
        'not provided',
        'undefined',
        'null',
        'not found',
        "doesn't exist"
    ]
    
    error_lower = error_text.lower()
    param_lower = param_name.lower()
    
    # Check if error text indicates this parameter is required
    for indicator in required_indicators:
        if indicator in error_lower and param_lower in error_lower:
            return True
    
    return False

# Test function for development
if __name__ == "__main__":
    # Test with a local endpoint
    test_url = "http://127.0.0.1:8001/api/test"
    result = infer_parameters(test_url, "POST", 3)
    print("\n" + "="*50)
    print("INFERENCE RESULTS:")
    print(json.dumps(result, indent=2))
