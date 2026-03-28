from fastapi import FastAPI, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
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
from auth import auth_service
from oauth import oauth_service
from user_models import UserCreate, UserLogin, UserLoginResponse, UserResponse, OAuthUserInfo
from user_db import user_db
from config import config
import sys
import os
import datetime
import json
import uuid

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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

# Security
security = HTTPBearer()

# Dependency to get current user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token."""
    try:
        payload = auth_service.verify_token(credentials.credentials)
        user_id = payload.get('sub')
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_db.get_user_by_id(int(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Authentication endpoints
@app.post("/auth/register", response_model=UserLoginResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = user_db.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        existing_username = user_db.get_user_by_username(user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create user
        user = user_db.create_user(user_data)
        
        # Create access token
        access_token = auth_service.create_access_token(data={"sub": str(user['id'])})
        
        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/auth/login", response_model=UserLoginResponse)
async def login(user_credentials: UserLogin):
    """Login user with username and password."""
    try:
        # Get user by username
        user = user_db.get_user_by_username(user_credentials.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if user has password (OAuth users may not have passwords)
        if not user.get('password_hash'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please login using OAuth provider"
            )
        
        # Verify password
        if not auth_service.verify_password(user_credentials.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create access token
        access_token = auth_service.create_access_token(data={"sub": str(user['id'])})
        
        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(**current_user)

@app.get("/auth/oauth/google")
async def google_oauth_login():
    """Initiate Google OAuth login."""
    if not config.is_oauth_configured('google'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth not configured"
        )
    
    state = auth_service.generate_oauth_state()
    auth_url = auth_service.create_oauth_auth_url('google', state)
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/oauth/github")
async def github_oauth_login():
    """Initiate GitHub OAuth login."""
    if not config.is_oauth_configured('github'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth not configured"
        )
    
    state = auth_service.generate_oauth_state()
    auth_url = auth_service.create_oauth_auth_url('github', state)
    
    return RedirectResponse(url=auth_url)

@app.get("/auth/oauth/callback/google")
async def google_oauth_callback(code: str):
    """Handle Google OAuth callback."""
    try:
        # Get user info from Google
        user_info = await oauth_service.get_google_user_info(code)
        
        # Create or update user
        user = user_db.create_or_update_oauth_user(user_info.dict())
        
        # Create access token
        access_token = auth_service.create_access_token(data={"sub": str(user['id'])})
        
        # Redirect to frontend with token
        redirect_url = f"{config.FRONTEND_URL}/auth/callback?token={access_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"Google OAuth callback failed: {str(e)}")
        redirect_url = f"{config.FRONTEND_URL}/login?error=oauth_failed"
        return RedirectResponse(url=redirect_url)

@app.get("/auth/oauth/callback/github")
async def github_oauth_callback(code: str):
    """Handle GitHub OAuth callback."""
    try:
        # Get user info from GitHub
        user_info = await oauth_service.get_github_user_info(code)
        
        # Create or update user
        user = user_db.create_or_update_oauth_user(user_info.dict())
        
        # Create access token
        access_token = auth_service.create_access_token(data={"sub": str(user['id'])})
        
        # Redirect to frontend with token
        redirect_url = f"{config.FRONTEND_URL}/auth/callback?token={access_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"GitHub OAuth callback failed: {str(e)}")
        redirect_url = f"{config.FRONTEND_URL}/login?error=oauth_failed"
        return RedirectResponse(url=redirect_url)

@app.post("/discover-schema")
async def discover_schema_endpoint(request: DiscoveryRequest, current_user: dict = Depends(get_current_user)):
    """
    Discover API schema from given URL.
    
    Args:
        request: DiscoverRequest containing the target URL
        
    Returns:
        JSON with discovered schema information
    """
    try:
        logger.info(f"User {current_user['username']} starting schema discovery for URL: {request.url}")
        
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
    base_url: str = Form(...),
    new_url: str = Form(...),
    current_user: dict = Depends(get_current_user)
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
        logger.info(f"User {current_user['username']} starting differential analysis between {base_url} and {new_url}")
        
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

@app.post("/validate-runtime")
async def validate_runtime_endpoint(request: RuntimeValidationRequest, current_user: dict = Depends(get_current_user)):
    """
    Validate API schema against runtime behavior.
    
    Args:
        request: RuntimeValidationRequest containing base URL and schema info
        
    Returns:
        JSON with runtime validation results
    """
    try:
        logger.info(f"User {current_user['username']} starting runtime validation for URL: {request.base_url}")
        
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

# Schema Monitor Endpoints
@app.get("/api/apis")
async def get_apis(current_user: dict = Depends(get_current_user)):
    """Get all registered APIs for current user"""
    try:
        apis = ApiRegistry.get_all(user_id=current_user['id'])
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
async def get_api_schemas(api_id: int, current_user: dict = Depends(get_current_user)):
    """Get all schema versions for a specific API"""
    try:
        # First check if API belongs to current user
        api = ApiRegistry.get_by_id(api_id, user_id=current_user['id'])
        if not api:
            return JSONResponse(
                status_code=404,
                content={"error": "API not found"}
            )
        
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
async def get_latest_schema(api_id: int, current_user: dict = Depends(get_current_user)):
    """Get the latest schema version for a specific API"""
    try:
        # First check if API belongs to current user
        api = ApiRegistry.get_by_id(api_id, user_id=current_user['id'])
        if not api:
            return JSONResponse(
                status_code=404,
                content={"error": "API not found"}
            )
        
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
async def scan_api_schema(api_id: int, current_user: dict = Depends(get_current_user)):
    """Scan an API for schema changes and store new version if different"""
    try:
        # Get API details (check ownership)
        api = ApiRegistry.get_by_id(api_id, user_id=current_user['id'])
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
    description: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Create a new API entry for monitoring"""
    try:
        # Check if API with this URL already exists for this user
        existing_api = ApiRegistry.get_by_url(base_url, user_id=current_user['id'])
        if existing_api:
            return {
                "status": "exists",
                "message": "API with this URL already exists",
                "api": existing_api
            }
        
        api = ApiRegistry.create(name=name, base_url=base_url, description=description, user_id=current_user['id'])
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
async def compare_schema_versions(api_id: int, version1: int, version2: int, structured: bool = False, current_user: dict = Depends(get_current_user)):
    """Compare two schema versions"""
    try:
        # Check if API belongs to current user
        api = ApiRegistry.get_by_id(api_id, user_id=current_user['id'])
        if not api:
            return JSONResponse(
                status_code=404,
                content={"error": "API not found"}
            )
        
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
async def get_schema_version(api_id: int, version: int, current_user: dict = Depends(get_current_user)):
    """Get a specific schema version for detailed comparison"""
    try:
        # Check if API belongs to current user
        api = ApiRegistry.get_by_id(api_id, user_id=current_user['id'])
        if not api:
            return JSONResponse(
                status_code=404,
                content={"error": "API not found"}
            )
        
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
async def delete_api(api_id: int, current_user: dict = Depends(get_current_user)):
    """Delete an API and all its schema versions"""
    try:
        # Check if API exists and belongs to current user
        api = ApiRegistry.get_by_id(api_id, user_id=current_user['id'])
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
