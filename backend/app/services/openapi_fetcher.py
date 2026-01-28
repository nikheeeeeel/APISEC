"""Service for fetching existing OpenAPI specifications."""
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import httpx

from app.core.config import settings
from app.core.security import AuthCredentials
from app.utils.http import SafeHTTPClient
from app.utils.validators import validate_openapi_spec, parse_json_safe


class OpenAPIFetcher:
    """Service to discover and fetch existing OpenAPI specifications."""
    
    def __init__(self, base_uri: str, credentials: Optional[AuthCredentials] = None):
        """
        Initialize OpenAPI fetcher.
        
        Args:
            base_uri: Base URI of the target API
            credentials: Optional authentication credentials
        """
        self.base_uri = base_uri.rstrip("/")
        self.client = SafeHTTPClient(credentials)
    
    async def discover(self) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Attempt to discover OpenAPI specification from common paths.
        
        Returns:
            Tuple of (spec_dict, discovery_path) or (None, None) if not found
        """
        for path in settings.OPENAPI_PATHS:
            url = urljoin(self.base_uri, path)
            
            try:
                response = await self.client.get(url)
                
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "").lower()
                    
                    # Check if it's JSON
                    if "json" in content_type or path.endswith(".json"):
                        spec = parse_json_safe(response.content)
                        
                        if spec:
                            is_valid, error = validate_openapi_spec(spec)
                            if is_valid:
                                return spec, path
                            # Continue searching if invalid
                    
            except (httpx.HTTPError, httpx.TimeoutException):
                # Continue to next path on error
                continue
        
        return None, None
