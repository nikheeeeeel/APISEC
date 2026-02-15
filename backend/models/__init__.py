"""
Data models for REST Parameter Discovery v2.

This module provides Pydantic models and dataclasses for:
- Discovery requests with contextual support
- Probe results with standard formats
- Detection results with confidence scoring
- Backward compatibility with existing v1 interface
"""

from .discovery_request import (
    AuthConfig,
    DiscoveryRequest, 
    DiscoveryContext,
    ProbeResult,
    DetectionResult,
    ConfidenceScore,
    create_legacy_request,
    create_legacy_context
)

__all__ = [
    'AuthConfig',
    'DiscoveryRequest',
    'DiscoveryContext', 
    'ProbeResult',
    'DetectionResult',
    'ConfidenceScore',
    'create_legacy_request',
    'create_legacy_context'
]
