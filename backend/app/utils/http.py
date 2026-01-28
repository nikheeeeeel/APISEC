"""HTTP client utilities."""
import asyncio
from typing import Optional
import httpx
from app.core.config import settings
from app.core.security import AuthCredentials


class SafeHTTPClient:
    """Safe HTTP client with rate limiting and timeout controls."""
    
    def __init__(self, credentials: Optional[AuthCredentials] = None):
        """Initialize HTTP client with optional credentials."""
        self.credentials = credentials
        self._last_request_time = 0.0
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < settings.RATE_LIMIT_DELAY:
            await asyncio.sleep(settings.RATE_LIMIT_DELAY - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def get(
        self,
        url: str,
        follow_redirects: bool = True,
        timeout: Optional[int] = None
    ) -> httpx.Response:
        """
        Perform a safe GET request with rate limiting.
        
        Args:
            url: Target URL
            follow_redirects: Whether to follow redirects
            timeout: Request timeout in seconds
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: On HTTP errors
        """
        await self._rate_limit()
        
        headers = {}
        if self.credentials:
            headers.update(self.credentials.get_headers())
        
        timeout = timeout or settings.REQUEST_TIMEOUT
        
        async with httpx.AsyncClient(
            follow_redirects=follow_redirects,
            timeout=timeout
        ) as client:
            response = await client.get(url, headers=headers)
            return response
