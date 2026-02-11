import requests
import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List

def infer_parameter_location(
    url: str,
    method: str,
    param_name: str,
    timeout: int = 5
) -> Dict[str, Any]:
    """
    Infer parameter location (query, body, path, header) using safe, bounded testing.
    
    Args:
        url: Target API endpoint
        method: HTTP method
        param_name: Name of parameter to locate
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with location, confidence, and evidence
    """
    print(f"🔍 Inferring location for parameter: {param_name}")
    print(f"Target: {url}")
    print(f"Method: {method}")
    
    evidence = []
    location_confidence = {"query": 0.0, "body": 0.0, "path": 0.0, "header": 0.0}
    
    try:
        # Test 1: Query Parameter Test
        print(f"\n1️⃣ Testing query parameter...")
        query_result = _test_query_parameter(url, method, param_name, timeout)
        if query_result:
            evidence.append(query_result)
            if _explicit_query_reference(query_result.get("error_text", "")):
                location_confidence["query"] += 0.5
            else:
                location_confidence["query"] += 0.1
        
        # Test 2: Body Parameter Test
        print(f"2️⃣ Testing body parameter...")
        body_result = _test_body_parameter(url, method, param_name, timeout)
        if body_result:
            evidence.append(body_result)
            if _explicit_body_reference(body_result.get("error_text", "")):
                location_confidence["body"] += 0.5
            else:
                location_confidence["body"] += 0.1
        
        # Test 3: Path Parameter Heuristic (NO REQUEST MUTATION)
        print(f"3️⃣ Checking path parameter heuristic...")
        path_result = _check_path_parameter(url, param_name)
        if path_result:
            evidence.append(path_result)
            location_confidence["path"] = 0.9  # High confidence for path match
        
        # Test 4: Header Test (Very Conservative)
        print(f"4️⃣ Testing header parameter...")
        header_result = _test_header_parameter(url, method, param_name, timeout)
        if header_result:
            if _explicit_header_reference(header_result.get("error_text", "")):
                evidence.append(header_result)
                location_confidence["header"] += 0.6
            else:
                print(f"   Header test inconclusive, discarding")
        
        # Apply penalties for conflicting signals
        locations_with_evidence = [loc for loc, conf in location_confidence.items() if conf > 0]
        if len(locations_with_evidence) > 1:
            # Multiple locations have evidence - reduce confidence
            for loc in location_confidence:
                if location_confidence[loc] > 0:
                    location_confidence[loc] -= 0.3
        
        # Determine final location and confidence
        best_location = "unknown"
        best_confidence = 0.0
        
        for loc, conf in location_confidence.items():
            if conf > best_confidence:
                best_confidence = conf
                best_location = loc
        
        # Clamp confidence to valid range
        best_confidence = max(0.1, min(1.0, best_confidence))
        
        # Early stop if high confidence achieved
        if best_confidence > 0.7:
            print(f"   ✅ High confidence ({best_confidence:.2f}) achieved, stopping early")
        
        result = {
            "location": best_location,
            "confidence": best_confidence,
            "evidence": evidence
        }
        
        print(f"🎯 Location inference complete: {best_location} (confidence: {best_confidence:.2f})")
        return result
        
    except Exception as e:
        print(f"💥 Location inference failed: {e}")
        return {
            "location": "unknown",
            "confidence": 0.1,
            "evidence": []
        }

def _test_query_parameter(url: str, method: str, param_name: str, timeout: int) -> Dict[str, Any]:
    """Test parameter as query parameter."""
    try:
        parsed_url = urlparse(url)
        existing_params = dict(q.split('=') for q in parsed_url.query.split('&') if '=' in q)
        test_params = {**existing_params, param_name: "test"}
        
        from urllib.parse import urlencode
        new_query = urlencode(test_params)
        test_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
        
        if method.upper() == "GET":
            response = requests.get(test_url, timeout=timeout)
        else:
            response = requests.post(test_url, timeout=timeout)
        
        return {
            "tested_location": "query",
            "status_code": response.status_code,
            "error_text": response.text[:200] + "..." if len(response.text) > 200 else response.text
        }
    except Exception as e:
        return {
            "tested_location": "query",
            "status_code": 0,
            "error_text": f"Connection error: {str(e)}"
        }

