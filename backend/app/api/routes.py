"""API routes."""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.api.schemas import (
    GenerateDocsRequest,
    GenerateDocsResponse,
    ReportInfo,
    ReportsListResponse
)
from app.core.config import settings
from app.core.security import AuthCredentials
from app.services.openapi_fetcher import OpenAPIFetcher
from app.services.crawler import SafeAPICrawler
from app.services.inferencer import OpenAPIInferencer
from app.services.report import PDFReportGenerator

router = APIRouter()


def _save_spec(spec: dict, api_uri: str) -> str:
    """
    Save OpenAPI specification to disk.
    
    Args:
        spec: OpenAPI specification dictionary
        api_uri: API URI for naming
        
    Returns:
        Spec ID (filename)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_uri = api_uri.replace("://", "_").replace("/", "_").replace(":", "_")[:50]
    spec_id = f"spec_{safe_uri}_{timestamp}.json"
    spec_path = settings.SPECS_DIR / spec_id
    
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)
    
    return spec_id


@router.post("/generate", response_model=GenerateDocsResponse)
async def generate_documentation(
    request: GenerateDocsRequest
):
    """
    Generate API documentation.
    
    First attempts to discover existing OpenAPI spec.
    If not found, performs safe crawling to infer specification.
    """
    api_uri = str(request.api_uri)
    
    # Prepare credentials if provided
    credentials = None
    if request.api_key or request.bearer_token:
        credentials = AuthCredentials(
            api_key=request.api_key,
            bearer_token=request.bearer_token
        )
    
    # Step 1: Try to discover existing OpenAPI spec
    fetcher = OpenAPIFetcher(api_uri, credentials)
    spec, discovery_path = await fetcher.discover()
    
    discovery_method = "existing"
    
    # Step 2: If not found, crawl and infer
    if spec is None:
        discovery_method = "inferred"
        
        crawler = SafeAPICrawler(api_uri, credentials)
        endpoints = await crawler.crawl()
        
        if not endpoints:
            raise HTTPException(
                status_code=404,
                detail="Could not discover any endpoints. The API may require authentication or may not be accessible."
            )
        
        inferencer = OpenAPIInferencer(api_uri, endpoints)
        spec = inferencer.infer()
    
    # Step 3: Save spec
    spec_id = _save_spec(spec, api_uri)
    
    # Step 4: Generate PDF report
    report_id = None
    try:
        # Determine discovery method
        discovery_method_for_report = "existing" if spec.get("x-generated") != "inferred" else "inferred"
        
        # Generate PDF report
        report_generator = PDFReportGenerator()
        report_path = report_generator.generate(
            api_uri=api_uri,
            openapi_spec=spec,
            discovery_method=discovery_method_for_report
        )
        report_id = report_path.name
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error generating PDF report: {e}")
    
    return GenerateDocsResponse(
        success=True,
        message=f"Documentation generated successfully via {discovery_method} method",
        discovery_method=discovery_method,
        spec_id=spec_id,
        report_id=report_id
    )


@router.get("/reports", response_model=ReportsListResponse)
async def list_reports():
    """List all generated PDF reports."""
    reports = []
    
    for report_file in sorted(settings.REPORTS_DIR.glob("*.pdf"), reverse=True):
        # Extract metadata from filename
        # Format: apisec_report_{uri}_{timestamp}.pdf
        filename = report_file.name
        stat = report_file.stat()
        generated_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        # Try to extract API URI from filename
        parts = filename.replace("apisec_report_", "").replace(".pdf", "").split("_")
        api_uri = "Unknown"
        if len(parts) > 1:
            # Reconstruct URI (simplified)
            api_uri = parts[0].replace("_", "://", 1) if "://" not in parts[0] else parts[0]
        
        # Determine discovery method from spec if available
        discovery_method = "unknown"
        spec_files = list(settings.SPECS_DIR.glob("*.json"))
        for spec_file in spec_files:
            if spec_file.stat().st_mtime <= stat.st_mtime:
                try:
                    with open(spec_file, "r") as f:
                        spec = json.load(f)
                        if spec.get("x-generated") == "inferred":
                            discovery_method = "inferred"
                        else:
                            discovery_method = "existing"
                        break
                except:
                    pass
        
        reports.append(ReportInfo(
            id=filename,
            filename=filename,
            api_uri=api_uri,
            generated_at=generated_at,
            discovery_method=discovery_method
        ))
    
    return ReportsListResponse(reports=reports)


@router.get("/reports/{report_id}")
async def download_report(report_id: str):
    """Download a specific PDF report."""
    report_path = settings.REPORTS_DIR / report_id
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=report_id
    )


@router.get("/specs/{spec_id}")
async def get_spec(spec_id: str):
    """Get OpenAPI specification JSON."""
    spec_path = settings.SPECS_DIR / spec_id
    
    if not spec_path.exists():
        raise HTTPException(status_code=404, detail="Specification not found")
    
    with open(spec_path, "r") as f:
        spec = json.load(f)
    
    return JSONResponse(content=spec)
