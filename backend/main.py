from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
from pydantic import BaseModel
from typing import Optional
from schema_monitor import crawl_for_schema, generate_pdf_from_json, compare_schemas, compare_schemas_structured
from probes.differential_engine import DifferentialEngine
from fingerprint import create_fingerprint, compare_fingerprints
from runtime_validator import create_runtime_validator
from models import DiscoveryRequest
from models_runtime import (
    RuntimeValidationRequest, 
    RuntimeValidationResponse, 
    EndpointTestResult
)
from registry_db import init_db, ApiRegistry, SchemaSnapshot
import sys
import os

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Schema Discovery & Diffing")

# Initialize database
init_db()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/validate-runtime")
async def validate_runtime_endpoint(request: RuntimeValidationRequest):
    """
    Validate API schema against runtime behavior.
    
    Args:
        request: RuntimeValidationRequest containing base URL and schema info
        
    Returns:
        JSON with runtime validation results
    """
    try:
        logger.info(f"Starting runtime validation for URL: {request.base_url}")
        
        # Create runtime validator
        validator = create_runtime_validator()
        
        # Perform validation
        result = await validator.validate_schema(request.base_url, request.schema_info)
        
        # Convert endpoint tests to response models
        endpoint_tests = []
        for test in result.endpoint_tests:
            endpoint_test = EndpointTestResult(
                method=test.method,
                path=test.path,
                url=test.url,
                expected_status=test.expected_status,
                actual_status=test.actual_status,
                expected_response_schema=test.expected_response_schema,
                actual_response=test.actual_response,
                response_time_ms=test.response_time_ms,
                error=test.error,
                status_mismatch=test.status_mismatch,
                schema_mismatch=test.schema_mismatch,
                validation_passed=test.validation_passed
            )
            endpoint_tests.append(endpoint_test)
        
        # Generate summary
        summary = f"Runtime validation completed: {result.passed_endpoints}/{result.tested_endpoints} endpoints passed"
        if result.failed_endpoints > 0:
            summary += f", {result.failed_endpoints} endpoints failed"
        
        response = RuntimeValidationResponse(
            base_url=result.base_url,
            total_endpoints=result.total_endpoints,
            tested_endpoints=result.tested_endpoints,
            passed_endpoints=result.passed_endpoints,
            failed_endpoints=result.failed_endpoints,
            endpoint_tests=endpoint_tests,
            validation_timestamp=result.validation_timestamp,
            overall_status=result.overall_status,
            summary=summary
        )
        
        return {
            "status": "success",
            "validation_result": response.dict()
        }
        
    except Exception as e:
        logger.error(f"Runtime validation failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Runtime validation failed: {str(e)}"}
        )

@app.post("/discover-schema")
async def discover_schema_endpoint(request: DiscoveryRequest):
    """
    Discover API schema from given URL.
    
    Args:
        request: DiscoverRequest containing the target URL
        
    Returns:
        JSON with discovered schema information
    """
    try:
        logger.info(f"Starting schema discovery for URL: {request.url}")
        
        # Discover schema
        schema_info, schema_url = crawl_for_schema(request.url)
        
        if schema_info:
            return {
                "status": "success",
                "schema": schema_info,
                "schema_url": schema_url,
                "url": request.url
            }
        else:
            return {
                "status": "not_found",
                "message": "No schema found at the given URL",
                "url": request.url
            }
        
    except Exception as e:
        logger.error(f"Schema discovery failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Schema discovery failed: {str(e)}"}
        )

@app.post("/analyze-diff")
async def analyze_diff_endpoint(
    base_url: str,
    new_url: str
):
    """
    Perform differential analysis between two API endpoints.
    
    Args:
        base_url: Base API endpoint URL
        new_url: New API endpoint URL to compare
        
    Returns:
        JSON with differential analysis results
    """
    try:
        logger.info(f"Starting differential analysis between {base_url} and {new_url}")
        
        # Create differential engine
        diff_engine = DifferentialEngine()
        
        # Perform analysis (this would need actual implementation)
        # For now, return a placeholder response
        return {
            "status": "success",
            "base_url": base_url,
            "new_url": new_url,
            "message": "Differential analysis functionality - needs implementation"
        }
        
    except Exception as e:
        logger.error(f"Differential analysis failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Differential analysis failed: {str(e)}"}
        )

# Schema Monitor Endpoints
@app.get("/api/apis")
async def get_apis():
    """Get all registered APIs"""
    try:
        apis = ApiRegistry.get_all()
        return {
            "status": "success",
            "apis": apis
        }
    except Exception as e:
        logger.error(f"Failed to get APIs: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get APIs: {str(e)}"}
        )

@app.get("/api/apis/{api_id}/schemas")
async def get_api_schemas(api_id: int):
    """Get all schema versions for a specific API"""
    try:
        schemas = SchemaSnapshot.get_by_api(api_id)
        return {
            "status": "success",
            "schemas": schemas
        }
    except Exception as e:
        logger.error(f"Failed to get API schemas: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get API schemas: {str(e)}"}
        )

