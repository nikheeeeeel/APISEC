"""
Base probe interface and common functionality for REST Parameter Discovery v2.

All probe strategies must implement this interface to ensure consistency
and enable dependency injection for unit testing.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models import DiscoveryContext, ProbeResult


class ProbeInterface(ABC):
    """
    Abstract base interface for all probe strategies.
    
    All probe implementations must inherit from this interface
    to ensure consistent behavior and enable dependency injection.
    """
    
    def __init__(self, name: str):
        """
        Initialize probe with a unique name.
        
        Args:
            name: Human-readable name for the probe
        """
        self.name = name
        self.enabled = True
    
    @abstractmethod
    async def execute(self, context: DiscoveryContext) -> ProbeResult:
        """
        Execute the probe strategy.
        
        Args:
            context: Discovery context containing request and state
            
        Returns:
            ProbeResult with discovered parameters and evidence
        """
        pass
    
    @abstractmethod
    def get_required_capabilities(self) -> list[str]:
        """
        Get list of required capabilities for this probe.
        
        Returns:
            List of capability names required for this probe
        """
        pass
    
    def get_supported_content_types(self) -> list[str]:
        """
        Get list of content types this probe supports.
        
        Returns:
            List of supported content-type strings
        """
        return ["application/json"]
    
    def can_handle_request(self, context: DiscoveryContext) -> bool:
        """
        Check if this probe can handle the current request.
        
        Args:
            context: Discovery context to evaluate
            
        Returns:
            True if probe can handle this request type
        """
        return True
    
    def get_priority(self) -> int:
        """
        Get execution priority for this probe.
        
        Lower numbers = higher priority.
        
        Returns:
            Priority integer (1-10)
        """
        return 5
    
    def is_enabled(self) -> bool:
        """Check if probe is enabled."""
        return self.enabled
    
    def enable(self) -> None:
        """Enable the probe."""
        self.enabled = True
    
    def disable(self) -> None:
        """Disable the probe."""
        self.enabled = False


class BaseProbe(ProbeInterface):
    """
    Base implementation of ProbeInterface with common functionality.
    
    Provides shared methods for logging, error handling, and evidence collection.
    """
    
    def __init__(self, name: str, http_client=None):
        """
        Initialize base probe.
        
        Args:
            name: Probe name
            http_client: Optional HTTP client for dependency injection
        """
        super().__init__(name)
        self.http_client = http_client
        self.execution_count = 0
        self.success_count = 0
    
    def log_execution(self, message: str) -> None:
        """Log execution message with probe name."""
        print(f"[{self.name}] {message}")
    
    def log_error(self, error: str, exception: Optional[Exception] = None) -> None:
        """Log error message with probe name."""
        print(f"[{self.name}] ERROR: {error}")
        if exception:
            print(f"[{self.name}] Exception: {str(exception)}")
    
    def create_success_result(
        self, 
        parameters: Dict[str, Any], 
        evidence: Dict[str, Any],
        confidence: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProbeResult:
        """Create a successful probe result."""
        self.success_count += 1
        self.execution_count += 1
        
        return ProbeResult(
            success=True,
            parameters=parameters,
            evidence=evidence,
            confidence=confidence or {},
            metadata=metadata or {}
        )
    
    def create_error_result(
        self, 
        error: str, 
        evidence: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProbeResult:
        """Create an error probe result."""
        self.execution_count += 1
        
        return ProbeResult(
            success=False,
            parameters={},
            evidence=evidence or {},
            confidence={},
            metadata=metadata or {},
            error=error
        )
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for this probe."""
        return {
            'name': self.name,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'success_rate': self.success_count / max(self.execution_count, 1)
        }


class ProbeCapability:
    """
    Enumeration of probe capabilities.
    
    Used for dependency injection and capability matching.
    """
    ERROR_ANALYSIS = "error_analysis"
    SUCCESS_ANALYSIS = "success_analysis"
    TYPE_INFERENCE = "type_inference"
    NULL_TESTING = "null_testing"
    BOUNDARY_TESTING = "boundary_testing"
    AUTHENTICATION = "authentication"
    CONTENT_TYPE_DETECTION = "content_type_detection"
    FRAMEWORK_DETECTION = "framework_detection"


class ProbeFactory:
    """
    Factory for creating probe instances with dependency injection.
    
    Enables clean separation of probe creation and configuration.
    """
    
    def __init__(self):
        """Initialize factory with available probe classes."""
        self._probe_classes = {}
        self._probe_instances = {}
    
    def register_probe(self, name: str, probe_class: type) -> None:
        """
        Register a probe class with the factory.
        
        Args:
            name: Unique name for the probe
            probe_class: Class that implements ProbeInterface
        """
        self._probe_classes[name] = probe_class
    
    def create_probe(self, name: str, **kwargs) -> Optional[ProbeInterface]:
        """
        Create a probe instance by name.
        
        Args:
            name: Registered probe name
            **kwargs: Additional arguments for probe construction
            
        Returns:
            Probe instance or None if not found
        """
        if name not in self._probe_classes:
            return None
        
        probe_class = self._probe_classes[name]
        return probe_class(**kwargs)
    
    def get_available_probes(self) -> list[str]:
        """Get list of registered probe names."""
        return list(self._probe_classes.keys())
    
    def create_probes_for_context(self, context: DiscoveryContext) -> list[ProbeInterface]:
        """
        Create appropriate probes for the given context.
        
        Args:
            context: Discovery context to evaluate
            
        Returns:
            List of probe instances that can handle this context
        """
        probes = []
        for probe_name in self.get_available_probes():
            probe = self.create_probe(probe_name)
            if probe and probe.can_handle_request(context):
                probes.append(probe)
        
        # Sort by priority
        probes.sort(key=lambda p: p.get_priority())
        return probes
