if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(backend_root.parent))
    __package__ = backend_root.name

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

# Import v2 architecture
from .models import DiscoveryRequest, AuthConfig
from .orchestrator.v2_orchestrator import create_v2_orchestrator

app = FastAPI(title="APISec Inference Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InferenceRequest(BaseModel):
    """Legacy inference request model for backward compatibility."""
    url: str = Field(..., description="Target API endpoint")
    method: str = Field(default="POST", description="HTTP method")
    time: int = Field(default=30, description="Maximum execution time in seconds")
    auth: Optional[AuthConfig] = Field(default=None, description="Authentication configuration")
    headers: dict[str, str] = Field(default_factory=dict, description="Custom headers")
    seed_body: Optional[dict] = Field(default=None, description="Seed request body")
    content_type_override: Optional[str] = Field(default=None, description="Content type override")

class HealthResponse(BaseModel):
    status: str
    version: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="0.1.0")

@app.post("/infer", response_model=dict)
async def inference_endpoint(request: InferenceRequest):
    """Enhanced parameter inference endpoint with v2 architecture."""
    try:
        # Create v2 discovery request
        discovery_request = DiscoveryRequest(
            url=request.url,
            method=request.method,
            timeout_seconds=request.time,
            auth=request.auth,
            headers=request.headers,
            seed_body=request.seed_body,
            content_type_override=request.content_type_override
        )
        
        # Validate request
        if not discovery_request.url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail={"error": "URL must start with http:// or https://"}
            )
        
        if discovery_request.timeout_seconds <= 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "Time must be positive"}
            )
        
        orchestrator = create_v2_orchestrator(enable_v2=True, fallback_to_v1_on_error=False)
        result = await orchestrator.discover_parameters(discovery_request)
        
        return result
        
    except HTTPException:
        # Re-raise FastAPI exceptions
        raise
    except Exception as e:
        # Return structured error for inference failures
        return {
            "url": request.url,
            "method": request.method,
            "parameters": [],
            "meta": {
                "total_parameters": 0,
                "partial_failures": 1,
                "execution_time_ms": 0,
                "error": str(e),
                "discovery_version": "v2"
            }
        }

@app.post("/spec", response_model=dict)
async def spec_endpoint(request: InferenceRequest):
    """Generate OpenAPI spec from v2 inference results."""
    try:
        # Create v2 discovery request
        discovery_request = DiscoveryRequest(
            url=request.url,
            method=request.method,
            timeout_seconds=request.time,
            auth=request.auth,
            headers=request.headers,
            seed_body=request.seed_body,
            content_type_override=request.content_type_override
        )
        
        # Validate request (same as /infer)
        if not discovery_request.url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail={"error": "URL must start with http:// or https://"}
            )
        
        if discovery_request.timeout_seconds <= 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "Time must be positive"}
            )
        
        orchestrator = create_v2_orchestrator(enable_v2=True, fallback_to_v1_on_error=False)
        inference_result = await orchestrator.discover_parameters(discovery_request)
        
        # Generate spec from v2 results
        from spec.generator import generate_spec
        spec = generate_spec(inference_result)
        
        return spec
        
    except HTTPException:
        raise
    except Exception as e:
        # Return structured error for spec generation failures
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Error",
                "version": "0.1.0",
                "description": f"Failed to generate spec: {str(e)}"
            },
            "paths": {},
            "error": str(e),
            "discovery_version": "v2"
        }

if __name__ == "__main__":
    print("🚀 Starting APISec Inference Service")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /infer - Run parameter inference")
    print("  POST /spec  - Generate OpenAPI spec")
    print("\nStarting server on http://127.0.0.1:8000")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