def _test_body_parameter(url: str, method: str, param_name: str, timeout: int) -> Dict[str, Any]:
    """Test parameter as body parameter."""
    try:
        payload = {param_name: "test"}
        
        if method.upper() == "POST":
            response = requests.post(url, json=payload, timeout=timeout)
        else:
            response = requests.get(url, json=payload, timeout=timeout)
        
        return {
            "tested_location": "body",
            "status_code": response.status_code,
            "error_text": response.text[:200] + "..." if len(response.text) > 200 else response.text
        }
    except Exception as e:
        return {
            "tested_location": "body",
            "status_code": 0,
            "error_text": f"Connection error: {str(e)}"
        }

def _check_path_parameter(url: str, param_name: str) -> Dict[str, Any]:
    """Check if parameter appears in URL path (heuristic, no request)."""
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Look for {param} or :param patterns
        path_patterns = [
            r'\{' + re.escape(param_name) + r'\}',  # {param}
            r':' + re.escape(param_name) + r'(?=/|$)',  # :param
        ]
        
        for pattern in path_patterns:
            if re.search(pattern, path):
                return {
                    "tested_location": "path",
                    "status_code": 0,  # No request made
                    "error_text": f"Path parameter detected: {param_name} in {path}"
                }
        
        return None
    except Exception as e:
        return {
            "tested_location": "path",
            "status_code": 0,
            "error_text": f"Path detection error: {str(e)}"
        }

def _test_header_parameter(url: str, method: str, param_name: str, timeout: int) -> Dict[str, Any]:
    """Test parameter as header parameter (conservative)."""
    try:
        headers = {f"X-{param_name}": "test"}
        
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, timeout=timeout)
        else:
            response = requests.get(url, headers=headers, timeout=timeout)
        
        # Only accept if explicitly referenced in error
        error_text = response.text.lower()
        if param_name.lower() in error_text and "header" in error_text:
            return {
                "tested_location": "header",
                "status_code": response.status_code,
                "error_text": response.text[:200] + "..." if len(response.text) > 200 else response.text
            }
        
        return None  # Inconclusive, discard
        
    except Exception as e:
        return {
            "tested_location": "header",
            "status_code": 0,
            "error_text": f"Header test error: {str(e)}"
        }

def _explicit_query_reference(error_text: str) -> bool:
    """Check if error explicitly mentions query parameter."""
    error_lower = error_text.lower()
    query_indicators = [
        "query parameter",
        "query string",
        "url parameter",
        "get parameter",
        "parameter in query"
    ]
    return any(indicator in error_lower for indicator in query_indicators)

def _explicit_body_reference(error_text: str) -> bool:
    """Check if error explicitly mentions body field."""
    error_lower = error_text.lower()
    body_indicators = [
        "body field",
        "request body",
        "json field",
        "field in body",
        "request field",
        "payload field"
    ]
    return any(indicator in error_lower for indicator in body_indicators)

def _explicit_header_reference(error_text: str) -> bool:
    """Check if error explicitly mentions header."""
    error_lower = error_text.lower()
    header_indicators = [
        "header parameter",
        "request header",
        "header field",
        "x-",
        "header missing"
    ]
    return any(indicator in error_lower for indicator in header_indicators)

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Location Inference Module")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("http://127.0.0.1:8004/api/orchestrated?username=test", "POST", "username"),
        ("http://127.0.0.1:8004/api/orchestrated", "POST", "username"),
        ("http://127.0.0.1:8004/users/123", "GET", "id"),  # Path parameter
    ]
    
    for url, method, param in test_cases:
        print(f"\n🔍 Testing: {param} in {url}")
        result = infer_parameter_location(url, method, param, 5)
        print(f"Result: {result['location']} (confidence: {result['confidence']:.2f})")
        print(f"Evidence: {len(result['evidence'])} items")
