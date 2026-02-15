"""
HTTP client abstraction for REST Parameter Discovery v2.

Provides dependency-injectable HTTP client interface with support for
multiple authentication types, content types, and request building.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import requests
from requests import Response
from ..models import AuthConfig


class HttpClientInterface(ABC):
    """
    Abstract interface for HTTP clients.
    
    Enables dependency injection and mocking for unit testing.
    """
    
    @abstractmethod
    async def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP GET request."""
        pass
    
    @abstractmethod
    async def post(
        self, 
        url: str, 
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP POST request."""
        pass
    
    @abstractmethod
    async def put(
        self, 
        url: str, 
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP PUT request."""
        pass
    
    @abstractmethod
    async def delete(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP DELETE request."""
        pass
    
    @abstractmethod
    async def patch(
        self, 
        url: str, 
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP PATCH request."""
        pass


class RequestsHttpClient(HttpClientInterface):
    """
    Production HTTP client implementation using requests library.
    
    Provides full HTTP functionality with authentication support,
    content-type handling, and proper error handling.
    """
    
    def __init__(self, default_timeout: int = 30):
        """
        Initialize HTTP client.
        
        Args:
            default_timeout: Default timeout for requests
        """
        self.default_timeout = default_timeout
        self.session = requests.Session()
        
        # Configure session defaults
        self.session.headers.update({
            'User-Agent': 'APISec-Discovery/2.0',
            'Accept': 'application/json, text/plain, */*'
        })
    
    def _apply_auth(self, headers: Dict[str, str], auth: Optional[AuthConfig]) -> Dict[str, str]:
        """Apply authentication configuration to headers."""
        if not auth or auth.type == "none":
            return headers
        
        auth_headers = headers.copy()
        
        if auth.type == "bearer":
            auth_headers['Authorization'] = f"Bearer {auth.value}"
        elif auth.type == "apikey":
            header_name = auth.header_name or "X-API-Key"
            auth_headers[header_name] = auth.value
        
        return auth_headers
    
    def _prepare_headers(
        self, 
        base_headers: Optional[Dict[str, str]], 
        auth: Optional[AuthConfig]
    ) -> Dict[str, str]:
        """Prepare headers with authentication and defaults."""
        headers = base_headers.copy() if base_headers else {}
        
        # Apply authentication
        headers = self._apply_auth(headers, auth)
        
        # Ensure content-type for POST/PUT/PATCH
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        return headers
    
    async def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP GET request."""
        try:
            prepared_headers = self._prepare_headers(headers, None)
            response = self.session.get(
                url, 
                headers=prepared_headers, 
                timeout=min(timeout, self.default_timeout)
            )
            return response
        except requests.RequestException as e:
            raise HttpClientError(f"GET request failed: {str(e)}")
    
    async def post(
        self, 
        url: str, 
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP POST request."""
        try:
            prepared_headers = self._prepare_headers(headers, None)
            response = self.session.post(
                url, 
                json=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None,
                headers=prepared_headers, 
                timeout=min(timeout, self.default_timeout)
            )
            return response
        except requests.RequestException as e:
            raise HttpClientError(f"POST request failed: {str(e)}")
    
    async def put(
        self, 
        url: str, 
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP PUT request."""
        try:
            prepared_headers = self._prepare_headers(headers, None)
            response = self.session.put(
                url, 
                json=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None,
                headers=prepared_headers, 
                timeout=min(timeout, self.default_timeout)
            )
            return response
        except requests.RequestException as e:
            raise HttpClientError(f"PUT request failed: {str(e)}")
    
    async def delete(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP DELETE request."""
        try:
            prepared_headers = self._prepare_headers(headers, None)
            response = self.session.delete(
                url, 
                headers=prepared_headers, 
                timeout=min(timeout, self.default_timeout)
            )
            return response
        except requests.RequestException as e:
            raise HttpClientError(f"DELETE request failed: {str(e)}")
    
    async def patch(
        self, 
        url: str, 
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Response:
        """Execute HTTP PATCH request."""
        try:
            prepared_headers = self._prepare_headers(headers, None)
            response = self.session.patch(
                url, 
                json=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None,
                headers=prepared_headers, 
                timeout=min(timeout, self.default_timeout)
            )
            return response
        except requests.RequestException as e:
            raise HttpClientError(f"PATCH request failed: {str(e)}")


class HttpClientError(Exception):
    """Exception raised by HTTP client implementations."""
    pass


class MockHttpClient(HttpClientInterface):
    """
    Mock HTTP client for unit testing.
    
    Returns predefined responses for testing probe logic
    without making actual HTTP requests.
    """
    
    def __init__(self, responses: Dict[str, Response]):
        """
        Initialize mock client with predefined responses.
        
        Args:
            responses: Dictionary mapping URLs to responses
        """
        self.responses = responses
        self.request_log = []
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Response:
        """Mock GET request."""
        self.request_log.append({'method': 'GET', 'url': url, 'headers': headers})
        return self.responses.get(url, self._create_error_response())
    
    async def post(self, url: str, data: Optional[Union[Dict[str, Any], str, bytes]] = None, 
                  headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Response:
        """Mock POST request."""
        self.request_log.append({'method': 'POST', 'url': url, 'data': data, 'headers': headers})
        return self.responses.get(url, self._create_error_response())
    
    async def put(self, url: str, data: Optional[Union[Dict[str, Any], str, bytes]] = None,
                  headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Response:
        """Mock PUT request."""
        self.request_log.append({'method': 'PUT', 'url': url, 'data': data, 'headers': headers})
        return self.responses.get(url, self._create_error_response())
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Response:
        """Mock DELETE request."""
        self.request_log.append({'method': 'DELETE', 'url': url, 'headers': headers})
        return self.responses.get(url, self._create_error_response())
    
    async def patch(self, url: str, data: Optional[Union[Dict[str, Any], str, bytes]] = None,
                   headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Response:
        """Mock PATCH request."""
        self.request_log.append({'method': 'PATCH', 'url': url, 'data': data, 'headers': headers})
        return self.responses.get(url, self._create_error_response())
    
    def _create_error_response(self) -> Response:
        """Create a default error response."""
        import requests
        return requests.Response()
        response.status_code = 404
        response._content = b'{"error": "Mock endpoint not found"}'
    
    def get_request_log(self) -> list[Dict[str, Any]]:
        """Get log of all requests made to this mock client."""
        return self.request_log
