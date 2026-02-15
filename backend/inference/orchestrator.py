import time
from typing import Dict, Any, List, Optional
from .error_probe import infer_parameters
from .type_probe import infer_parameter_type
from .content_type_probe import detect_content_type, adapt_probe_strategy
from .binary_probe import infer_file_parameters
from .classifier import classify_endpoint, select_strategy

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
    Orchestrate adaptive parameter inference with content-type detection and endpoint classification.
    
    Args:
        url: Target API endpoint
        method: HTTP method ("GET" or "POST")
        max_time_seconds: Maximum execution time in seconds
        
    Returns:
        Dictionary with aggregated results and metadata
    """
    print(f"🚀 Starting Adaptive Parameter Inference Orchestration")
    print(f"Target: {url}")
    print(f"Method: {method}")
    print(f"Time limit: {max_time_seconds}s")
    print("=" * 60)
    
    start_time = time.time()
    discovered_params = {}
    partial_failures = 0
    total_parameters = 0
    metadata = {}
    
    try:
        # Phase 1: Transport-Layer Inference
        print("\n🌐 Phase 1: Transport-Layer Inference...")
        
        # Step 1.1: Content-Type Detection
        print("1️⃣ Detecting content types...")
        content_type_start = time.time()
        content_type_result = detect_content_type(url, timeout=min(5, max_time_seconds))
        content_type_time = time.time() - content_type_start
        
        detected_content_type = content_type_result.get("preferred_strategy", "json")
        metadata["content_type_detection"] = {
            "detected_types": content_type_result.get("detected_content_types", []),
            "preferred_strategy": detected_content_type,
            "confidence": content_type_result.get("confidence", 0.0),
            "execution_time_ms": int(content_type_time * 1000)
        }
        
        print(f"   Detected content type: {detected_content_type}")
        print(f"   Confidence: {content_type_result.get('confidence', 0.0):.2f}")
        
        # Step 1.2: Endpoint Classification
        print("2️⃣ Classifying endpoint...")
        classification_start = time.time()
        endpoint_type = classify_endpoint(url, method)
        classification_time = time.time() - classification_start
        
        strategy = select_strategy(endpoint_type)
        metadata["endpoint_classification"] = {
            "endpoint_type": endpoint_type,
            "strategy": strategy,
            "execution_time_ms": int(classification_time * 1000)
        }
        
        print(f"   Endpoint type: {endpoint_type}")
        print(f"   Strategy: {strategy['priority']}")
        
        # Phase 2: Schema Inference
        print(f"\n🔍 Phase 2: Schema Inference...")
        
        # Step 2.1: Adaptive Parameter Discovery
        print("3️⃣ Adaptive parameter discovery...")
        discovery_start = time.time()
        
        # Choose discovery method based on strategy
        if endpoint_type == "upload":
            # Use binary probe for upload endpoints
            print("   Using binary probe for upload endpoint...")
            discovery_result = infer_file_parameters(url, method, timeout=min(10, max_time_seconds - (time.time() - start_time)))
        else:
            # Use error probe with appropriate content type
            print(f"   Using error probe with content type: {strategy['content_type']}...")
            discovery_result = infer_parameters(
                url, method, 
                max_rounds=strategy.get("max_rounds", 3),
                content_type=strategy["content_type"]
            )
        
        discovery_time = time.time() - discovery_start
        
        if discovery_result:
            discovered_params.update(discovery_result)
            total_parameters += len(discovery_result)
            print(f"   Discovered {len(discovery_result)} parameters")
        else:
            print("   No parameters discovered")
        
        metadata["parameter_discovery"] = {
            "method": "binary_probe" if endpoint_type == "upload" else "error_probe",
            "content_type": strategy["content_type"],
            "execution_time_ms": int(discovery_time * 1000)
        }
        
        # Step 2.2: Type Inference (skip for upload endpoints as binary_probe handles types)
        if endpoint_type != "upload" and discovered_params:
            print(f"4️⃣ Type inference for {len(discovered_params)} parameters...")
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
            metadata["type_inference"] = {
                "execution_time_ms": int(type_inference_time * 1000)
            }
        
        # Calculate total execution time
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
                "time_limit_seconds": max_time_seconds,
                "adaptive_inference": metadata
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
        
        print(f"\n🎯 Adaptive Orchestration Complete!")
        print(f"   Total parameters: {total_parameters}")
        print(f"   Partial failures: {partial_failures}")
        print(f"   Execution time: {total_time:.1f}s")
        print(f"   Time used: {(total_time/max_time_seconds)*100:.1f}%")
        print(f"   Endpoint type: {endpoint_type}")
        print(f"   Content type: {detected_content_type}")
        
        return result
        
    except Exception as e:
        print(f"\n💥 Adaptive orchestration failed: {e}")
        return {
            "url": url,
            "method": method,
            "parameters": [],
            "meta": {
                "total_parameters": 0,
                "partial_failures": 1,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
                "adaptive_inference": metadata
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
