from typing import Dict, Any
from inference.orchestrator import orchestrate_inference

def run_inference(url: str, method: str, max_time_seconds: int = 30) -> Dict[str, Any]:
    """
    Run complete parameter inference orchestration.
    
    Args:
        url: Target API endpoint
        method: HTTP method
        max_time_seconds: Maximum execution time
        
    Returns:
        Complete inference result from orchestrator
    """
    try:
        result = orchestrate_inference(url, method, max_time_seconds)
        return result
    except Exception as e:
        return {
            "url": url,
            "method": method,
            "parameters": [],
            "meta": {
                "total_parameters": 0,
                "partial_failures": 1,
                "execution_time_ms": 0,
                "error": str(e)
            }
        }
