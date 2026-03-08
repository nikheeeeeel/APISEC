from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
import json
import logging
import base64
import uvicorn
from typing import Optional
import asyncio
import io
from registry_db import init_db, ApiRegistry, SchemaSnapshot
from schema_monitor import crawl_for_schema, compare_schemas, generate_pdf_from_json

# Import v2 architecture for inference endpoints
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import DiscoveryRequest, AuthConfig
from backend.orchestrator.v2_orchestrator import create_v2_orchestrator
from spec.generator import generate_spec

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class ApiCreateRequest(BaseModel):
    name: str
    base_url: str
    description: Optional[str] = None

class ApiUpdateRequest(BaseModel):
    name: str
    base_url: str
    description: Optional[str] = None

class InferenceRequest(BaseModel):
    url: str = Field(..., description="Target API endpoint")
    method: str = Field(default="POST", description="HTTP method")
    time: int = Field(default=30, description="Maximum execution time in seconds")
    auth: Optional[AuthConfig] = Field(default=None, description="Authentication configuration")
    headers: dict[str, str] = Field(default_factory=dict, description="Custom headers")
    seed_body: Optional[dict] = Field(default=None, description="Seed request body")
    content_type_override: Optional[str] = Field(default=None, description="Content type override")

app = FastAPI(title="APISec - Full Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

# Inference Endpoints
@app.post("/infer", response_model=dict)
async def inference_endpoint(request: InferenceRequest):
    try:
        discovery_request = DiscoveryRequest(
            url=request.url,
            method=request.method,
            timeout_seconds=request.time,
            auth=request.auth,
            headers=request.headers,
            seed_body=request.seed_body,
            content_type_override=request.content_type_override
        )
        
        if not discovery_request.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail={"error": "URL must start with http:// or https://"})
        
        if discovery_request.timeout_seconds <= 0:
            raise HTTPException(status_code=400, detail={"error": "Time must be positive"})
        
        orchestrator = create_v2_orchestrator(enable_v2=True, fallback_to_v1_on_error=False)
        result = await orchestrator.discover_parameters(discovery_request)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
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
    try:
        discovery_request = DiscoveryRequest(
            url=request.url,
            method=request.method,
            timeout_seconds=request.time,
            auth=request.auth,
            headers=request.headers,
            seed_body=request.seed_body,
            content_type_override=request.content_type_override
        )
        
        if not discovery_request.url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail={"error": "URL must start with http:// or https://"})
        
        if discovery_request.timeout_seconds <= 0:
            raise HTTPException(status_code=400, detail={"error": "Time must be positive"})
        
        orchestrator = create_v2_orchestrator(enable_v2=True, fallback_to_v1_on_error=False)
        inference_result = await orchestrator.discover_parameters(discovery_request)
        
        spec = generate_spec(inference_result)
        return spec
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "openapi": "3.0.0",
            "info": {"title": "Error", "version": "0.1.0", "description": f"Failed to generate spec: {str(e)}"},
            "paths": {},
            "error": str(e),
            "discovery_version": "v2"
        }

# API Registry Endpoints
@app.get("/apis")
async def get_apis():
    try:
        apis = ApiRegistry.get_all()
        return {"apis": apis}
    except Exception as e:
        logger.error(f"Error getting APIs: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/apis")
async def create_api(request: ApiCreateRequest):
    try:
        api = ApiRegistry.create(request.name, request.base_url, request.description)
        return {"api": api}
    except Exception as e:
        logger.error(f"Error creating API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/apis/{api_id}")
