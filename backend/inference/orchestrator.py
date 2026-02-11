import time
from typing import Dict, Any, List, Optional
from .error_probe import infer_parameters
from .type_probe import infer_parameter_type

def _merge_parameter_info(existing_info: Dict[str, Any], type_info: Dict[str, Any]) -> Dict[str, Any]:
    """Merge existing parameter info with type inference results."""
    merged = existing_info.copy()
    
    # Add type information if available
    if type_info.get("type") != "unknown":
        merged["type"] = type_info["type"]
        merged["nullable"] = type_info.get("nullable", False)
    
    # Combine evidence
    existing_evidence = existing_info.get("evidence", [])
    type_evidence = type_info.get("evidence", [])
    merged["evidence"] = existing_evidence + type_evidence
    
    return merged

def orchestrate_inference(
    url: str, 
    method: str = "POST", 
    max_time_seconds: int = 30
) -> Dict[str, Any]:
    """
    Orchestrate parameter inference with time bounds and safety constraints.
    
    Args:
        url: Target API endpoint
        method: HTTP method ("GET" or "POST")
        max_time_seconds: Maximum execution time in seconds
        
    Returns:
        Dictionary with aggregated results and metadata
    """
    print(f"🚀 Starting Parameter Inference Orchestration")
    print(f"Target: {url}")
    print(f"Method: {method}")
    print(f"Time limit: {max_time_seconds}s")
    print("=" * 60)
    
    start_time = time.time()
    discovered_params = {}
    partial_failures = 0
    total_parameters = 0
    
    try:
        # Step 1: Error-based parameter discovery
        print("\n🔍 Step 1: Error-based parameter discovery...")
        error_probe_start = time.time()
        
        error_result = infer_parameters(url, method, max_rounds=3)
        error_probe_time = time.time() - error_probe_start
        
        print(f"   Completed in {error_probe_time:.1f}s")
        
        if error_result:
            discovered_params.update(error_result)
            total_parameters += len(error_result)
            print(f"   Discovered {len(error_result)} parameters via error analysis")
        else:
            print("   No parameters discovered via error analysis")
        
        # Step 2: Type inference for each discovered parameter
        print(f"\n🧪 Step 2: Type inference for {len(discovered_params)} parameters...")
        type_inference_start = time.time()
        
        for param_name in discovered_params.keys():
            # Check time limit
            elapsed_time = time.time() - start_time
            remaining_time = max_time_seconds - elapsed_time
            
            if remaining_time <= 0:
                print(f"   ⏰ Time limit reached, stopping type inference")
                break
            
            print(f"   Inferring type for: {param_name} (remaining: {remaining_time:.1f}s)")
            
            try:
                # Run type inference with time limit
                type_result = infer_parameter_type(
                    url, method, param_name, 
                    timeout=min(5, remaining_time)
                )
                
                if type_result:
                    # Merge with existing parameter info
                    existing_info = discovered_params[param_name]
                    merged_info = _merge_parameter_info(existing_info, type_result)
                    
                    # Update parameter with type information
                    discovered_params[param_name] = merged_info
                    
                    print(f"     ✅ Type: {type_result.get('type', 'unknown')} (confidence: {merged_info.get('confidence', 0.0):.2f})")
                else:
                    print(f"     ❌ Type inference failed for {param_name}")
                    partial_failures += 1
                    
            except Exception as e:
                print(f"     ⚠️  Type inference error for {param_name}: {e}")
                partial_failures += 1
        
        type_inference_time = time.time() - type_inference_start
        total_time = time.time() - start_time
        
        # Build final result
        result = {
            "url": url,
            "method": method,
            "parameters": [],
            "meta": {
                "total_parameters": total_parameters,
                "partial_failures": partial_failures,
                "execution_time_ms": int(total_time * 1000),
                "error_probe_time_ms": int(error_probe_time * 1000),
                "type_inference_time_ms": int(type_inference_time * 1000),
                "time_limit_seconds": max_time_seconds
            }
        }
        
        # Add parameters to result
        for param_name, param_info in discovered_params.items():
            result["parameters"].append({
                "name": param_name,
                "location": param_info.get("location", "body"),
                "required": param_info.get("required", False),
                "type": param_info.get("type", "unknown"),
                "nullable": param_info.get("nullable", False),
                "confidence": param_info.get("confidence", 0.0),
                "evidence": param_info.get("evidence", [])
            })
        
        print(f"\n🎯 Orchestration Complete!")
        print(f"   Total parameters: {total_parameters}")
        print(f"   Partial failures: {partial_failures}")
        print(f"   Execution time: {total_time:.1f}s")
        print(f"   Time used: {(total_time/max_time_seconds)*100:.1f}%")
        
        return result
        
    except Exception as e:
        print(f"\n💥 Orchestration failed: {e}")
        return {
            "url": url,
            "method": method,
            "parameters": [],
            "meta": {
                "total_parameters": 0,
                "partial_failures": 1,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
        }

def _merge_parameter_info(existing_info: Dict[str, Any], type_info: Dict[str, Any]) -> Dict[str, Any]:
    """Merge existing parameter info with type inference results."""
    merged = existing_info.copy()
    
    # Add type information if available
    if type_info.get("type") != "unknown":
        merged["type"] = type_info["type"]
        merged["nullable"] = type_info.get("nullable", False)
    
    # Combine evidence
    existing_evidence = existing_info.get("evidence", [])
    type_evidence = type_info.get("evidence", [])
    merged["evidence"] = existing_evidence + type_evidence
    
    return merged

# Test function for development
if __name__ == "__main__":
    # Test with a local endpoint
    test_url = "http://127.0.0.1:8002/api/typed"
    
    print("🧪 Testing Inference Orchestrator")
    print("=" * 50)
    
    # Test case 1: Normal operation
    print("\nTest 1: Normal operation (should succeed)")
    result1 = orchestrate_inference(test_url, "POST", 30)
    print("Result 1:")
    print(f"  Parameters: {len(result1['parameters'])}")
    print(f"  Time: {result1['meta']['execution_time_ms']}ms")
    
    # Test case 2: Time limit (should stop early)
    print("\nTest 2: Time limit (should stop early)")
    result2 = orchestrate_inference(test_url, "POST", 5)
    print("Result 2:")
    print(f"  Parameters: {len(result2['parameters'])}")
    print(f"  Time: {result2['meta']['execution_time_ms']}ms")
    print(f"  Time used: {(result2['meta']['execution_time_ms']/50000)*100:.1f}%")
