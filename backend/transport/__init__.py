"""
Transport layer for REST Parameter Discovery v2.

This module provides enhanced HTTP client abstraction with automatic
authentication, header injection, and support for multiple payload locations.
"""

from .client import (
    TransportClientInterface,
    RequestsTransportClient,
    MockTransportClient,
    TransportClientError,
    create_legacy_client,
    apply_auth_to_headers
)

from .http_client import (
    HttpClientInterface,
    RequestsHttpClient,
    MockHttpClient,
    HttpClientError
)

__all__ = [
    # Enhanced transport client
    'TransportClientInterface',
    'RequestsTransportClient',
    'MockTransportClient',
    'TransportClientError',
    'create_legacy_client',
    'apply_auth_to_headers',
    
    # Legacy HTTP client (backward compatibility)
    'HttpClientInterface',
    'RequestsHttpClient',
    'MockHttpClient',
    'HttpClientError'
]
