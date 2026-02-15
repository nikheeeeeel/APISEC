"""
Enhanced data models for REST Parameter Discovery v2.

This module provides Pydantic models for discovery requests with
contextual REST support including authentication, seed bodies, and content-type overrides.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Literal, Any
from pydantic import BaseModel, Field, validator


class AuthConfig(BaseModel):
    """
    Authentication configuration for discovery requests.
    
    Supports multiple authentication types commonly used in REST APIs.
    """
    type: Literal["none", "bearer", "apikey"] = Field(
        default="none", 
        description="Authentication type: none, bearer, or apikey"
    )
    value: Optional[str] = Field(
        default=None, 
        description="Authentication value (token, API key, etc.)"
    )
    header_name: Optional[str] = Field(
        default=None,
        description="Custom header name for authentication (e.g., 'X-API-Key')"
    )

    @validator('header_name')
    def validate_header_name(cls, v, values):
        """Validate that header_name is provided when type is apikey."""
        if values.get('type') == 'apikey' and not v:
            raise ValueError('header_name is required when auth type is apikey')
        return v


class DiscoveryRequest(BaseModel):
    """
    Enhanced discovery request with contextual REST support.
    
    Extends basic discovery with authentication, custom headers, seed bodies,
    and content-type overrides for more sophisticated parameter discovery.
    """
    url: str = Field(
        ..., 
        description="Target API endpoint URL"
    )
    method: str = Field(
        default="POST", 
        description="HTTP method (GET, POST, PUT, DELETE, PATCH)"
    )
    headers: Dict[str, str] = Field(
        default_factory=dict, 
        description="Custom HTTP headers to include in requests"
    )
    auth: Optional[AuthConfig] = Field(
        default=None, 
        description="Authentication configuration"
    )
    seed_body: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Seed request body for starting discovery"
    )
    content_type_override: Optional[str] = Field(
        default=None, 
        description="Force specific content type for requests"
    )
    timeout_seconds: int = Field(
        default=5, 
        ge=1, 
        le=300,
        description="Timeout in seconds (1-300)"
    )

    @validator('method')
    def validate_method(cls, v):
        """Validate HTTP method."""
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if v.upper() not in allowed_methods:
            raise ValueError(f'Method must be one of: {", ".join(allowed_methods)}')
        return v.upper()

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    class Config:
        """Pydantic configuration."""
        extra = "forbid"  # Prevent additional fields
        validate_assignment = True  # Validate on assignment


class DiscoveryContext(BaseModel):
    """
    Context object passed to all probes and modules.
    
    Contains request information, HTTP client, and shared state
    for the current discovery session.
    """
    request: DiscoveryRequest
    session_headers: Dict[str, str] = Field(default_factory=dict)
    discovered_parameters: Dict[str, Any] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    execution_stats: Dict[str, Any] = Field(default_factory=dict)
    
    def add_evidence(self, key: str, evidence: Any) -> None:
        """Add evidence to the discovery context."""
        self.evidence[key] = evidence
    
    def add_parameter(self, name: str, info: Any) -> None:
        """Add discovered parameter to context."""
        self.discovered_parameters[name] = info
    
    def update_stats(self, key: str, value: Any) -> None:
        """Update execution statistics."""
        self.execution_stats[key] = value


class ProbeResult(BaseModel):
    """
    Standard result format for all probe strategies.
    
    Ensures consistent output format across different probe implementations.
    """
    success: bool = Field(description="Whether probe completed successfully")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Discovered parameters from this probe"
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Evidence collected during probing"
    )
    confidence: Dict[str, float] = Field(
        default_factory=dict, 
        description="Confidence scores for discovered parameters"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional probe metadata"
    )
    error: Optional[str] = Field(
        default=None, 
        description="Error message if probe failed"
    )


class DetectionResult(BaseModel):
    """
    Standard result format for all detection modules.
    
    Ensures consistent output across fingerprinting modules.
    """
    detected_type: str = Field(description="Type of detection result")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ConfidenceScore(BaseModel):
    """
    Confidence score with supporting evidence.
    
    Used for scoring and evidence merging modules.
    """
    score: float = Field(ge=0.0, le=1.0, description="Confidence score")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    sources: List[str] = Field(default_factory=list, description="Source probes/modules")
    calculation_method: str = Field(description="Method used for calculation")


# Backward compatibility functions
def create_legacy_request(url: str, method: str = "POST", max_time_seconds: int = 30) -> DiscoveryRequest:
    """
    Create DiscoveryRequest from legacy function parameters.
    
    Maintains backward compatibility with existing orchestrate_inference function.
    """
    return DiscoveryRequest(
        url=url,
        method=method,
        timeout_seconds=max_time_seconds
    )


def create_legacy_context(discovery_request: DiscoveryRequest) -> Dict[str, Any]:
    """
    Create legacy context dictionary from DiscoveryRequest.
    
    Maintains backward compatibility with existing probe functions.
    """
    return {
        'url': discovery_request.url,
        'method': discovery_request.method,
        'timeout_seconds': discovery_request.timeout_seconds,
        'headers': discovery_request.headers,
        'auth': discovery_request.auth.dict() if discovery_request.auth else None,
        'seed_body': discovery_request.seed_body,
        'content_type_override': discovery_request.content_type_override
    }
