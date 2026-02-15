import requests
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

def detect_content_type(url: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Detect supported content types and optimal probing strategy.
    
    Args:
        url: Target API endpoint
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with content type information and probing strategy
    """
    print(f"🔍 Detecting content types for: {url}")
    
    evidence = []
    detected_types = []
    preferred_strategy = "json"  # Default to existing JSON strategy
    
    try:
        # Test 1: OPTIONS request for allowed methods and content types
        print("1️⃣ Testing OPTIONS request...")
        options_result = _test_options_method(url, timeout)
        if options_result:
            evidence.append(options_result)
            detected_types.extend(options_result.get("allowed_content_types", []))
        
        # Test 2: HEAD request for content-type headers
        print("2️⃣ Testing HEAD request...")
        head_result = _test_head_method(url, timeout)
        if head_result:
            evidence.append(head_result)
            detected_types.extend(head_result.get("content_types", []))
        
        # Test 3: Minimal POST with JSON to analyze response
        print("3️⃣ Testing JSON POST response...")
        json_result = _test_json_response(url, timeout)
        if json_result:
            evidence.append(json_result)
            if json_result.get("accepts_json"):
                detected_types.append("application/json")
        
        # Test 4: Minimal POST with form data to analyze response
        print("4️⃣ Testing form POST response...")
        form_result = _test_form_response(url, timeout)
        if form_result:
            evidence.append(form_result)
            if form_result.get("accepts_form"):
                detected_types.extend(["multipart/form-data", "application/x-www-form-urlencoded"])
        
        # Analyze detected types and determine strategy
        detected_types = list(set(detected_types))  # Remove duplicates
        
        if "multipart/form-data" in detected_types:
            preferred_strategy = "upload"
        elif "application/x-www-form-urlencoded" in detected_types:
            preferred_strategy = "form"
        elif "application/json" in detected_types:
            preferred_strategy = "json"
        
        result = {
            "detected_content_types": detected_types,
            "preferred_strategy": preferred_strategy,
            "evidence": evidence,
            "confidence": _calculate_type_confidence(detected_types, evidence)
        }
        
        print(f"🎯 Content type detection complete")
        print(f"   Detected types: {detected_types}")
        print(f"   Preferred strategy: {preferred_strategy}")
        print(f"   Confidence: {result['confidence']:.2f}")
        
        return result
        
    except Exception as e:
        print(f"💥 Content type detection failed: {e}")
        return {
            "detected_content_types": ["application/json"],  # Fallback
            "preferred_strategy": "json",
            "evidence": [{"error": str(e)}],
            "confidence": 0.1
        }

def adapt_probe_strategy(content_type: str, url: str, method: str) -> Dict[str, Any]:
    """
    Adapt probing strategy based on detected content type.
    
    Args:
        content_type: Detected content type or strategy
        url: Target API endpoint
        method: HTTP method
        
    Returns:
        Dictionary with strategy configuration
    """
    strategies = {
        "json": {
            "content_type": "application/json",
            "probe_module": "error_probe",
            "request_builder": _build_json_request,
            "max_requests": 10,
            "timeout": 5
        },
        "form": {
            "content_type": "application/x-www-form-urlencoded",
            "probe_module": "error_probe",
            "request_builder": _build_form_request,
            "max_requests": 8,
            "timeout": 5
        },
        "upload": {
            "content_type": "multipart/form-data",
            "probe_module": "binary_probe",
            "request_builder": _build_multipart_request,
            "max_requests": 15,
            "timeout": 10
        }
    }
    
    strategy = strategies.get(content_type, strategies["json"])
    
    print(f"🔧 Adapting strategy for: {content_type}")
    print(f"   Content-Type: {strategy['content_type']}")
    print(f"   Probe module: {strategy['probe_module']}")
    print(f"   Max requests: {strategy['max_requests']}")
    
    return strategy

def _test_options_method(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test OPTIONS method to discover allowed content types."""
    try:
        response = requests.options(url, timeout=timeout)
        
        # Parse Allow header for methods
        allow_header = response.headers.get("Allow", "")
        allowed_methods = [m.strip() for m in allow_header.split(",") if m.strip()]
        
        # Parse Accept header for content types
        accept_header = response.headers.get("Accept", "")
        content_types = _parse_accept_header(accept_header)
        
        return {
            "method": "OPTIONS",
            "status_code": response.status_code,
            "allowed_methods": allowed_methods,
            "allowed_content_types": content_types,
            "headers": dict(response.headers)
        }
    except Exception as e:
        return {
            "method": "OPTIONS",
            "status_code": 0,
            "error": str(e)
        }

def _test_head_method(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test HEAD method to analyze response headers."""
    try:
        response = requests.head(url, timeout=timeout)
        
        content_type = response.headers.get("Content-Type", "")
        content_types = [content_type] if content_type else []
        
        return {
            "method": "HEAD",
            "status_code": response.status_code,
            "content_types": content_types,
            "headers": dict(response.headers)
        }
    except Exception as e:
        return {
            "method": "HEAD",
            "status_code": 0,
            "error": str(e)
        }

def _test_json_response(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test minimal JSON POST to analyze response."""
    try:
        payload = {"test": "value"}
        response = requests.post(
            url, 
            json=payload, 
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        # Check if server accepts JSON based on response
        accepts_json = (
            response.status_code != 415 and  # Not Unsupported Media Type
            "json" in response.headers.get("Content-Type", "").lower()
        )
        
        return {
            "method": "POST",
            "content_type": "application/json",
            "status_code": response.status_code,
            "accepts_json": accepts_json,
            "response_content_type": response.headers.get("Content-Type", ""),
            "error_text": response.text[:200] if response.text else ""
        }
    except Exception as e:
        return {
            "method": "POST",
            "content_type": "application/json",
            "status_code": 0,
            "accepts_json": False,
            "error": str(e)
        }

def _test_form_response(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test minimal form POST to analyze response."""
    try:
        payload = {"test": "value"}
        response = requests.post(
            url, 
            data=payload, 
            timeout=timeout,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Check if server accepts form data
        accepts_form = (
            response.status_code != 415 and  # Not Unsupported Media Type
            "form" in response.text.lower() or
            response.status_code < 500
        )
        
        return {
            "method": "POST",
            "content_type": "application/x-www-form-urlencoded",
            "status_code": response.status_code,
            "accepts_form": accepts_form,
            "response_content_type": response.headers.get("Content-Type", ""),
            "error_text": response.text[:200] if response.text else ""
        }
    except Exception as e:
        return {
            "method": "POST",
            "content_type": "application/x-www-form-urlencoded",
            "status_code": 0,
            "accepts_form": False,
            "error": str(e)
        }

def _parse_accept_header(accept_header: str) -> List[str]:
    """Parse Accept header to extract content types."""
    if not accept_header:
        return []
    
    content_types = []
    for part in accept_header.split(","):
        content_type = part.split(";")[0].strip()
        if content_type:
            content_types.append(content_type)
    
    return content_types

def _calculate_type_confidence(detected_types: List[str], evidence: List[Dict[str, Any]]) -> float:
    """Calculate confidence in content type detection."""
    base_confidence = 0.3
    
    # Higher confidence for explicit content type headers
    for item in evidence:
        if item.get("content_types"):
            base_confidence += 0.2
        if item.get("allowed_content_types"):
            base_confidence += 0.2
    
    # Higher confidence for multiple successful tests
    successful_tests = len([e for e in evidence if e.get("status_code", 0) < 500])
    base_confidence += min(0.3, successful_tests * 0.1)
    
    # Higher confidence for specific content types
    if "multipart/form-data" in detected_types:
        base_confidence += 0.2
    elif "application/json" in detected_types:
        base_confidence += 0.1
    
    return min(1.0, max(0.1, base_confidence))

def _build_json_request(url: str, method: str, payload: Dict[str, Any]) -> requests.PreparedRequest:
    """Build JSON request for probing."""
    session = requests.Session()
    if method.upper() == "GET":
        req = requests.Request("GET", url, params=payload)
    else:
        req = requests.Request("POST", url, json=payload)
    return session.prepare_request(req)

def _build_form_request(url: str, method: str, payload: Dict[str, Any]) -> requests.PreparedRequest:
    """Build form request for probing."""
    session = requests.Session()
    if method.upper() == "GET":
        req = requests.Request("GET", url, params=payload)
    else:
        req = requests.Request("POST", url, data=payload)
    return session.prepare_request(req)

def _build_multipart_request(url: str, method: str, payload: Dict[str, Any]) -> requests.PreparedRequest:
    """Build multipart request for probing."""
    session = requests.Session()
    if method.upper() == "GET":
        req = requests.Request("GET", url, params=payload)
    else:
        # For multipart, we need to handle files separately
        files = {}
        data = {}
        
        for key, value in payload.items():
            if hasattr(value, 'read') or isinstance(value, bytes):
                files[key] = value
            else:
                data[key] = value
        
        req = requests.Request("POST", url, data=data, files=files)
    return session.prepare_request(req)

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Content Type Probe Module")
    print("=" * 50)
    
    # Test with a local endpoint
    test_url = "http://127.0.0.1:8000/api/test"
    
    result = detect_content_type(test_url, 5)
    print("\n" + "=" * 50)
    print("CONTENT TYPE DETECTION RESULT:")
    print(f"Detected types: {result['detected_content_types']}")
    print(f"Preferred strategy: {result['preferred_strategy']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Evidence items: {len(result['evidence'])}")