async def get_api(api_id: int):
    try:
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        return {"api": api}
    except Exception as e:
        logger.error(f"Error getting API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.put("/apis/{api_id}")
async def update_api(api_id: int, request: ApiUpdateRequest):
    try:
        success = ApiRegistry.update(api_id, request.name, request.base_url, request.description)
        if not success:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        api = ApiRegistry.get_by_id(api_id)
        return {"api": api}
    except Exception as e:
        logger.error(f"Error updating API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/apis/{api_id}")
async def delete_api(api_id: int):
    try:
        success = ApiRegistry.delete(api_id)
        if not success:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        return {"message": "API deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/apis/{api_id}/scan")
async def scan_api(api_id: int):
    try:
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        
        base_url = api['base_url']
        
        schema, found_url = crawl_for_schema(base_url)
        
        if not schema:
            return JSONResponse(status_code=404, content={
                "error": "Schema Not Found",
                "message": "No OpenAPI/Swagger schema found at common paths"
            })
        
        pdf_base64 = generate_pdf_from_json(schema)
        
        snapshot = SchemaSnapshot.create(api_id, schema, pdf_base64)
        
        return {
            "message": "Schema scan completed successfully",
            "schema_url": found_url,
            "snapshot": snapshot
        }
        
    except Exception as e:
        logger.error(f"Error scanning API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/apis/{api_id}/rescan")
async def rescan_api(api_id: int):
    try:
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        
        base_url = api['base_url']
        
        schema, found_url = crawl_for_schema(base_url)
        
        if not schema:
            return JSONResponse(status_code=404, content={
                "error": "Schema Not Found",
                "message": "No OpenAPI/Swagger schema found at common paths"
            })
        
        latest_snapshot = SchemaSnapshot.get_latest(api_id)
        changes = []
        
        if latest_snapshot:
            old_schema = latest_snapshot['schema_json']
            changes = compare_schemas(old_schema, schema)
            
            if not changes:
                return {
                    "message": "No Changes Detected",
                    "identical": True,
                    "changes": []
                }
        
        pdf_base64 = generate_pdf_from_json(schema)
        
        snapshot = SchemaSnapshot.create(api_id, schema, pdf_base64)
        
        return {
            "message": "New schema version stored",
            "identical": False,
            "changes": changes if latest_snapshot else [],
            "snapshot": snapshot
        }
        
    except Exception as e:
        logger.error(f"Error rescanning API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/apis/{api_id}/scan/stream")
async def scan_api_stream(api_id: int):
    """Streaming SSE endpoint for schema scanning with progress updates."""
    
    async def event_stream():
        try:
            api = ApiRegistry.get_by_id(api_id)
            if not api:
                yield f"event: error\ndata: {json.dumps({'error': 'API not found'})}\n\n"
                return
            
            base_url = api['base_url']
            
            progress_queue = asyncio.Queue()
            
            def progress_callback(status: str, path: str, progress: int, total: int):
                asyncio.create_task(progress_queue.put({
                    'status': status,
                    'path': path,
                    'progress': progress,
                    'total': total
                }))
            
            async def progress_reader():
                while True:
                    try:
                        data = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                        yield f"event: progress\ndata: {json.dumps(data)}\n\n"
                    except asyncio.TimeoutError:
                        if crawl_done:
                            break
            
            crawl_done = False
            
            async def run_crawl():
                nonlocal crawl_done
                try:
                    schema, found_url = await asyncio.to_thread(
                        crawl_for_schema,
                        base_url,
                        timeout=3.0,
                        progress_callback=progress_callback
                    )
                    
                    if not schema:
                        yield f"event: error\ndata: {json.dumps({'error': 'Schema Not Found', 'message': 'No OpenAPI/Swagger schema found at common paths'})}\n\n"
                        crawl_done = True
                        return
                    
                    pdf_base64 = generate_pdf_from_json(schema)
                    snapshot = SchemaSnapshot.create(api_id, schema, pdf_base64)
                    
                    yield f"event: complete\ndata: {json.dumps({'message': 'Schema scan completed successfully', 'schema_url': found_url, 'snapshot': snapshot})}\n\n"
                except Exception as e:
                    logger.error(f"Error in crawl: {e}")
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                finally:
                    crawl_done = True
            
            crawl_task = asyncio.create_task(run_crawl())
            
            while not crawl_done or not progress_queue.empty():
                try:
                    data = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                    yield f"event: progress\ndata: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    if crawl_done:
                        break
            
            await crawl_task
            
        except Exception as e:
            logger.error(f"Error in streaming scan: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/apis/{api_id}/rescan/stream")
async def rescan_api_stream(api_id: int):
    """Streaming SSE endpoint for schema rescanning with progress updates."""
    
    async def event_stream():
        try:
            api = ApiRegistry.get_by_id(api_id)
            if not api:
                yield f"event: error\ndata: {json.dumps({'error': 'API not found'})}\n\n"
                return
            
            base_url = api['base_url']
            
            progress_queue = asyncio.Queue()
            crawl_result = {}
            crawl_error = {}
            
            def progress_callback(status: str, path: str, progress: int, total: int):
                asyncio.create_task(progress_queue.put({
                    'status': status,
                    'path': path,
                    'progress': progress,
                    'total': total
                }))
            
            def run_crawl():
                try:
                    schema, found_url = crawl_for_schema(
                        base_url, 
                        timeout=3.0,
                        progress_callback=progress_callback
                    )
                    crawl_result['schema'] = schema
                    crawl_result['found_url'] = found_url
                except Exception as e:
                    crawl_error['error'] = str(e)
            
            crawl_done = False
            
            await asyncio.to_thread(run_crawl)
            
            while not progress_queue.empty():
                data = await progress_queue.get()
                yield f"event: progress\ndata: {json.dumps(data)}\n\n"
            
            if 'error' in crawl_error:
                yield f"event: error\ndata: {json.dumps({'error': crawl_error['error']})}\n\n"
                return
            
            schema = crawl_result.get('schema')
            found_url = crawl_result.get('found_url')
            
            if not schema:
                yield f"event: error\ndata: {json.dumps({'error': 'Schema Not Found', 'message': 'No OpenAPI/Swagger schema found at common paths'})}\n\n"
                return
            
            latest_snapshot = SchemaSnapshot.get_latest(api_id)
            changes = []
            
            if latest_snapshot:
                old_schema = latest_snapshot['schema_json']
                changes = compare_schemas(old_schema, schema)
                
                if not changes:
                    yield f"event: complete\ndata: {json.dumps({'message': 'No Changes Detected', 'identical': True, 'changes': []})}\n\n"
                    return
            
            pdf_base64 = generate_pdf_from_json(schema)
            snapshot = SchemaSnapshot.create(api_id, schema, pdf_base64)
            
            yield f"event: complete\ndata: {json.dumps({'message': 'New schema version stored', 'identical': False, 'changes': changes if latest_snapshot else [], 'snapshot': snapshot})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in streaming rescan: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/apis/{api_id}/schemas")
