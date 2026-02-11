from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from app import run_inference
from spec.generator import generate_spec

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
    url: str = Field(..., description="Target API endpoint")
    method: str = Field(default="POST", description="HTTP method")
    time: int = Field(default=30, description="Maximum execution time in seconds")

class HealthResponse(BaseModel):
    status: str
    version: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="0.1.0")

@app.post("/infer", response_model=dict)
async def inference_endpoint(request: InferenceRequest):
    """Main inference endpoint"""
    try:
        # Validate URL format
        if not request.url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail={"error": "URL must start with http:// or https://"}
            )
        
        # Validate time
        if request.time <= 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "Time must be positive"}
            )
        
        # Validate method
        if request.method.upper() not in ["GET", "POST"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Method must be GET or POST"}
            )
        
        # Run inference
        result = run_inference(request.url, request.method, request.time)
        
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
                "error": str(e)
            }
        }

@app.post("/spec", response_model=dict)
async def spec_endpoint(request: InferenceRequest):
    """Generate OpenAPI spec from inference results"""
    try:
        # Validate request (same as /infer)
        if not request.url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail={"error": "URL must start with http:// or https://"}
            )
        
        if request.time <= 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "Time must be positive"}
            )
        
        if request.method.upper() not in ["GET", "POST"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Method must be GET or POST"}
            )
        
        # Run inference first
        inference_result = run_inference(request.url, request.method, request.time)
        
        # Generate OpenAPI spec
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
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 Starting APISec Inference Service")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /infer - Run parameter inference")
    print("  POST /spec  - Generate OpenAPI spec")
    print("\nStarting server on http://127.0.0.1:8000")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
