import requests
import json
from typing import Dict, Any
from urllib.parse import urlencode, urlparse

def infer_parameter_type(url, method, param_name, timeout=5):
    """
    Infer basic type and constraints for a single parameter using error-driven probing.
    """
    print(f"🔍 Inferring type for parameter: {param_name}")
    
    # Test values to try (in order of specificity)
    test_values = [
        ("test", "string"),      # String hypothesis
        ("1", "number"),         # Number hypothesis  
        ("true", "boolean"),       # Boolean hypothesis
        ("null", "nullable"),      # Nullable hypothesis
        ("{}", "object")         # Object hypothesis
    ]
    
    evidence = []
    inferred_type = "unknown"
    is_nullable = False
    is_required = False
    
    for test_value, test_type in test_values:
        if len(evidence) >= 5:  # Safety limit
            print(f"⚠️  Safety limit reached, stopping inference for {param_name}")
            break
            
        print(f"  Testing {test_type}: {test_value}")
        
        # Send test request
        response = _send_type_test_request(url, method, param_name, test_value, timeout)
        
        # Record evidence
        evidence_item = {
            "tested_value": test_value,
            "status_code": response.status_code,
            "error_text": response.text[:200] + "..." if len(response.text) > 200 else response.text
        }
        evidence.append(evidence_item)
        
        # Analyze response
        if response.status_code == 200:
            # Success - this type is accepted
            inferred_type = test_type
            is_nullable = (test_value == "null")
            print(f"    ✅ {test_type} accepted")
            break
        elif response.status_code == 422:
            # Validation error - analyze to see if this type is rejected
            if _is_type_rejected(response.text, test_value):
                print(f"    ❌ {test_type} rejected by validation")
                continue
            else:
                print(f"    ⚠️  {test_type} caused different error")
                continue
        else:
            # Other error - continue testing
            print(f"    ⚠️  {test_type} caused error {response.status_code}")
            continue
    
    # Test if parameter is required by sending empty/null
    if not is_required and len(evidence) < 5:
        print(f"  Testing if {param_name} is required...")
        required_response = _send_type_test_request(url, method, param_name, "", timeout)
        
        required_evidence = {
            "tested_value": "",
            "status_code": required_response.status_code,
            "error_text": required_response.text[:200] + "..." if len(required_response.text) > 200 else required_response.text
        }
        evidence.append(required_evidence)
        
        if required_response.status_code == 422:
            is_required = True
            print(f"    ✅ {param_name} is required")
        elif required_response.status_code == 200:
            print(f"    ✅ {param_name} is optional")
    
    # Build result
    result = {
        "type": inferred_type,
        "nullable": is_nullable,
        "required": is_required,
        "evidence": evidence
    }
    
    print(f"🎯 Inference complete for {param_name}: {inferred_type} (required: {is_required}, nullable: {is_nullable})")
    return result

def _send_type_test_request(url, method, param_name, test_value, timeout):
    """
    Send a type test request for a single parameter.
    """
    try:
        if method.upper() == "GET":
            # For GET, add parameter to URL
            parsed_url = urlparse(url)
            existing_params = dict(q.split('=') for q in parsed_url.query.split('&') if '=' in q)
            test_params = {**existing_params, param_name: test_value}
            new_query = urlencode(test_params)
            test_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
            response = requests.get(test_url, timeout=timeout, headers={'Content-Type': 'application/json'})
        else:
            # For POST, send as JSON with single parameter
            payload = {param_name: test_value}
            response = requests.post(url, json=payload, timeout=timeout, headers={'Content-Type': 'application/json'})
        
        return response
    except Exception as e:
        # Return a mock response for connection errors
        class MockResponse:
            def __init__(self):
                self.status_code = 0
                self.text = f"Connection error: {str(e)}"
                self.content = self.text.encode()
        return MockResponse()

def _is_type_rejected(error_text, test_value):
    """
    Check if error text indicates the test value type was rejected.
    """
    error_lower = error_text.lower()
    
    # Type-specific rejection patterns
    if test_value == "test" and any(keyword in error_lower for keyword in [
        'must be a string', 'expected string', 'invalid string', 'not a string'
    ]):
        return True
    
    if test_value == "1" and any(keyword in error_lower for keyword in [
        'must be a number', 'expected number', 'invalid number', 'not a number',
        'must be integer', 'expected integer', 'invalid integer'
    ]):
        return True
    
    if test_value == "true" and any(keyword in error_lower for keyword in [
        'must be a boolean', 'expected boolean', 'invalid boolean', 'not a boolean'
    ]):
        return True
    
    if test_value == "null" and any(keyword in error_lower for keyword in [
        'may not be null', 'cannot be null', 'expected value', 'required field'
    ]):
        return True
    
    if test_value == "{}" and any(keyword in error_lower for keyword in [
        'must be an object', 'expected object', 'invalid object', 'not an object'
    ]):
        return True
    
    return False

# Test function for development
if __name__ == "__main__":
    # Test with a local endpoint that has type validation
    test_url = "http://127.0.0.1:8003/api/typed"
    
    print("🧪 Testing Type Inference Module")
    print("=" * 50)
    
    # Test parameter that should be discovered as required string
    result = infer_parameter_type(test_url, "POST", "username", 5)
    print("\n" + "=" * 50)
    print("TYPE INFERENCE RESULT:")
    print(json.dumps(result, indent=2))