@app.get("/api/apis/{api_id}/schemas/latest")
async def get_latest_schema(api_id: int):
    """Get the latest schema version for a specific API"""
    try:
        schema = SchemaSnapshot.get_latest(api_id)
        if not schema:
            return JSONResponse(
                status_code=404,
                content={"error": "No schemas found for this API"}
            )
        return {
            "status": "success",
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Failed to get latest schema: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get latest schema: {str(e)}"}
        )

@app.post("/api/apis/{api_id}/scan")
async def scan_api_schema(api_id: int):
    """Scan an API for schema changes and store new version if different"""
    try:
        # Get API details
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(
                status_code=404,
                content={"error": "API not found"}
            )
        
        # Discover new schema
        schema_info, schema_url = crawl_for_schema(api['base_url'])
        
        if not schema_info:
            return {
                "status": "no_schema",
                "message": "No schema found at the given URL"
            }
        
        # Use the new duplicate detection method
        result = SchemaSnapshot.create_if_different(api_id, schema_info)
        
        if result['status'] == 'unchanged':
            return {
                "status": "unchanged",
                "message": "Schema has not changed",
                "schema": result['schema']['schema_json'],
                "schema_url": schema_url
            }
        
        # Generate PDF for new schema
        schema_pdf = generate_pdf_from_json(schema_info)
        
        # Update the result with PDF
        SchemaSnapshot.update_pdf(result['id'], schema_pdf)
        
        return {
            "status": "success",
            "message": "New schema version stored",
            "schema": schema_info,
            "schema_url": schema_url,
            "snapshot": result
        }
        
    except Exception as e:
        logger.error(f"Failed to scan API schema: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to scan API schema: {str(e)}"}
        )

@app.post("/api/apis")
async def create_api(
    name: str = Form(...),
    base_url: str = Form(...),
    description: Optional[str] = Form(None)
):
    """Create a new API entry for monitoring"""
    try:
        # Check if API with this URL already exists
        existing_api = ApiRegistry.get_by_url(base_url)
        if existing_api:
            return {
                "status": "exists",
                "message": "API with this URL already exists",
                "api": existing_api
            }
        
        api = ApiRegistry.create(name=name, base_url=base_url, description=description)
        return {
            "status": "success",
            "api": api
        }
    except Exception as e:
        logger.error(f"Failed to create API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to create API: {str(e)}"}
        )

@app.get("/api/schemas/{api_id}/compare/{version1}/{version2}")
async def compare_schema_versions(api_id: int, version1: int, version2: int, structured: bool = False):
    """Compare two schema versions"""
    try:
        schema1 = SchemaSnapshot.get_by_version(api_id, version1)
        schema2 = SchemaSnapshot.get_by_version(api_id, version2)
        
        if not schema1 or not schema2:
            return JSONResponse(
                status_code=404,
                content={"error": "One or both schema versions not found"}
            )
        
        if structured:
            # Use new structured format with summary
            result = compare_schemas_structured(schema1['schema_json'], schema2['schema_json'])
            return {
                "status": "success",
                "summary": result["summary"],
                "changes": result["changes"],
                "schema1": {
                    "version": version1,
                    "timestamp": schema1['timestamp']
                },
                "schema2": {
                    "version": version2,
                    "timestamp": schema2['timestamp']
                }
            }
        else:
            # Use original format for backward compatibility
            changes = compare_schemas(schema1['schema_json'], schema2['schema_json'])
            return {
                "status": "success",
                "changes": changes,
                "schema1": {
                    "version": version1,
                    "timestamp": schema1['timestamp']
                },
                "schema2": {
                    "version": version2,
                    "timestamp": schema2['timestamp']
                }
            }
        
    except Exception as e:
        logger.error(f"Failed to compare schemas: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to compare schemas: {str(e)}"}
        )

@app.get("/api/schemas/{api_id}/version/{version}")
async def get_schema_version(api_id: int, version: int):
    """Get a specific schema version for detailed comparison"""
    try:
        schema = SchemaSnapshot.get_by_version(api_id, version)
        if not schema:
            return JSONResponse(
                status_code=404,
                content={"error": "Schema version not found"}
            )
        return {
            "status": "success",
            "schema": schema
        }
    except Exception as e:
        logger.error(f"Failed to get schema version: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get schema version: {str(e)}"}
        )

@app.delete("/api/apis/{api_id}")
async def delete_api(api_id: int):
    """Delete an API and all its schema versions"""
    try:
        # Check if API exists
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(
                status_code=404,
                content={"error": "API not found"}
            )
        
        # Delete API (cascade will delete schema snapshots)
        success = ApiRegistry.delete(api_id)
        
        if success:
            return {
                "status": "success",
                "message": "API and all schema versions deleted successfully"
            }
        else:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to delete API"}
            )
        
    except Exception as e:
        logger.error(f"Failed to delete API: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to delete API: {str(e)}"}
        )

# Mount static files to serve frontend
# app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
