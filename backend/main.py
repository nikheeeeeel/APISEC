from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import tempfile
import os
import json
import logging
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from models import CanonicalParameter
from spec_utils import load_spec, diff_spec, merge_spec
from arjun_wrapper import run_arjun, parse_arjun_output

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscoverRequest(BaseModel):
    url: str

app = FastAPI(title="APISec Backend")

# CORS settings to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/test-diff")
async def test_diff(file: UploadFile = File(...)):
    """
    Test endpoint for spec diff functionality.
    Accepts OpenAPI spec file upload and returns missing parameters.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Load spec
            spec_dict = load_spec(temp_file_path)
            
            # Example discovered parameters for testing
            example_params = [
                CanonicalParameter(
                    name="foo",
                    in_="query",
                    type_="string",
                    required=True,
                    description="Test parameter foo"
                ),
                CanonicalParameter(
                    name="bar", 
                    in_="header",
                    type_="integer",
                    required=False,
                    description="Test parameter bar"
                ),
                CanonicalParameter(
                    name="param1",
                    in_="query", 
                    type_="string",
                    required=True,
                    description="Discovered parameter from Arjun"
                )
            ]
            
            # Find missing parameters
            missing_params = diff_spec(spec_dict, example_params)
            
            # Convert to dict for JSON response
            missing_params_dict = [
                {
                    "name": param.name,
                    "in": param.in_,
                    "type": param.type_,
                    "required": param.required,
                    "description": param.description,
                    "example": param.example
                }
                for param in missing_params
            ]
            
            return {"to_add": missing_params_dict}
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


@app.post("/discover")
async def discover(
    url: Optional[str] = Form(""),
    file: Optional[UploadFile] = File(None)
):
    """
    Main discovery endpoint that integrates Arjun, spec diff, and merge.
    
    Args:
        url: API endpoint to scan with Arjun
        file: Optional OpenAPI spec file (JSON/YAML)
        
    Returns:
        JSON with path to updated spec file
    """
    temp_spec_path = None
    arjun_output_path = None
    
    try:
        logger.info(f"Starting discovery for URL: {url}")
        
        # Basic URL validation
        if not url or not url.strip():
            logger.error("Empty URL provided")
            return JSONResponse(
                status_code=400,
                content={"error": "URL is required"}
            )
        
        # Basic URL format validation
        if not (url.startswith('http://') or url.startswith('https://')):
            logger.error(f"Invalid URL format: {url}")
            return JSONResponse(
                status_code=400,
                content={"error": "URL must start with http:// or https://"}
            )
        
        # Step 1: Load or create spec
        if file:
            logger.info(f"Loading uploaded spec file: {file.filename}")
            # Save uploaded spec temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_spec_path = temp_file.name
            
            spec_dict = load_spec(temp_spec_path)
        else:
            logger.info("No spec file provided, creating empty template")
            spec_dict = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Generated API Spec",
                    "version": "1.0.0",
                    "description": f"API spec generated from scanning {url}"
                },
                "paths": {},
                "components": {
                    "parameters": {}
                }
            }
        
        # Step 2: Run Arjun on URL
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arjun_output_path = f"arjun_output_{timestamp}.json"
        
        logger.info(f"Running Arjun on URL: {url}")
        arjun_result = run_arjun(url, arjun_output_path)
        
        if not arjun_result["success"]:
            logger.error(f"Arjun execution failed: {arjun_result['stderr']}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Arjun execution failed: {arjun_result['stderr']}"}
            )
        
        # Check if file was created
        if not os.path.exists(arjun_output_path):
            logger.info(f"Arjun output file not found (no parameters discovered): {arjun_output_path}")
            # This is normal when Arjun finds no parameters
            discovered_params = []
        else:
            logger.info(f"Arjun completed successfully")
            
            # Step 3: Parse Arjun output into canonical parameters
            discovered_params = parse_arjun_output(arjun_output_path)
            logger.info(f"Parsed {len(discovered_params)} discovered parameters")
        
        # Step 4: Diff canonical params with loaded spec
        missing_params = diff_spec(spec_dict, discovered_params)
        logger.info(f"Found {len(missing_params)} missing parameters")
        
        # Step 5: Merge missing parameters into spec
        updated_spec = merge_spec(spec_dict, missing_params)
        
        # Step 6: Export updated spec with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_format = "json"  # Default to JSON
        output_filename = f"outputs/updated_spec_{timestamp}.{output_format}"
        
        # Ensure outputs directory exists
        os.makedirs("outputs", exist_ok=True)
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(updated_spec, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Updated spec saved to: {output_filename}")
        
        return {
            "filename": output_filename,
            "discovered_params": len(discovered_params),
            "missing_params": len(missing_params),
            "message": f"Successfully updated spec with {len(missing_params)} new parameters"
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )
        
    finally:
        # Clean up temporary files
        if temp_spec_path and os.path.exists(temp_spec_path):
            os.unlink(temp_spec_path)
            logger.info(f"Cleaned up temporary spec file: {temp_spec_path}")
            
        if arjun_output_path and os.path.exists(arjun_output_path):
            os.unlink(arjun_output_path)
            logger.info(f"Cleaned up Arjun output file: {arjun_output_path}")

# Serve output files for download
@app.get("/outputs/{filename}")
async def download_output(filename: str):
    from fastapi.responses import FileResponse
    file_path = f"outputs/{filename}"
    
    if not os.path.exists(file_path):
        logger.warning(f"Download request for non-existent file: {file_path}")
        return JSONResponse(
            status_code=404,
            content={"error": "File not found"}
        )
    
    # Determine MIME type
    if filename.endswith('.json'):
        media_type = 'application/json'
    elif filename.endswith('.yaml') or filename.endswith('.yml'):
        media_type = 'application/x-yaml'
    else:
        media_type = 'application/octet-stream'
    
    logger.info(f"Serving file for download: {file_path}")
    return FileResponse(
        file_path, 
        filename=filename,
        media_type=media_type
    )

# Mount static files to serve frontend (but exclude API routes)
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
