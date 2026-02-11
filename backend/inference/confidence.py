from typing import Dict, Any, Optional, List

def calculate_confidence(
    parameter_name: str,
    error_probe_result: Optional[Dict[str, Any]] = None,
    type_probe_result: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Calculate confidence score for a parameter by merging signals from error_probe and type_probe.
    
    Pure function - no HTTP requests, no side effects, fully deterministic.
    
    Args:
        parameter_name: Name of the parameter
        error_probe_result: Result from error_probe module (may be None)
        type_probe_result: Result from type_probe module (may be None)
        
    Returns:
        None if both probes failed, otherwise confidence metadata
    """
    # If both probes failed, return None
    if not error_probe_result and not type_probe_result:
        return None
    
    # Start with base confidence if parameter exists at all
    confidence = 0.2 if (error_probe_result or type_probe_result) else 0.0
    
    evidence = []
    
    # Process error probe signals
    if error_probe_result:
        param_info = error_probe_result.get(parameter_name)
        if param_info:
            # Structured validation error mentioning param → +0.3
            if _is_structured_error(param_info):
                confidence += 0.3
                evidence.append({
                    "source": "error_probe",
                    "detail": "Structured validation error"
                })
            
            # Parameter referenced multiple times → +0.2
            if _is_multiple_references(param_info):
                confidence += 0.2
                evidence.append({
                    "source": "error_probe", 
                    "detail": "Multiple parameter references"
                })
            
            # Required inferred from missing field error → +0.1
            if _is_required_inference(param_info):
                confidence += 0.1
                evidence.append({
                    "source": "error_probe",
                    "detail": "Required field inference"
                })
    
    # Process type probe signals
    if type_probe_result:
        param_info = type_probe_result.get(parameter_name)
        if param_info:
            # Type inferred (Not unknown) → +0.2
            if param_info.get("type") != "unknown":
                confidence += 0.2
                evidence.append({
                    "source": "type_probe",
                    "detail": f"Type inferred: {param_info.get('type')}"
                })
            
            # Required inferred from validation → +0.1
            if param_info.get("required"):
                confidence += 0.1
                evidence.append({
                    "source": "type_probe",
                    "detail": "Required parameter inference"
                })
    
    # Apply penalties
    if error_probe_result and type_probe_result:
        # Conflicting evidence → -0.2
        if _has_conflicting_evidence(error_probe_result.get(parameter_name), type_probe_result.get(parameter_name)):
            confidence -= 0.2
            evidence.append({
                "source": "confidence_engine",
                "detail": "Conflicting evidence detected"
            })
    
    # Penalty for only generic errors
    if error_probe_result:
        param_info = error_probe_result.get(parameter_name)
        if _only_generic_errors(param_info):
            confidence -= 0.1
            evidence.append({
                "source": "confidence_engine",
                "detail": "Only generic error patterns"
            })
    
    # Clamp confidence to valid range
    confidence = max(0.1, min(1.0, confidence))
    
    # If no meaningful evidence, keep confidence low
    if not evidence:
        confidence = 0.1
    
    # Build final result
    result = {
        "name": parameter_name,
        "location": "body",  # Default location (auth/query out of scope)
        "required": _infer_required(error_probe_result, type_probe_result),
        "type": _infer_type(type_probe_result),
        "nullable": _infer_nullable(type_probe_result),
        "confidence": confidence,
        "evidence": evidence
    }
    
    return result

def _is_structured_error(param_info: Dict[str, Any]) -> bool:
    """Check if error shows structured validation mentioning the parameter."""
    if not param_info.get("evidence"):
        return False
    
    for evidence_item in param_info["evidence"]:
        error_text = evidence_item.get("error_text", "").lower()
        if any(keyword in error_text for keyword in [
            "field required", "missing", "invalid", "validation error"
        ]) and param_info.get("name", "").lower() in error_text:
            return True
    
    return False

def _is_multiple_references(param_info: Dict[str, Any]) -> bool:
    """Check if parameter is referenced multiple times in error messages."""
    if not param_info.get("evidence"):
        return False
    
    param_name = param_info.get("name", "").lower()
    reference_count = 0
    
    for evidence_item in param_info["evidence"]:
        error_text = evidence_item.get("error_text", "").lower()
        reference_count += error_text.count(param_name)
    
    return reference_count > 1

def _is_required_inference(param_info: Dict[str, Any]) -> bool:
    """Check if required status was inferred from missing field errors."""
    if not param_info.get("evidence"):
        return False
    
    for evidence_item in param_info["evidence"]:
        error_text = evidence_item.get("error_text", "").lower()
        if any(keyword in error_text for keyword in [
            "required", "missing", "not provided", "null", "undefined"
        ]):
            return True
    
    return False

def _only_generic_errors(param_info: Optional[Dict[str, Any]]) -> bool:
    """Check if error evidence contains only generic patterns."""
    if not param_info or not param_info.get("evidence"):
        return True  # No evidence = generic
    
    for evidence_item in param_info["evidence"]:
        error_text = evidence_item.get("error_text", "").lower()
        # Generic error patterns that don't give specific parameter info
        if any(generic in error_text for generic in [
            "internal server error", "bad request", "forbidden", "unauthorized",
            "not found", "method not allowed", "timeout", "connection error"
        ]):
            return True
    
    return False

def _has_conflicting_evidence(error_info: Dict[str, Any], type_info: Dict[str, Any]) -> bool:
    """Check if error and type probe provide conflicting information."""
    if not error_info or not type_info:
        return False
    
    # Check for conflicting type information
    error_type = _extract_type_from_error(error_info)
    probe_type = type_info.get("type", "unknown")
    
    if error_type != "unknown" and probe_type != "unknown" and error_type != probe_type:
        return True
    
    # Check for conflicting required information
    error_required = _infer_required({"": error_info}, None)
    probe_required = type_info.get("required", False)
    
    if error_required != probe_required:
        return True
    
    return False

def _extract_type_from_error(param_info: Dict[str, Any]) -> str:
    """Extract type information from error probe evidence."""
    if not param_info.get("evidence"):
        return "unknown"
    
    for evidence_item in param_info["evidence"]:
        error_text = evidence_item.get("error_text", "").lower()
        
        if "string" in error_text:
            return "string"
        elif "number" in error_text or "integer" in error_text:
            return "number"
        elif "boolean" in error_text:
            return "boolean"
        elif "object" in error_text:
            return "object"
    
    return "unknown"

def _infer_required(error_probe_result: Optional[Dict[str, Any]], type_probe_result: Optional[Dict[str, Any]]) -> bool:
    """Infer if parameter is required from probe results."""
    # Check type probe first (more direct)
    if type_probe_result and type_probe_result.get("required"):
        return True
    
    # Check error probe for missing field errors
    if error_probe_result:
        for param_info in error_probe_result.values():
            if _is_required_inference(param_info):
                return True
    
    return False

def _infer_type(type_probe_result: Optional[Dict[str, Any]]) -> str:
    """Infer parameter type from type probe result."""
    if not type_probe_result:
        return "unknown"
    
    return type_probe_result.get("type", "unknown")

def _infer_nullable(type_probe_result: Optional[Dict[str, Any]]) -> bool:
    """Infer if parameter is nullable from type probe result."""
    if not type_probe_result:
        return False
    
    return type_probe_result.get("nullable", False)

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Confidence Engine")
    print("=" * 50)
    
    # Test case 1: Strong evidence from both probes
    error_result = {
        "username": {
            "required": True,
            "evidence": [{"error_text": "Field username is required", "status_code": 422}]
        }
    }
    
    type_result = {
        "username": {
            "type": "string",
            "required": True,
            "evidence": [{"tested_value": "test", "status_code": 200}]
        }
    }
    
    result1 = calculate_confidence("username", error_result, type_result)
    print("Test 1 - Strong evidence from both probes:")
    print(f"  Confidence: {result1['confidence']:.2f}")
    print(f"  Type: {result1['type']}")
    print(f"  Required: {result1['required']}")
    
    # Test case 2: Weak evidence from error probe only
    result2 = calculate_confidence("email", error_result, None)
    print("\nTest 2 - Weak evidence from error probe only:")
    print(f"  Confidence: {result2['confidence']:.2f}")
    print(f"  Type: {result2['type']}")
    
    # Test case 3: No evidence
    result3 = calculate_confidence("unknown_param", None, None)
    print("\nTest 3 - No evidence:")
    print(f"  Result: {result3}")
    
    # Test case 4: Conflicting evidence
    conflicting_type = {
        "username": {
            "type": "number",
            "required": True,
            "evidence": [{"tested_value": "1", "status_code": 200}]
        }
    }
    
    result4 = calculate_confidence("username", error_result, conflicting_type)
    print("\nTest 4 - Conflicting evidence:")
    print(f"  Confidence: {result4['confidence']:.2f}")
    print(f"  Evidence: {len(result4['evidence'])} items")
