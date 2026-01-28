"""Security utilities for handling API credentials."""
from typing import Optional
from pydantic import BaseModel


class AuthCredentials(BaseModel):
    """API authentication credentials."""
    api_key: Optional[str] = None
    bearer_token: Optional[str] = None
    
    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for authentication."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers
