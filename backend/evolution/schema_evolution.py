import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Storage directory for schema history
SCHEMA_STORAGE_DIR = Path.home() / ".apisec" / "schema_history"

def store_spec_version(url: str, spec: Dict[str, Any], timestamp: str = None) -> bool:
    """
    Store a version of the API spec for evolution tracking.
    
    Args:
        url: API endpoint URL
        spec: OpenAPI spec dictionary
        timestamp: Optional timestamp (defaults to current time)
        
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Create storage directory if it doesn't exist
        SCHEMA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename based on URL hash and timestamp
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp_clean = timestamp.replace(":", "-").replace(".", "-")
        filename = f"{url_hash}_{timestamp_clean}.json"
        filepath = SCHEMA_STORAGE_DIR / filename
        
        # Prepare storage data
        storage_data = {
            "url": url,
            "timestamp": timestamp,
            "spec": spec,
            "metadata": {
                "version_hash": _generate_spec_hash(spec),
                "parameter_count": _count_parameters(spec),
                "endpoint_count": _count_endpoints(spec)
            }
        }
        
        # Store to file
        with open(filepath, 'w') as f:
            json.dump(storage_data, f, indent=2)
        
        print(f"💾 Stored spec version: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to store spec version: {e}")
        return False

def get_spec_history(url: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve historical specs for a given URL.
    
    Args:
        url: API endpoint URL
        limit: Maximum number of historical versions to return
        
    Returns:
        List of historical spec data ordered by timestamp (newest first)
    """
    try:
        if not SCHEMA_STORAGE_DIR.exists():
            return []
        
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        history = []
        
        # Find all files for this URL
        for filename in os.listdir(SCHEMA_STORAGE_DIR):
            if filename.startswith(f"{url_hash}_") and filename.endswith(".json"):
                filepath = SCHEMA_STORAGE_DIR / filename
                
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        history.append(data)
                except Exception as e:
                    print(f"⚠️  Could not read history file {filename}: {e}")
        
        # Sort by timestamp (newest first) and limit
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return history[:limit]
        
    except Exception as e:
        print(f"❌ Failed to retrieve spec history: {e}")
        return []

def compare_specs(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare two API specs and identify changes.
    
    Args:
        old_spec: Previous version of the spec
        new_spec: Current version of the spec
        
    Returns:
        Dictionary containing detailed change analysis
    """
    print("🔍 Comparing API specifications...")
    
    changes = {
        "summary": {
            "parameters_added": 0,
            "parameters_removed": 0,
            "parameters_modified": 0,
            "endpoints_added": 0,
            "endpoints_removed": 0,
            "endpoints_modified": 0,
            "breaking_changes": 0,
            "non_breaking_changes": 0
        },
        "parameter_changes": {},
        "endpoint_changes": {},
        "breaking_changes": [],
        "non_breaking_changes": []
    }
    
    try:
        # Compare endpoints
        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})
        
        for path, old_path_spec in old_paths.items():
            if path in new_paths:
                # Endpoint exists in both - compare details
                new_path_spec = new_paths[path]
                path_changes = _compare_endpoint_specs(path, old_path_spec, new_path_spec)
                
                if path_changes["has_changes"]:
                    changes["endpoint_changes"][path] = path_changes
                    changes["summary"]["endpoints_modified"] += 1
                    
                    # Add breaking/non-breaking changes
                    for change in path_changes.get("breaking_changes", []):
                        changes["breaking_changes"].append(f"{path}: {change}")
                        changes["summary"]["breaking_changes"] += 1
                    
                    for change in path_changes.get("non_breaking_changes", []):
                        changes["non_breaking_changes"].append(f"{path}: {change}")
                        changes["summary"]["non_breaking_changes"] += 1
            else:
                # Endpoint removed
                changes["endpoint_changes"][path] = {
                    "change_type": "removed",
                    "methods": list(old_path_spec.keys())
                }
                changes["summary"]["endpoints_removed"] += 1
                changes["breaking_changes"].append(f"Endpoint {path} removed")
                changes["summary"]["breaking_changes"] += 1
        
        for path, new_path_spec in new_paths.items():
            if path not in old_paths:
                # New endpoint added
                changes["endpoint_changes"][path] = {
                    "change_type": "added",
                    "methods": list(new_path_spec.keys())
                }
                changes["summary"]["endpoints_added"] += 1
                changes["non_breaking_changes"].append(f"Endpoint {path} added")
                changes["summary"]["non_breaking_changes"] += 1
        
        # Compare parameters across all endpoints
        param_changes = _compare_parameters(old_spec, new_spec)
        changes["parameter_changes"] = param_changes
        changes["summary"]["parameters_added"] += len(param_changes.get("added", []))
        changes["summary"]["parameters_removed"] += len(param_changes.get("removed", []))
        changes["summary"]["parameters_modified"] += len(param_changes.get("modified", []))
        
        print(f"🎯 Spec comparison complete")
        print(f"   Breaking changes: {changes['summary']['breaking_changes']}")
        print(f"   Non-breaking changes: {changes['summary']['non_breaking_changes']}")
        
        return changes
        
    except Exception as e:
        print(f"❌ Spec comparison failed: {e}")
        return changes

def generate_evolution_report(changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive evolution report from spec changes.
    
    Args:
        changes: Output from compare_specs function
        
    Returns:
        Formatted evolution report
    """
    report = {
        "report_timestamp": datetime.now().isoformat(),
        "change_summary": changes["summary"],
        "impact_assessment": _assess_impact(changes),
        "recommendations": _generate_recommendations(changes),
        "detailed_changes": {
            "breaking_changes": changes["breaking_changes"],
            "non_breaking_changes": changes["non_breaking_changes"],
            "parameter_changes": changes["parameter_changes"],
            "endpoint_changes": changes["endpoint_changes"]
        }
    }
    
    return report

def _generate_spec_hash(spec: Dict[str, Any]) -> str:
    """Generate a hash of the spec content for version tracking."""
    spec_str = json.dumps(spec, sort_keys=True)
    return hashlib.sha256(spec_str.encode()).hexdigest()[:16]

def _count_parameters(spec: Dict[str, Any]) -> int:
    """Count total parameters in the spec."""
    count = 0
    paths = spec.get("paths", {})
    
    for path_spec in paths.values():
        for method_spec in path_spec.values():
            # Count parameters in parameters array
            params = method_spec.get("parameters", [])
            count += len(params)
            
            # Count parameters in request body
            request_body = method_spec.get("requestBody", {})
            content = request_body.get("content", {})
            for media_type in content.values():
                schema = media_type.get("schema", {})
                properties = schema.get("properties", {})
                count += len(properties)
    
    return count

def _count_endpoints(spec: Dict[str, Any]) -> int:
    """Count total endpoints (path + method combinations) in the spec."""
    count = 0
    paths = spec.get("paths", {})
    
    for path_spec in paths.values():
        # Count HTTP method entries (get, post, put, delete, etc.)
        methods = [k for k in path_spec.keys() if k.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]]
        count += len(methods)
    
    return count

