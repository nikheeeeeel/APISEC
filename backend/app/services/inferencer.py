"""Service for inferring OpenAPI 3.x specifications from discovered endpoints."""
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse

from app.services.crawler import EndpointInfo


class OpenAPIInferencer:
    """Service to infer OpenAPI 3.x specifications from discovered endpoints."""
    
    def __init__(self, base_uri: str, endpoints: List[EndpointInfo]):
        """
        Initialize OpenAPI inferencer.
        
        Args:
            base_uri: Base URI of the API
            endpoints: List of discovered endpoints
        """
        self.base_uri = base_uri.rstrip("/")
        self.endpoints = endpoints
        parsed = urlparse(base_uri)
        self.server_url = f"{parsed.scheme}://{parsed.netloc}"
    
    def infer(self) -> Dict[str, Any]:
        """
        Infer OpenAPI 3.x specification from discovered endpoints.
        
        Returns:
            OpenAPI 3.x specification dictionary
        """
        paths = {}
        
        # Group endpoints by path
        for endpoint in self.endpoints:
            if endpoint.status_code == 0:  # Skip failed endpoints
                continue
            
            if endpoint.path not in paths:
                paths[endpoint.path] = {}
            
            # Only GET method is supported (safety constraint)
            paths[endpoint.path]["get"] = {
                "summary": f"GET {endpoint.path}",
                "description": f"Inferred endpoint discovered during API crawling",
                "operationId": f"get_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}",
                "responses": {
                    str(endpoint.status_code): {
                        "description": f"Response with status {endpoint.status_code}",
                        "content": {}
                    }
                },
                "x-generated": "inferred"
            }
            
            # Add response schema if available
            if endpoint.response_schema:
                paths[endpoint.path]["get"]["responses"][str(endpoint.status_code)]["content"] = {
                    "application/json": {
                        "schema": endpoint.response_schema
                    }
                }
        
        # Build OpenAPI spec
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": f"Inferred API Documentation - {self.server_url}",
                "description": (
                    "This OpenAPI specification was automatically inferred from API crawling. "
                    "It may be incomplete or inaccurate. Auth-protected and dynamic endpoints "
                    "may not be detected."
                ),
                "version": "1.0.0-inferred",
                "x-generated": "inferred",
                "x-generation-date": datetime.utcnow().isoformat() + "Z"
            },
            "servers": [
                {
                    "url": self.server_url,
                    "description": "API Server"
                }
            ],
            "paths": paths,
            "x-generated": "inferred",
            "x-limitations": [
                "Only GET endpoints were discovered (safety constraint)",
                "Auth-protected endpoints may not be accessible",
                "Dynamic endpoints may not be detected",
                "Response schemas are inferred from samples and may be incomplete"
            ]
        }
        
        return spec
