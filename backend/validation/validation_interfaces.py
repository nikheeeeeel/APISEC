"""
Validation interfaces and protocols for REST Parameter Discovery v2.

Defines contracts for validation components to ensure dependency inversion
and architectural compliance with enterprise standards.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum


class ValidationCategory(Enum):
    """Typed validation categories."""
    ARCHITECTURAL_INTEGRITY = "architectural_integrity"
    BEHAVIORAL_CORRECTNESS = "behavioral_correctness"
    PERFORMANCE = "performance"
    REAL_WORLD = "real_world"
    FALSE_POSITIVE_PREVENTION = "false_positive_prevention"


class ValidationStatus(Enum):
    """Validation result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class ValidationConfig:
    """Immutable configuration for validation behavior."""
    strict_mode: bool
    performance_targets: Dict[str, float]
    real_world_endpoints: List[str]
    max_runtime_seconds: float
    false_positive_threshold: float
    live_validation_enabled: bool
    confidence_thresholds: Dict[str, float]
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.false_positive_threshold < 0 or self.false_positive_threshold > 1:
            raise ValueError("False positive threshold must be between 0 and 1")
        if self.max_runtime_seconds <= 0:
            raise ValueError("Max runtime must be positive")


@dataclass
class ValidationResult:
    """Structured validation result."""
    test_name: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any]
    duration_ms: float
    category: ValidationCategory


class ParameterDiscoveryEngine(Protocol):
    """Protocol for parameter discovery engines."""
    
    async def discover_parameters(self, request: 'DiscoveryRequest') -> Dict[str, Any]:
        """Discover parameters from API endpoint."""
        ...


class ValidationEngine(ABC):
    """Abstract base for validation engines."""
    
    @abstractmethod
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Execute validation with given configuration."""
        pass
    
    @abstractmethod
    def get_category(self) -> ValidationCategory:
        """Get validation category."""
        pass


class StaticValidationEngine(ValidationEngine):
    """Static validation without network dependencies."""
    
    def __init__(self, discovery_engine: Optional[ParameterDiscoveryEngine] = None):
        """Initialize with optional discovery engine."""
        self.discovery_engine = discovery_engine
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Execute static validation."""
        return []
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return ValidationCategory.ARCHITECTURAL_INTEGRITY


class UnitValidationEngine(ValidationEngine):
    """Unit validation with mocked transport layer."""
    
    def __init__(self, discovery_engine: ParameterDiscoveryEngine):
        """Initialize with discovery engine."""
        self.discovery_engine = discovery_engine
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Execute unit validation with mocks."""
        return []
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return ValidationCategory.BEHAVIORAL_CORRECTNESS


class IntegrationValidationEngine(ValidationEngine):
    """Integration validation with optional live mode."""
    
    def __init__(self, discovery_engine: ParameterDiscoveryEngine):
        """Initialize with discovery engine."""
        self.discovery_engine = discovery_engine
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Execute integration validation."""
        if not config.live_validation_enabled:
            return []
        return []
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return ValidationCategory.REAL_WORLD
