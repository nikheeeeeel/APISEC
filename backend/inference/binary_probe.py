import requests
import re
import io
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

def infer_file_parameters(url: str, method: str, timeout: int = 10) -> Dict[str, Dict[str, Any]]:
    """
    Infer file upload parameters and metadata requirements.
    
    Args:
        url: Target API endpoint
        method: HTTP method (typically POST for uploads)
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary of discovered file and metadata parameters
    """
    print(f"🔍 Inferring file parameters for: {url}")
    
    discovered_params = {}
    tested_params = set()
    evidence = []
    
    try:
        # Test 1: Empty multipart request to trigger validation errors
        print("1️⃣ Testing empty multipart request...")
        empty_result = _test_empty_multipart(url, timeout)
        if empty_result:
            evidence.append(empty_result)
            empty_params = _extract_params_from_multipart_error(empty_result.get("error_text", ""), tested_params)
            discovered_params.update(empty_params)
            tested_params.update(empty_params.keys())
        
        # Test 2: Multipart with only file to discover metadata requirements
        print("2️⃣ Testing file-only multipart request...")
        file_result = _test_file_only_multipart(url, timeout)
        if file_result:
            evidence.append(file_result)
            file_params = _extract_params_from_multipart_error(file_result.get("error_text", ""), tested_params)
            discovered_params.update(file_params)
            tested_params.update(file_params.keys())
        
        # Test 3: Multipart with common metadata fields
        print("3️⃣ Testing metadata fields...")
        metadata_result = _test_common_metadata(url, timeout)
        if metadata_result:
            evidence.append(metadata_result)
            metadata_params = _extract_params_from_multipart_error(metadata_result.get("error_text", ""), tested_params)
            discovered_params.update(metadata_params)
            tested_params.update(metadata_params.keys())
        
        # Test 4: Test specific file types if file parameter discovered
        file_params = {k: v for k, v in discovered_params.items() if _is_file_parameter(k, v)}
        if file_params:
            print("4️⃣ Testing file type requirements...")
            file_type_result = _test_file_types(url, list(file_params.keys())[0], timeout)
            if file_type_result:
                evidence.append(file_type_result)
                _update_file_type_info(discovered_params, file_type_result)
        
        # Add evidence to all discovered parameters
        for param_name, param_info in discovered_params.items():
            param_info["evidence"] = evidence.copy()
            param_info["confidence"] = _calculate_file_confidence(param_name, param_info, evidence)
        
        print(f"🎯 File parameter inference complete")
        print(f"   Discovered {len(discovered_params)} parameters")
        print(f"   File parameters: {len([p for p in discovered_params.values() if _is_file_parameter(p, discovered_params)])}")
        
        return discovered_params
        
    except Exception as e:
        print(f"💥 File parameter inference failed: {e}")
        return {}

def _test_empty_multipart(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test empty multipart request to trigger validation errors."""
    try:
        # Send empty multipart form
        files = {}
        data = {}
        
        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=timeout,
            headers={"Accept": "application/json"}
        )
        
        return {
            "test_type": "empty_multipart",
            "status_code": response.status_code,
            "error_text": response.text[:500] if response.text else "",
            "content_type": response.headers.get("Content-Type", "")
        }
    except Exception as e:
        return {
            "test_type": "empty_multipart",
            "status_code": 0,
            "error_text": str(e)
        }

def _test_file_only_multipart(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test multipart with only a file to discover metadata requirements."""
    try:
        # Generate small test file
        test_file = generate_test_binary("image/png")
        
        files = {"file": ("test.png", test_file, "image/png")}
        data = {}
        
        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=timeout,
            headers={"Accept": "application/json"}
        )
        
        return {
            "test_type": "file_only",
            "status_code": response.status_code,
            "error_text": response.text[:500] if response.text else "",
            "content_type": response.headers.get("Content-Type", ""),
            "file_type": "image/png"
        }
    except Exception as e:
        return {
            "test_type": "file_only",
            "status_code": 0,
            "error_text": str(e)
        }