def _compare_endpoint_specs(path: str, old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two endpoint specifications."""
    changes = {
        "has_changes": False,
        "methods_added": [],
        "methods_removed": [],
        "methods_modified": [],
        "breaking_changes": [],
        "non_breaking_changes": []
    }
    
    # Get all methods from both specs
    old_methods = set(k.lower() for k in old_spec.keys() if k.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    new_methods = set(k.lower() for k in new_spec.keys() if k.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    
    # Find added methods
    changes["methods_added"] = list(new_methods - old_methods)
    if changes["methods_added"]:
        changes["has_changes"] = True
        changes["non_breaking_changes"].extend([f"Method {method} added" for method in changes["methods_added"]])
    
    # Find removed methods
    changes["methods_removed"] = list(old_methods - new_methods)
    if changes["methods_removed"]:
        changes["has_changes"] = True
        changes["breaking_changes"].extend([f"Method {method} removed" for method in changes["methods_removed"]])
    
    # Find modified methods
    common_methods = old_methods & new_methods
    for method in common_methods:
        old_method_spec = old_spec[method]
        new_method_spec = new_spec[method]
        
        if old_method_spec != new_method_spec:
            changes["methods_modified"].append(method)
            changes["has_changes"] = True
            
            # Analyze what changed in the method
            method_changes = _compare_method_specs(method, old_method_spec, new_method_spec)
            changes["breaking_changes"].extend(method_changes["breaking"])
            changes["non_breaking_changes"].extend(method_changes["non_breaking"])
    
    return changes

def _compare_method_specs(method: str, old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two method specifications."""
    changes = {"breaking": [], "non_breaking": []}
    
    # Compare parameters
    old_params = _extract_method_parameters(old_spec)
    new_params = _extract_method_parameters(new_spec)
    
    # Check for removed parameters (breaking)
    removed_params = set(old_params.keys()) - set(new_params.keys())
    for param in removed_params:
        if old_params[param].get("required", False):
            changes["breaking"].append(f"Required parameter '{param}' removed from {method.upper()}")
        else:
            changes["non_breaking"].append(f"Optional parameter '{param}' removed from {method.upper()}")
    
    # Check for added parameters
    added_params = set(new_params.keys()) - set(old_params.keys())
    for param in added_params:
        if new_params[param].get("required", False):
            changes["breaking"].append(f"Required parameter '{param}' added to {method.upper()}")
        else:
            changes["non_breaking"].append(f"Optional parameter '{param}' added to {method.upper()}")
    
    # Check for modified parameters
    common_params = set(old_params.keys()) & set(new_params.keys())
    for param in common_params:
        old_param = old_params[param]
        new_param = new_params[param]
        
        if old_param != new_param:
            # Check for type changes (breaking)
            if old_param.get("type") != new_param.get("type"):
                changes["breaking"].append(f"Parameter '{param}' type changed from {old_param.get('type')} to {new_param.get('type')} in {method.upper()}")
            
            # Check for required changes (breaking if becoming required)
            old_required = old_param.get("required", False)
            new_required = new_param.get("required", False)
            if old_required != new_required:
                if new_required:
                    changes["breaking"].append(f"Parameter '{param}' became required in {method.upper()}")
                else:
                    changes["non_breaking"].append(f"Parameter '{param}' became optional in {method.upper()}")
    
    return changes

def _extract_method_parameters(method_spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract all parameters from a method specification."""
    params = {}
    
    # Parameters from parameters array
    for param in method_spec.get("parameters", []):
        param_name = param["name"]
        params[param_name] = {
            "type": param.get("type", "string"),
            "required": param.get("required", False),
            "in": param.get("in", "query")
        }
    
    # Parameters from request body
    request_body = method_spec.get("requestBody", {})
    content = request_body.get("content", {})
    for media_type, media_spec in content.items():
        schema = media_spec.get("schema", {})
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        for prop_name, prop_spec in properties.items():
            params[prop_name] = {
                "type": prop_spec.get("type", "string"),
                "required": prop_name in required_fields,
                "in": "body"
            }
    
    return params

def _compare_parameters(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Compare parameters across all endpoints."""
    old_params = _extract_all_parameters(old_spec)
    new_params = _extract_all_parameters(new_spec)
    
    return {
        "added": list(set(new_params.keys()) - set(old_params.keys())),
        "removed": list(set(old_params.keys()) - set(new_params.keys())),
        "modified": [p for p in set(old_params.keys()) & set(new_params.keys()) 
                     if old_params[p] != new_params[p]]
    }

def _extract_all_parameters(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract all parameters from all endpoints."""
    all_params = {}
    paths = spec.get("paths", {})
    
    for path, path_spec in paths.items():
        for method, method_spec in path_spec.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                method_params = _extract_method_parameters(method_spec)
                for param_name, param_spec in method_params.items():
                    # Create unique key for parameter
                    key = f"{path}:{method.upper()}:{param_name}"
                    all_params[key] = param_spec
    
    return all_params

def _assess_impact(changes: Dict[str, Any]) -> Dict[str, Any]:
    """Assess the impact of the changes."""
    summary = changes["summary"]
    
    impact = {
        "severity": "low",
        "client_compatibility": "compatible",
        "migration_required": False,
        "risk_score": 0
    }
    
    # Calculate risk score
    risk_score = 0
    risk_score += summary["breaking_changes"] * 10
    risk_score += summary["endpoints_removed"] * 8
    risk_score += summary["parameters_removed"] * 5
    risk_score += summary["parameters_modified"] * 2
    risk_score += summary["non_breaking_changes"] * 1
    
    impact["risk_score"] = risk_score
    
    # Determine severity
    if risk_score >= 20:
        impact["severity"] = "high"
        impact["client_compatibility"] = "incompatible"
        impact["migration_required"] = True
    elif risk_score >= 10:
        impact["severity"] = "medium"
        impact["client_compatibility"] = "partially_compatible"
    elif risk_score >= 5:
        impact["severity"] = "low"
    
    return impact

def _generate_recommendations(changes: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on the changes."""
    recommendations = []
    summary = changes["summary"]
    
    if summary["breaking_changes"] > 0:
        recommendations.append("Consider versioning the API due to breaking changes")
        recommendations.append("Update client libraries to handle removed/modified parameters")
        recommendations.append("Communicate breaking changes to API consumers")
    
    if summary["endpoints_removed"] > 0:
        recommendations.append("Implement deprecation warnings before removing endpoints")
    
    if summary["parameters_added"] > 0:
        recommendations.append("Document new parameters in API documentation")
    
    if summary["non_breaking_changes"] > 0:
        recommendations.append("Review non-breaking changes for potential optimization opportunities")
    
    if not recommendations:
        recommendations.append("No major issues detected - API evolution looks good")
    
    return recommendations

# Test function for development
if __name__ == "__main__":
    print("🧪 Testing Schema Evolution Module")
    print("=" * 50)
    
    # Test spec storage and comparison
    test_url = "https://api.example.com/users"
    
    # Create test specs
    old_spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "limit", "type": "integer", "required": False}
                    ]
                }
            }
        }
    }
    
    new_spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {"name": "limit", "type": "integer", "required": True},
                        {"name": "offset", "type": "integer", "required": False}
                    ]
                },
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Store and compare
    store_spec_version(test_url, old_spec, "2023-01-01T00:00:00")
    store_spec_version(test_url, new_spec, "2023-01-02T00:00:00")
    
    changes = compare_specs(old_spec, new_spec)
    report = generate_evolution_report(changes)
    
    print("\n" + "=" * 50)
    print("EVOLUTION REPORT:")
    print(f"Risk Score: {report['impact_assessment']['risk_score']}")
    print(f"Severity: {report['impact_assessment']['severity']}")
    print(f"Breaking Changes: {len(changes['breaking_changes'])}")
    print(f"Recommendations: {len(report['recommendations'])}")
