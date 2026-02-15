"""
REST Parameter Discovery v2 - Enhanced modular architecture.

This package provides a complete, modular parameter discovery system
with dependency injection, unit-testable components, and backward compatibility.
"""

# Core models and interfaces
from .models import (
    AuthConfig,
    DiscoveryRequest,
    DiscoveryContext,
    ProbeResult,
    DetectionResult,
    ConfidenceScore
)

# Transport layer
from .transport import HttpClientInterface, RequestsHttpClient

# Fingerprinting
from .fingerprint import FrameworkDetector

# Probes
from .probes import ProbeInterface, ProbeFactory

# Scoring
from .scoring import calculate_confidence

# Orchestrator
from .orchestrator import (
    DiscoveryOrchestrator,
    V2Orchestrator,
    create_v2_orchestrator,
    orchestrate_inference_v2,
)

# Backward compatibility
from .orchestrator import orchestrate_inference as legacy_orchestrate_inference

__all__ = [
    # Models
    'AuthConfig',
    'DiscoveryRequest',
    'DiscoveryContext', 
    'ProbeResult',
    'DetectionResult',
    'ConfidenceScore',
    
    # Transport
    'HttpClientInterface',
    'RequestsHttpClient',
    
    # Fingerprinting
    'FrameworkDetector',
    
    # Probes
    'ProbeInterface',
    'ProbeFactory',
    
    # Scoring
    'calculate_confidence',
    
    # Orchestrator
    'DiscoveryOrchestrator',
    'V2Orchestrator',
    'create_v2_orchestrator',
    'orchestrate_inference_v2',

    # Backward compatibility
    'legacy_orchestrate_inference'
]