def _test_common_metadata(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test multipart with common metadata fields."""
    try:
        # Common metadata fields for file uploads
        common_metadata = {
            "folderId": "1",
            "filename": "test.png",
            "description": "Test file",
            "title": "Test Upload",
            "category": "general",
            "tags": "test",
            "parentId": "0"
        }
        
        test_file = generate_test_binary("image/png")
        files = {"file": ("test.png", test_file, "image/png")}
        
        response = requests.post(
            url,
            files=files,
            data=common_metadata,
            timeout=timeout,
            headers={"Accept": "application/json"}
        )
        
        return {
            "test_type": "common_metadata",
            "status_code": response.status_code,
            "error_text": response.text[:500] if response.text else "",
            "content_type": response.headers.get("Content-Type", ""),
            "metadata_tested": list(common_metadata.keys())
        }
    except Exception as e:
        return {
            "test_type": "common_metadata",
            "status_code": 0,
            "error_text": str(e)
        }

def _test_file_types(url: str, file_param: str, timeout: int) -> Optional[Dict[str, Any]]:
    """Test different file types to determine accepted formats."""
    file_types = [
        ("image/png", "test.png"),
        ("image/jpeg", "test.jpg"),
        ("application/pdf", "test.pdf"),
        ("text/plain", "test.txt")
    ]
    
    results = []
    
    for content_type, filename in file_types:
        try:
            test_file = generate_test_binary(content_type)
            files = {file_param: (filename, test_file, content_type)}
            
            response = requests.post(
                url,
                files=files,
                data={},
                timeout=timeout,
                headers={"Accept": "application/json"}
            )
            
            results.append({
                "content_type": content_type,
                "filename": filename,
                "status_code": response.status_code,
                "error_text": response.text[:200] if response.text else ""
            })
            
        except Exception as e:
            results.append({
                "content_type": content_type,
                "filename": filename,
                "status_code": 0,
                "error_text": str(e)
            })
    
    return {
        "test_type": "file_types",
        "results": results
    }

def generate_test_binary(file_type: str) -> bytes:
    """Generate a small test binary file of the specified type."""
    if file_type == "image/png":
        # Minimal PNG header (1x1 transparent pixel)
        return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    elif file_type == "image/jpeg":
        # Minimal JPEG header
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    elif file_type == "application/pdf":
        # Minimal PDF header
        return b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF'
    elif file_type == "text/plain":
        # Simple text content
        return b"This is a test file content for upload testing."
    else:
        # Default binary content
        return b"Test binary content for " + file_type.encode()

def _extract_params_from_multipart_error(error_text: str, tested_params: set) -> Dict[str, Dict[str, Any]]:
    """Extract parameter names from multipart/form-data error responses."""
    new_params = {}
    
    # Multipart-specific error patterns
    patterns = [
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
        
        # Generic patterns
        r'"(\w+)"\s*:\s*["\']?required["\']?',
        r'(\w+)\s+(?:parameter|field)\s+(?:is\s+)?(?:required|missing|invalid)',
    ]
    
    # Common non-parameter words to filter out
    NON_PARAM_WORDS = {
        'error', 'message', 'status', 'code', 'type', 'detail', 'success', 'failed',
        'field', 'required', 'missing', 'invalid', 'parameter', 'is', 'not', 'in',
        'loc', 'input', 'form', 'data', 'payload', 'body', 'file', 'upload'
    }
    
    for pattern in patterns:
        matches = re.finditer(pattern, error_text, re.IGNORECASE)
        for match in matches:
            param_name = match.group(1)
            
            # Skip if already tested or if it's a common non-parameter word
            if (param_name.lower() in tested_params or 
                param_name.lower() in NON_PARAM_WORDS):
                continue
            
            # Determine if this is a file parameter
            is_file = _is_file_parameter(param_name, {"error_text": error_text})
            
            new_params[param_name] = {
                "required": True,
                "type": "file" if is_file else "string",
                "location": "form",
                "is_file": is_file,
                "confidence": 0.7 if is_file else 0.5
            }
    
    return new_params

def _is_file_parameter(param_name: str, param_info: Dict[str, Any]) -> bool:
    """Determine if a parameter is a file parameter."""
    param_lower = param_name.lower()
    error_text = param_info.get("error_text", "").lower()
    
    # File parameter indicators
    file_indicators = [
        'file', 'upload', 'image', 'document', 'media', 'attachment',
        'photo', 'picture', 'video', 'audio', 'pdf', 'csv', 'excel'
    ]
    
    # Check parameter name
    if any(indicator in param_lower for indicator in file_indicators):
        return True
    
    # Check error text for file-related context
    if any(indicator in error_text for indicator in file_indicators):
        return True
    
    # Check for specific file upload patterns
    if any(pattern in error_text for pattern in [
        'file upload', 'upload file', 'file field', 'multipart file'
    ]):
        return True
    
    return False

def _update_file_type_info(discovered_params: Dict[str, Any], file_type_result: Dict[str, Any]) -> None:
    """Update file parameter information with type test results."""
    results = file_type_result.get("results", [])
    accepted_types = []
    rejected_types = []
    
    for result in results:
        content_type = result["content_type"]
        status_code = result["status_code"]
        
        if status_code == 200 or status_code == 201:
            accepted_types.append(content_type)
        elif status_code == 415:  # Unsupported Media Type
            rejected_types.append(content_type)
    
    # Update file parameters with type information
    for param_name, param_info in discovered_params.items():
        if param_info.get("is_file"):
            param_info["accepted_types"] = accepted_types
            param_info["rejected_types"] = rejected_types
            if accepted_types:
                param_info["confidence"] += 0.2

def _calculate_file_confidence(param_name: str, param_info: Dict[str, Any], evidence: List[Dict[str, Any]]) -> float:
    """Calculate confidence score for file parameter discovery."""
    base_confidence = param_info.get("confidence", 0.3)
    
    # Higher confidence for file parameters
    if param_info.get("is_file"):
        base_confidence += 0.2
    
    # Higher confidence if accepted types were determined
    if param_info.get("accepted_types"):
        base_confidence += 0.2
    
    # Higher confidence for explicit error messages
    for item in evidence:
        error_text = item.get("error_text", "").lower()
        if param_name.lower() in error_text:
            base_confidence += 0.1
    
    return min(1.0, max(0.1, base_confidence))

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Binary Probe Module")
    print("=" * 50)
    
    # Test with a local upload endpoint
    test_url = "http://127.0.0.1:8000/api/upload"
    
    result = infer_file_parameters(test_url, "POST", 10)
    print("\n" + "=" * 50)
    print("FILE PARAMETER INFERENCE RESULT:")
    for param_name, param_info in result.items():
        print(f"Parameter: {param_name}")
        print(f"  Type: {param_info.get('type', 'unknown')}")
        print(f"  Required: {param_info.get('required', False)}")
        print(f"  Is File: {param_info.get('is_file', False)}")
        print(f"  Confidence: {param_info.get('confidence', 0.0):.2f}")
        if param_info.get('accepted_types'):
            print(f"  Accepted Types: {param_info['accepted_types']}")
        print()
