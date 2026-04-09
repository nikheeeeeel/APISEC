from fastapi import FastAPI, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import logging
import sys
import os

from schema_monitor import crawl_for_schema, crawl_all_schemas, generate_pdf_from_json, compare_schemas, compare_schemas_structured
from ai_analyzer import analyze_single_change, analyze_runtime_endpoint_failure
from runtime_validator import create_runtime_validator
from models import DiscoveryRequest
from models_runtime import (
    RuntimeValidationRequest,
    RuntimeValidationResponse,
    RuntimeFailureAnalysisRequest,
    EndpointTestResult,
)
from registry_db import init_db, ApiRegistry, SchemaSnapshot, UserRegistry
from runtime_validator_demo_routes import router as rtv_demo_router

# Authentication dependencies
from passlib.context import CryptContext
from jose import JWTError, jwt

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Wait for DB to be initialized by docker-compose, or initialize here
try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize DB: {e}")

app = FastAPI(title="API Schema Discovery & Diffing")
app.include_router(rtv_demo_router)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Authentication setup ===
SECRET_KEY = os.environ.get("JWT_SECRET", "super-secret-default-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = UserRegistry.get_by_username(username=username)
    if user is None:
        raise credentials_exception
    return user

class UserCreate(BaseModel):
    username: str
    password: str

@app.post("/auth/register")
async def register(user: UserCreate):
    existing_user = UserRegistry.get_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed_password = get_password_hash(user.password)
    new_user = UserRegistry.create(user.username, hashed_password)
    if not new_user:
        raise HTTPException(status_code=500, detail="Failed to create user")
        
    return {"message": "User created successfully"}

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = UserRegistry.get_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# === Endpoints ===

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/validate-runtime")
async def validate_runtime_endpoint(request: RuntimeValidationRequest, current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Starting runtime validation for URL: {request.base_url}")
        validator = create_runtime_validator()
        result = await validator.validate_schema(request.base_url, request.schema_info)
        
        endpoint_tests = []
        for test in result.endpoint_tests:
            endpoint_test = EndpointTestResult(
                method=test.method, path=test.path, url=test.url,
                expected_status=test.expected_status, actual_status=test.actual_status,
                expected_response_schema=test.expected_response_schema,
                actual_response=test.actual_response, response_time_ms=test.response_time_ms,
                error=test.error, status_mismatch=test.status_mismatch,
                schema_mismatch=test.schema_mismatch, validation_passed=test.validation_passed
            )
            endpoint_tests.append(endpoint_test)
        
        summary = f"Runtime validation completed: {result.passed_endpoints}/{result.tested_endpoints} endpoints passed"
        if result.failed_endpoints > 0:
            summary += f", {result.failed_endpoints} endpoints failed"
        
        response = RuntimeValidationResponse(
            base_url=result.base_url, total_endpoints=result.total_endpoints,
            tested_endpoints=result.tested_endpoints, passed_endpoints=result.passed_endpoints,
            failed_endpoints=result.failed_endpoints, endpoint_tests=endpoint_tests,
            validation_timestamp=result.validation_timestamp, overall_status=result.overall_status,
            summary=summary
        )
        return {"status": "success", "validation_result": response.dict()}
        
    except Exception as e:
        logger.error(f"Runtime validation failed: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"Runtime validation failed: {str(e)}"})


@app.post("/validate-runtime/analyze-failure")
async def validate_runtime_analyze_failure(
    request: RuntimeFailureAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """AI explanation for a single failed runtime endpoint test (same stack as version-monitor Analyze)."""
    try:
        payload = request.endpoint_test.model_dump(mode="json")
        analysis = await analyze_runtime_endpoint_failure(request.base_url, payload)
        return {"status": "success", "analysis": analysis}
    except Exception as e:
        logger.error(f"Runtime failure analysis failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/discover-schema")
async def discover_schema_endpoint(request: DiscoveryRequest, current_user: dict = Depends(get_current_user)):
    try:
        logger.info(f"Starting schema discovery for URL: {request.url}")
        schema_info, schema_url = crawl_for_schema(request.url)
        if schema_info:
            return {"status": "success", "schema": schema_info, "schema_url": schema_url, "url": request.url}
        else:
            return {"status": "not_found", "message": "No schema found", "url": request.url}
    except Exception as e:
        logger.error(f"Schema discovery failed: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# === Schema Monitor API Endpoints ===

@app.get("/api/apis")
async def get_apis(current_user: dict = Depends(get_current_user)):
    try:
        apis = ApiRegistry.get_all(user_id=current_user['id'])
        return {"status": "success", "apis": apis}
    except Exception as e:
        logger.error(f"Failed to get APIs: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/apis/{api_id}/schemas")
async def get_api_schemas(api_id: int, current_user: dict = Depends(get_current_user)):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        schemas = SchemaSnapshot.get_by_api(api_id)
        return {"status": "success", "schemas": schemas}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/apis/{api_id}/schemas/latest")
async def get_latest_schema(api_id: int, current_user: dict = Depends(get_current_user)):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        schema = SchemaSnapshot.get_latest(api_id)
        if not schema: return JSONResponse(status_code=404, content={"error": "No schemas found"})
        return {"status": "success", "schema": schema}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/apis/{api_id}/scan")
async def scan_api_schema(api_id: int, current_user: dict = Depends(get_current_user)):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        # Discover ALL versioned schemas at once (e.g., /v1/openapi.json + /v2/openapi.json)
        all_schemas = crawl_all_schemas(api['base_url'])
        if not all_schemas:
            return {"status": "no_schema", "message": "No schema found"}
        
        new_snapshots = []
        unchanged_count = 0
        
        for schema_info, schema_url in all_schemas:
            result = SchemaSnapshot.create_if_different(api_id, schema_info, schema_url=schema_url)
            if result.get('status') == 'unchanged':
                unchanged_count += 1
                continue
            
            # Generate PDF and attach to snapshot
            schema_pdf = generate_pdf_from_json(schema_info)
            SchemaSnapshot.update_pdf(result['id'], schema_pdf)
            new_snapshots.append(result)
        
        if new_snapshots:
            return {
                "status": "success",
                "message": f"{len(new_snapshots)} new schema(s) stored, {unchanged_count} unchanged",
                "schemas_found": len(all_schemas),
                "snapshots": new_snapshots
            }
        else:
            return {
                "status": "unchanged",
                "message": f"All {unchanged_count} schema(s) unchanged"
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/apis")
async def create_api(
    name: str = Form(...),
    base_url: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        existing_api = ApiRegistry.get_by_url(current_user['id'], base_url)
        if existing_api:
            return {"status": "exists", "message": "API with this URL already exists", "api": existing_api}
        
        api = ApiRegistry.create(user_id=current_user['id'], name=name, base_url=base_url, description=description)
        return {"status": "success", "api": api}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.put("/api/apis/{api_id}")
async def update_api(
    api_id: int,
    name: str = Form(...),
    base_url: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api:
            return JSONResponse(status_code=404, content={"error": "API not found"})
        
        success = ApiRegistry.update(current_user['id'], api_id, name, base_url, description)
        if success:
            updated_api = ApiRegistry.get_by_id(current_user['id'], api_id)
            return {"status": "success", "api": updated_api}
        else:
            return JSONResponse(status_code=500, content={"error": "Failed to update API"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/schemas/{api_id}/compare/{version1}/{version2}")
async def compare_schema_versions(api_id: int, version1: int, version2: int, structured: bool = False, current_user: dict = Depends(get_current_user)):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        schema1 = SchemaSnapshot.get_by_version(api_id, version1)
        schema2 = SchemaSnapshot.get_by_version(api_id, version2)
        if not schema1 or not schema2: return JSONResponse(status_code=404, content={"error": "Versions not found"})
        
        if structured:
            result = compare_schemas_structured(schema1['schema_json'], schema2['schema_json'])
            return {
                "status": "success", "summary": result["summary"], "changes": result["changes"], "ai_enabled": False,
                "schema1": {"version": version1, "timestamp": schema1['timestamp']},
                "schema2": {"version": version2, "timestamp": schema2['timestamp']}
            }
        else:
            changes = compare_schemas(schema1['schema_json'], schema2['schema_json'])
            return {
                "status": "success", "changes": changes,
                "schema1": {"version": version1, "timestamp": schema1['timestamp']},
                "schema2": {"version": version2, "timestamp": schema2['timestamp']}
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/schemas/{api_id}/analyze-change")
async def analyze_specific_change(api_id: int, request: dict, current_user: dict = Depends(get_current_user)):
    version1 = request.get("version1")
    version2 = request.get("version2")
    change = request.get("change")

    if not all([version1, version2, change]):
        return JSONResponse(status_code=400, content={"error": "Missing required fields"})

    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        schema1 = SchemaSnapshot.get_by_version(api_id, version1)
        schema2 = SchemaSnapshot.get_by_version(api_id, version2)
        if not schema1 or not schema2: return JSONResponse(status_code=404, content={"error": "Versions not found"})
            
        enriched_change = await analyze_single_change(change, schema1['schema_json'], schema2['schema_json'])
        return {"status": "success", "analysis": enriched_change.get("detailed_analysis", "No analysis returned")}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/schemas/{api_id}/version/{version}")
async def get_schema_version(api_id: int, version: int, current_user: dict = Depends(get_current_user)):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        schema = SchemaSnapshot.get_by_version(api_id, version)
        if not schema: return JSONResponse(status_code=404, content={"error": "Schema not found"})
        return {"status": "success", "schema": schema}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/apis/{api_id}")
async def delete_api(api_id: int, current_user: dict = Depends(get_current_user)):
    try:
        api = ApiRegistry.get_by_id(current_user['id'], api_id)
        if not api: return JSONResponse(status_code=404, content={"error": "API not found"})
        
        success = ApiRegistry.delete(current_user['id'], api_id)
        if success: return {"status": "success", "message": "Deleted"}
        else: return JSONResponse(status_code=500, content={"error": "Failed to delete"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
