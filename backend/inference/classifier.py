import requests
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

def classify_endpoint(url: str, method: str, initial_response: Optional[requests.Response] = None) -> str:
    """
    Classify endpoint type to determine optimal probing strategy.
    
    Args:
        url: Target API endpoint
        method: HTTP method
        initial_response: Optional initial response for analysis
        
    Returns:
        Endpoint type: 'json_crud', 'upload', 'auth_protected', 'nested_relational'
    """
    print(f"🔍 Classifying endpoint: {method} {url}")
    
    evidence = []
    scores = {
        'json_crud': 0.3,      # Default baseline
        'upload': 0.1,
        'auth_protected': 0.1,
        'nested_relational': 0.1
    }
    
    try:
        # Analyze URL patterns
        url_analysis = _analyze_url_patterns(url)
        evidence.append(url_analysis)
        for endpoint_type, score in url_analysis.get("type_scores", {}).items():
            scores[endpoint_type] += score
        
        # Analyze method
        method_analysis = _analyze_method(method)
        evidence.append(method_analysis)
        for endpoint_type, score in method_analysis.get("type_scores", {}).items():
            scores[endpoint_type] += score
        
        # If no initial response provided, get one
        if initial_response is None:
            print("📡 Getting initial response for classification...")
            initial_response = _get_initial_response(url, method)
        
        if initial_response:
            # Analyze response
            response_analysis = _analyze_response(initial_response)
            evidence.append(response_analysis)
            for endpoint_type, score in response_analysis.get("type_scores", {}).items():
                scores[endpoint_type] += score
        
        # Determine final classification
        best_type = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[best_type] / sum(scores.values())
        
        result = {
            "endpoint_type": best_type,
            "confidence": min(1.0, confidence),
            "scores": scores,
            "evidence": evidence
        }
        
        print(f"🎯 Classification complete: {best_type} (confidence: {confidence:.2f})")
        return best_type
        
    except Exception as e:
        print(f"💥 Classification failed: {e}")
        return "json_crud"  # Safe fallback

def select_strategy(endpoint_type: str) -> Dict[str, Any]:
    """
    Select probing strategy based on endpoint classification.
    
    Args:
        endpoint_type: Classified endpoint type
        
    Returns:
        Strategy configuration dictionary
    """
    strategies = {
        "json_crud": {
            "content_type": "application/json",
            "probe_modules": ["error_probe", "type_probe", "location_probe"],
            "max_rounds": 5,
            "timeout": 5,
            "priority": "parameter_discovery"
        },
        "upload": {
            "content_type": "multipart/form-data",
            "probe_modules": ["binary_probe", "error_probe"],
            "max_rounds": 3,
            "timeout": 10,
            "priority": "file_and_metadata"
        },
        "auth_protected": {
            "content_type": "application/json",
            "probe_modules": ["error_probe", "type_probe"],
            "max_rounds": 3,
            "timeout": 5,
            "priority": "auth_parameters"
        },
        "nested_relational": {
            "content_type": "application/json",
            "probe_modules": ["error_probe", "type_probe", "location_probe"],
            "max_rounds": 7,
            "timeout": 8,
            "priority": "nested_structure"
        }
    }
    
    strategy = strategies.get(endpoint_type, strategies["json_crud"])
    
    print(f"🔧 Selected strategy for {endpoint_type}:")
    print(f"   Content-Type: {strategy['content_type']}")
    print(f"   Probe modules: {strategy['probe_modules']}")
    print(f"   Max rounds: {strategy['max_rounds']}")
    print(f"   Priority: {strategy['priority']}")
    
    return strategy

def _analyze_url_patterns(url: str) -> Dict[str, Any]:
    """Analyze URL patterns for classification hints."""
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()
    
    scores = {
        'json_crud': 0.1,
        'upload': 0.1,
        'auth_protected': 0.1,
        'nested_relational': 0.1
    }
    
    # Upload indicators
    upload_patterns = [
        '/upload', '/file', '/files', '/media', '/image', '/images',
        '/document', '/documents', '/attachment', '/attachments'
    ]
    
    for pattern in upload_patterns:
        if pattern in path:
            scores['upload'] += 0.4
            break
    
    # Auth indicators
    auth_patterns = [
        '/auth', '/login', '/token', '/oauth', '/signin', '/register',
        '/signup', '/authenticate', '/authorize'
    ]
    
    for pattern in auth_patterns:
        if pattern in path:
            scores['auth_protected'] += 0.5
            break
    
    # Nested relational indicators
    nested_patterns = [
        r'/\d+/',  # ID-based paths like /users/123/posts
        r'/\w+/\d+',  # Resource with ID
        'relationship', 'nested', 'hierarchy'
    ]
    
    for pattern in nested_patterns:
        if isinstance(pattern, str) and pattern in path:
            scores['nested_relational'] += 0.3
        elif hasattr(pattern, 'search') and pattern.search(path):
            scores['nested_relational'] += 0.3
    
    # CRUD indicators (default)
    crud_patterns = [
        '/api/', '/v1/', '/v2/',  # API versioning
        '/users', '/posts', '/comments', '/items', '/products'
    ]
    
    for pattern in crud_patterns:
        if pattern in path:
            scores['json_crud'] += 0.2
    
    return {
        "analysis_type": "url_patterns",
        "path": path,
        "type_scores": scores
    }