async def get_schema_versions(api_id: int):
    try:
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        
        snapshots = SchemaSnapshot.get_by_api(api_id)
        
        return {"api": api, "snapshots": snapshots}
        
    except Exception as e:
        logger.error(f"Error getting schemas: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/apis/{api_id}/schemas/{version}")
async def get_schema_version(api_id: int, version: int):
    try:
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        
        snapshot = SchemaSnapshot.get_by_version(api_id, version)
        if not snapshot:
            return JSONResponse(status_code=404, content={"error": "Schema version not found"})
        
        return {"snapshot": snapshot}
        
    except Exception as e:
        logger.error(f"Error getting schema version: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/apis/{api_id}/compare")
async def compare_schemas_endpoint(api_id: int, from_version: int, to_version: int):
    try:
        api = ApiRegistry.get_by_id(api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        
        old_snapshot = SchemaSnapshot.get_by_version(api_id, from_version)
        new_snapshot = SchemaSnapshot.get_by_version(api_id, to_version)
        
        if not old_snapshot or not new_snapshot:
            return JSONResponse(status_code=404, content={"error": "One or both schema versions not found"})
        
        changes = compare_schemas(old_snapshot['schema_json'], new_snapshot['schema_json'])
        
        return {
            "from_version": from_version,
            "to_version": to_version,
            "identical": len(changes) == 0,
            "changes": changes
        }
        
    except Exception as e:
        logger.error(f"Error comparing schemas: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/apis/{api_id}/schemas/{version}/download")
async def download_schema(api_id: int, version: int):
    try:
        snapshot = SchemaSnapshot.get_by_version(api_id, version)
        if not snapshot:
            return JSONResponse(status_code=404, content={"error": "Schema version not found"})
        
        schema_json = json.dumps(snapshot['schema_json'], indent=2)
        
        return Response(
            content=schema_json,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=schema_v{version}.json"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading schema: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/apis/{api_id}/schemas/{version}/pdf")
async def download_pdf(api_id: int, version: int):
    try:
        snapshot = SchemaSnapshot.get_by_version(api_id, version)
        if not snapshot:
            return JSONResponse(status_code=404, content={"error": "Schema version not found"})
        
        if not snapshot.get('schema_pdf'):
            return JSONResponse(status_code=404, content={"error": "PDF not available"})
        
        pdf_data = base64.b64decode(snapshot['schema_pdf'])
        
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=schema_v{version}.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    print("🚀 Starting APISec Full Service")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /infer - Run parameter inference")
    print("  POST /spec  - Generate OpenAPI spec")
    print("  GET  /apis  - List registered APIs")
    print("  POST /apis  - Register new API")
    print("\nStarting server on http://127.0.0.1:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
