"""
Orchestrator module for REST Parameter Discovery v2.

This module provides coordination of discovery phases with
dependency injection and modular architecture.
"""

from .discovery_orchestrator import (
    DiscoveryOrchestrator,
    orchestrate_inference  # Backward compatibility
)
from .v2_orchestrator import (
    V2Orchestrator,
    create_v2_orchestrator,
    orchestrate_inference_v2
)

__all__ = [
    'DiscoveryOrchestrator',
    'orchestrate_inference',
    'V2Orchestrator',
    'create_v2_orchestrator',
    'orchestrate_inference_v2'
]