def _analyze_method(method: str) -> Dict[str, Any]:
    """Analyze HTTP method for classification hints."""
    method = method.upper()
    
    scores = {
        'json_crud': 0.1,
        'upload': 0.1,
        'auth_protected': 0.1,
        'nested_relational': 0.1
    }
    
    if method == "POST":
        scores['upload'] += 0.3  # Uploads are typically POST
        scores['auth_protected'] += 0.2  # Auth endpoints often POST
        scores['json_crud'] += 0.2  # Create operations
    elif method == "GET":
        scores['json_crud'] += 0.3  # Read operations
        scores['nested_relational'] += 0.2  # Often used for nested data
    elif method in ["PUT", "PATCH"]:
        scores['json_crud'] += 0.3  # Update operations
    elif method == "DELETE":
        scores['json_crud'] += 0.3  # Delete operations
    
    return {
        "analysis_type": "http_method",
        "method": method,
        "type_scores": scores
    }

def _analyze_response(response: requests.Response) -> Dict[str, Any]:
    """Analyze response for classification hints."""
    scores = {
        'json_crud': 0.1,
        'upload': 0.1,
        'auth_protected': 0.1,
        'nested_relational': 0.1
    }
    
    # Analyze status code
    status_code = response.status_code
    
    if status_code == 401:
        scores['auth_protected'] += 0.6
    elif status_code == 415:
        scores['upload'] += 0.4  # Unsupported Media Type suggests file upload
    elif status_code == 422:
        scores['json_crud'] += 0.2  # Validation error suggests structured data
    
    # Analyze response headers
    content_type = response.headers.get("Content-Type", "").lower()
    
    if "application/json" in content_type:
        scores['json_crud'] += 0.2
        scores['nested_relational'] += 0.1
    elif "text/html" in content_type:
        scores['upload'] += 0.1  # Upload forms often return HTML
    
    # Analyze response body
    response_text = response.text.lower()
    
    # Upload indicators in response
    upload_indicators = [
        'file', 'upload', 'multipart', 'form-data', 'attachment',
        'image', 'document', 'media'
    ]
    
    upload_score = sum(1 for indicator in upload_indicators if indicator in response_text)
    if upload_score > 0:
        scores['upload'] += min(0.4, upload_score * 0.1)
    
    # Auth indicators in response
    auth_indicators = [
        'unauthorized', 'authentication', 'login', 'token', 'credential',
        'forbidden', 'access denied', 'permission'
    ]
    
    auth_score = sum(1 for indicator in auth_indicators if indicator in response_text)
    if auth_score > 0:
        scores['auth_protected'] += min(0.5, auth_score * 0.1)
    
    # Nested relational indicators
    nested_indicators = [
        'nested', 'relationship', 'children', 'parent', 'hierarchy',
        'tree', 'nested object', 'array of objects'
    ]
    
    nested_score = sum(1 for indicator in nested_indicators if indicator in response_text)
    if nested_score > 0:
        scores['nested_relational'] += min(0.3, nested_score * 0.1)
    
    return {
        "analysis_type": "response_analysis",
        "status_code": status_code,
        "content_type": content_type,
        "type_scores": scores
    }

def _get_initial_response(url: str, method: str) -> Optional[requests.Response]:
    """Get initial response for classification."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=5)
        else:
            # Send minimal payload for POST
            if method.upper() == "POST":
                response = requests.post(url, json={}, timeout=5)
            else:
                response = requests.request(method, url, timeout=5)
        
        return response
    except Exception as e:
        print(f"⚠️  Could not get initial response: {e}")
        return None

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Endpoint Classifier Module")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("https://api.example.com/users", "GET"),
        ("https://api.example.com/upload", "POST"),
        ("https://api.example.com/auth/login", "POST"),
        ("https://api.example.com/users/123/posts", "GET"),
    ]
    
    for url, method in test_cases:
        print(f"\n🔍 Testing: {method} {url}")
        endpoint_type = classify_endpoint(url, method)
        strategy = select_strategy(endpoint_type)
        print(f"Result: {endpoint_type}")
        print(f"Strategy: {strategy['priority']}")
