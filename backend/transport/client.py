"""
Enhanced transport client for REST Parameter Discovery v2.

Provides stateless HTTP client with automatic authentication,
header injection, and support for multiple payload locations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, Tuple
import requests
from requests import Response
from urllib.parse import urlencode, urlparse
from ..models import DiscoveryRequest, AuthConfig


class TransportClientInterface(ABC):
    """
    Enhanced transport client interface with DiscoveryRequest support.
    
    Supports automatic authentication, header injection, and multiple payload locations.
    """
    
    @abstractmethod
    async def send(
        self, 
        request: DiscoveryRequest,
        payload: Optional[Union[Dict[str, Any], str, bytes]] = None,
        location: str = "body"
    ) -> Response:
        """
        Send HTTP request with automatic auth and headers.
        
        Args:
            request: Discovery request with auth and headers
            payload: Request payload data
            location: Payload location ('body', 'query', 'form', 'header')
            
        Returns:
            HTTP response object
        """
        pass


class RequestsTransportClient(TransportClientInterface):
    """
    Production transport client using requests library.
    
    Provides automatic authentication, header injection, and
support for JSON, form, query, and header payloads.
    """
    
    def __init__(self, default_timeout: int = 30):
        """
        Initialize transport client.
        
        Args:
            default_timeout: Default timeout for requests
        """
        self.default_timeout = default_timeout
        self.session = requests.Session()
        
        # Configure session defaults
        self.session.headers.update({
            'User-Agent': 'APISec-Discovery/v2.0',
            'Accept': 'application/json, text/plain, */*',
            'Connection': 'keep-alive'
        })
    
    def _apply_auth(self, request: DiscoveryRequest) -> Dict[str, str]:
        """Apply authentication configuration to headers."""
        headers = {}
        
        if request.auth and request.auth.type != "none":
            if request.auth.type == "bearer":
                headers['Authorization'] = f"Bearer {request.auth.value}"
            elif request.auth.type == "apikey":
                header_name = request.auth.header_name or "X-API-Key"
                headers[header_name] = request.auth.value
        
        return headers
    
    def _prepare_headers(self, request: DiscoveryRequest, location: str = "body") -> Dict[str, str]:
        """Prepare headers with authentication and custom headers."""
        # Start with base headers
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'APISec-Discovery/v2.0'
        }
        
        # Apply authentication
        auth_headers = self._apply_auth(request)
        headers.update(auth_headers)
        
        # Apply custom headers
        if request.headers:
            headers.update(request.headers)
        
        # Apply content-type override
        if request.content_type_override:
            headers['Content-Type'] = request.content_type_override
        elif location == "body":
            headers['Content-Type'] = 'application/json'
        elif location == "form":
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return headers
    
    def _prepare_payload(
        self, 
        payload: Optional[Union[Dict[str, Any], str, bytes]], 
        location: str,
        request: DiscoveryRequest
    ) -> Tuple[Union[Dict[str, Any], str, bytes, None], Dict[str, str]]:
        """
        Prepare payload for different locations.
        
        Args:
            payload: Raw payload data
            location: Target location ('body', 'query', 'form', 'header')
            request: Discovery request with seed body
            
        Returns:
            Tuple of (prepared_payload, final_headers)
        """
        headers = {}
        
        if location == "body":
            # JSON body payload
            if payload is None:
                # Use seed body if no payload provided
                prepared_payload = request.seed_body or {}
            else:
                prepared_payload = payload
            
            headers['Content-Type'] = request.content_type_override or 'application/json'
            
        elif location == "query":
            # URL query parameters
            if payload is None:
                prepared_payload = {}
            else:
                prepared_payload = payload
            
            # Query parameters go in URL, not body
            prepared_payload = None
            
        elif location == "form":
            # Form data payload
            if payload is None:
                prepared_payload = {}
            else:
                prepared_payload = payload
            
            headers['Content-Type'] = request.content_type_override or 'application/x-www-form-urlencoded'
            
        elif location == "header":
            # Custom headers (payload becomes additional headers)
            if payload is None:
                prepared_payload = {}
            else:
                prepared_payload = None
            
            # Add payload as custom headers
            if isinstance(payload, dict):
                for key, value in payload.items():
                    headers[f"X-APISec-{key.title()}"] = str(value)
        
        else:
            raise ValueError(f"Unsupported location: {location}")
        
        return prepared_payload, headers
    
    async def send(
        self, 
        request: DiscoveryRequest,
        payload: Optional[Union[Dict[str, Any], str, bytes]] = None,
        location: str = "body"
    ) -> Response:
        """
        Send HTTP request with automatic auth and headers.
        
        Args:
            request: Discovery request with auth and headers
            payload: Request payload data
            location: Payload location ('body', 'query', 'form', 'header')
            
        Returns:
            HTTP response object
        """
        try:
            # Prepare headers and payload
            prepared_payload, additional_headers = self._prepare_payload(payload, location, request)
            headers = self._prepare_headers(request, location)
            headers.update(additional_headers)
            
            # Determine method and URL
            method = request.method.upper()
            url = request.url
            
            if location == "query":
                # Add query parameters to URL
                if prepared_payload:
                    parsed_url = urlparse(url)
                    existing_params = dict(q.split('=') for q in parsed_url.query.split('&') if '=' in q)
                    query_params = {**existing_params, **prepared_payload}
                    new_query = urlencode(query_params)
                    url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
                else:
                    url = request.url
            
            # Make request based on location
            if location == "query":
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=min(request.timeout_seconds, self.default_timeout),
                    allow_redirects=True
                )
            else:
                # For body, form, header locations, use POST/PUT/PATCH/DELETE
                response = self.session.request(
                    method=method,
                    url=url,
                    json=prepared_payload if location == "body" and isinstance(prepared_payload, dict) else None,
                    data=prepared_payload if location in ["form", "header"] else None,
                    headers=headers, 
                    timeout=min(request.timeout_seconds, self.default_timeout),
                    allow_redirects=True
                )
            
            return response
            
        except requests.RequestException as e:
            raise TransportClientError(f"Request failed: {str(e)}")
        except Exception as e:
            raise TransportClientError(f"Unexpected error: {str(e)}")


class MockTransportClient(TransportClientInterface):
    """
    Mock transport client for unit testing.
    
    Returns predefined responses for testing without making actual HTTP requests.
    """
    
    def __init__(self, responses: Dict[str, Response]):
        """
        Initialize mock client with predefined responses.
        
        Args:
            responses: Dictionary mapping URLs to responses
        """
        self.responses = responses
        self.request_log = []
    
    async def send(
        self, 
        request: DiscoveryRequest,
        payload: Optional[Union[Dict[str, Any], str, bytes]] = None,
        location: str = "body"
    ) -> Response:
        """Mock send request."""
        self.request_log.append({
            'method': request.method,
            'url': request.url,
            'location': location,
            'payload': payload,
            'headers': request.headers,
            'auth': request.auth.dict() if request.auth else None
        })
        return self.responses.get(request.url, self._create_error_response())
    
    def _create_error_response(self) -> Response:
        """Create a default error response."""
        response = requests.Response()
        response.status_code = 404
        response._content = b'{"error": "Mock endpoint not found"}'
        return response
    
    def get_request_log(self) -> list[Dict[str, Any]]:
        """Get log of all requests made to this mock client."""
        return self.request_log


class TransportClientError(Exception):
    """Exception raised by transport client implementations."""
    pass


# Backward compatibility functions
def create_legacy_client(timeout: int = 30) -> RequestsTransportClient:
    """
    Create legacy transport client for backward compatibility.
    
    Args:
        timeout: Default timeout
        
    Returns:
        RequestsTransportClient instance
    """
    return RequestsTransportClient(timeout)


def apply_auth_to_headers(headers: Dict[str, str], auth: Optional[AuthConfig]) -> Dict[str, str]:
    """
    Apply authentication to headers (legacy function).
    
    Args:
        headers: Existing headers
        auth: Authentication configuration
        
    Returns:
        Headers with authentication applied
    """
    if not auth or auth.type == "none":
        return headers
    
    auth_headers = headers.copy()
    
    if auth.type == "bearer":
        auth_headers['Authorization'] = f"Bearer {auth.value}"
    elif auth.type == "apikey":
        header_name = auth.header_name or "X-API-Key"
        auth_headers[header_name] = auth.value
    
    return auth_headers
