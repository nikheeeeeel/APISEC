"""Safe API crawler for endpoint discovery."""
from typing import List, Dict, Any, Set, Optional
from urllib.parse import urljoin, urlparse
import asyncio

from app.core.config import settings
from app.core.security import AuthCredentials
from app.utils.http import SafeHTTPClient


class EndpointInfo:
    """Information about a discovered endpoint."""
    
    def __init__(
        self,
        path: str,
        method: str = "GET",
        status_code: int = 200,
        response_schema: Optional[Dict[str, Any]] = None,
        error_count: int = 0
    ):
        self.path = path
        self.method = method
        self.status_code = status_code
        self.response_schema = response_schema or {}
        self.error_count = error_count


class SafeAPICrawler:
    """Safe, GET-only API crawler with depth and rate limiting."""
    
    def __init__(
        self,
        base_uri: str,
        credentials: Optional[AuthCredentials] = None
    ):
        """
        Initialize API crawler.
        
        Args:
            base_uri: Base URI of the target API
            credentials: Optional authentication credentials
        """
        self.base_uri = base_uri.rstrip("/")
        self.client = SafeHTTPClient(credentials)
        self.visited: Set[str] = set()
        self.endpoints: List[EndpointInfo] = []
        self.base_domain = urlparse(base_uri).netloc
    
    def _is_same_origin(self, url: str) -> bool:
        """Check if URL is same-origin as base URI."""
        parsed = urlparse(url)
        return parsed.netloc == self.base_domain
    
    def _normalize_path(self, path: str) -> str:
        """Normalize API path."""
        # Remove query params and fragments for path normalization
        parsed = urlparse(path)
        return parsed.path
    
    def _extract_paths_from_response(
        self,
        response_data: Dict[str, Any],
        current_path: str
    ) -> List[str]:
        """
        Heuristically extract potential API paths from response data.
        
        This is a simple heuristic - looks for common patterns like:
        - Links in JSON responses
        - Arrays of objects with 'url' or 'path' fields
        """
        paths = []
        
        if isinstance(response_data, dict):
            # Look for common link fields
            for key in ["url", "href", "link", "path", "endpoint"]:
                if key in response_data:
                    value = response_data[key]
                    if isinstance(value, str) and value.startswith("/"):
                        paths.append(value)
            
            # Recursively search nested structures
            for value in response_data.values():
                if isinstance(value, (dict, list)):
                    paths.extend(self._extract_paths_from_response(value, current_path))
        
        elif isinstance(response_data, list):
            for item in response_data[:10]:  # Limit recursion depth
                if isinstance(item, (dict, list)):
                    paths.extend(self._extract_paths_from_response(item, current_path))
        
        return paths
    
    async def _crawl_path(self, path: str, depth: int) -> Optional[EndpointInfo]:
        """
        Crawl a single API path.
        
        Args:
            path: API path to crawl
            depth: Current crawl depth
            
        Returns:
            EndpointInfo if successful, None otherwise
        """
        if depth > settings.MAX_CRAWL_DEPTH:
            return None
        
        normalized = self._normalize_path(path)
        if normalized in self.visited:
            return None
        
        if len(self.endpoints) >= settings.MAX_ENDPOINTS:
            return None
        
        url = urljoin(self.base_uri, normalized)
        
        if not self._is_same_origin(url):
            return None
        
        self.visited.add(normalized)
        
        try:
            response = await self.client.get(url)
            
            # Parse response schema
            response_schema = {}
            if response.headers.get("content-type", "").startswith("application/json"):
                import json
                try:
                    data = json.loads(response.content)
                    response_schema = self._infer_schema(data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            
            endpoint = EndpointInfo(
                path=normalized,
                method="GET",
                status_code=response.status_code,
                response_schema=response_schema
            )
            
            self.endpoints.append(endpoint)
            
            # If successful response, try to discover more paths
            if response.status_code == 200 and depth < settings.MAX_CRAWL_DEPTH:
                if response.headers.get("content-type", "").startswith("application/json"):
                    import json
                    try:
                        data = json.loads(response.content)
                        discovered_paths = self._extract_paths_from_response(data, normalized)
                        
                        # Queue discovered paths for crawling
                        for discovered_path in discovered_paths[:5]:  # Limit branching
                            if discovered_path not in self.visited:
                                await self._crawl_path(discovered_path, depth + 1)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            
            return endpoint
            
        except Exception:
            # On error, still record the endpoint but mark it
            endpoint = EndpointInfo(
                path=normalized,
                method="GET",
                status_code=0,
                error_count=1
            )
            self.endpoints.append(endpoint)
            return None
    
    def _infer_schema(self, data: Any) -> Dict[str, Any]:
        """
        Infer JSON schema from data sample.
        
        Args:
            data: Sample data
            
        Returns:
            Simplified schema dictionary
        """
        if isinstance(data, dict):
            properties = {}
            for key, value in data.items():
                properties[key] = self._infer_type(value)
            return {
                "type": "object",
                "properties": properties
            }
        elif isinstance(data, list):
            if data:
                return {
                    "type": "array",
                    "items": self._infer_schema(data[0])
                }
            return {"type": "array"}
        else:
            return {"type": self._infer_type(data)}
    
    def _infer_type(self, value: Any) -> Dict[str, Any]:
        """Infer JSON schema type from Python value."""
        if isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        elif isinstance(value, str):
            return {"type": "string"}
        elif isinstance(value, dict):
            return self._infer_schema(value)
        elif isinstance(value, list):
            return {"type": "array", "items": {}}
        else:
            return {"type": "string"}  # Default fallback
    
    async def crawl(self, seed_paths: Optional[List[str]] = None) -> List[EndpointInfo]:
        """
        Start crawling the API.
        
        Args:
            seed_paths: Optional list of seed paths to start crawling from.
                       If None, starts from root "/"
        
        Returns:
            List of discovered endpoints
        """
        if seed_paths is None:
            seed_paths = ["/"]
        
        # Crawl seed paths
        for path in seed_paths:
            if len(self.endpoints) >= settings.MAX_ENDPOINTS:
                break
            await self._crawl_path(path, depth=0)
        
        return self.endpoints
