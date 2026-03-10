"""
API Security - Schema Discovery and Diffing Module.

This package provides focused functionality for:
1. API schema discovery and monitoring
2. Differential analysis between API responses
"""

# Core models
from .models import (
    AuthConfig,
    DiscoveryRequest,
    DiscoveryContext,
    ProbeResult,
    DetectionResult,
    ConfidenceScore
)

# Schema monitoring
from .schema_monitor import (
    discover_schema,
    monitor_schema_changes,
    generate_pdf_from_json
)

# Database operations
from .registry_db import (
    SchemaSnapshot,
    APIMetadata
)

# Fingerprinting and diffing
from .fingerprint import (
    ResponseFingerprint,
    FingerprintDiff,
    create_fingerprint,
    compare_fingerprints
)

# Differential engine
from .probes.differential_engine import (
    DifferentialEngine,
    ParameterCandidate
)

__all__ = [
    # Models
    'AuthConfig',
    'DiscoveryRequest',
    'DiscoveryContext', 
    'ProbeResult',
    'DetectionResult',
    'ConfidenceScore',
    
    # Schema monitoring
    'discover_schema',
    'monitor_schema_changes',
    'generate_pdf_from_json',
    
    # Database operations
    'SchemaSnapshot',
    'APIMetadata',
    
    # Fingerprinting and diffing
    'ResponseFingerprint',
    'FingerprintDiff',
    'create_fingerprint',
    'compare_fingerprints',
    
    # Differential engine
    'DifferentialEngine',
    'ParameterCandidate'
]
