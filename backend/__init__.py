"""
API Security — schema discovery, registry, and OpenAPI diffing (frontend-backed API).
"""

from .models import (
    AuthConfig,
    DiscoveryRequest,
    DiscoveryContext,
    ProbeResult,
    DetectionResult,
    ConfidenceScore,
)

from .registry_db import (
    ApiRegistry,
    SchemaSnapshot,
)

from .probes.schema_diff_engine import (
    DiffEngine,
    DifferentialEngine,
    compare_schemas_v2,
    semantic_schema_diff,
)

__all__ = [
    "AuthConfig",
    "DiscoveryRequest",
    "DiscoveryContext",
    "ProbeResult",
    "DetectionResult",
    "ConfidenceScore",
    "ApiRegistry",
    "SchemaSnapshot",
    "DiffEngine",
    "DifferentialEngine",
    "compare_schemas_v2",
    "semantic_schema_diff",
]
