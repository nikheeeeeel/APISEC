"""
Discovery orchestrator for REST Parameter Discovery v2.

Coordinates all discovery phases with dependency injection,
modular architecture, and backward compatibility.
"""

import time
from typing import List, Optional, Dict, Any
from ..models import (
    DiscoveryRequest, DiscoveryContext, ProbeResult, DetectionResult,
    create_legacy_context
)
from ..transport import TransportClientInterface, RequestsTransportClient
from ..probes import ProbeFactory
from ..fingerprint import FrameworkDetector
from ..scoring import calculate_confidence, filter_parameters_by_confidence


class DiscoveryOrchestrator:
    """
    Main orchestrator for parameter discovery with modular architecture.
    
    Coordinates transport, fingerprinting, probing, and scoring phases
without containing business logic, enabling clean separation of concerns.
    """
    
    def __init__(
        self,
        transport_client: TransportClientInterface,
        probe_factory: ProbeFactory,
        framework_detector: FrameworkDetector
    ):
        """
        Initialize orchestrator with dependency injection.
        
        Args:
            transport_client: Enhanced transport client for making requests
            probe_factory: Factory for creating probe instances
            framework_detector: Framework detector for API analysis
        """
        self.transport_client = transport_client
        self.probe_factory = probe_factory
        self.framework_detector = framework_detector
    
    async def discover_parameters(
        self, 
        request: DiscoveryRequest
    ) -> Dict[str, Any]:
        """
        Orchestrate complete parameter discovery process.
        
        Args:
            request: Enhanced discovery request with context
            
        Returns:
            Dictionary with discovered parameters and metadata
        """
        print(f"🚀 Starting REST Parameter Discovery v2")
        print(f"Target: {request.url}")
        print(f"Method: {request.method}")
        print(f"Timeout: {request.timeout_seconds}s")
        print("=" * 60)
        
        start_time = time.time()
        
        # Create discovery context
        context = DiscoveryContext(
            request=request,
            session_headers=request.headers.copy()
        )
        
        try:
            # Phase 1: Fingerprinting
            print("\n🔍 Phase 1: Framework Fingerprinting...")
            framework_result = await self._execute_fingerprinting_phase(context)
            
            # Phase 2: Probing
            print("\n🔬 Phase 2: Parameter Probing...")
            probe_results = await self._execute_probing_phase(context, framework_result)
            
            # Phase 3: Scoring and Aggregation
            print("\n📊 Phase 3: Confidence Scoring...")
            scored_parameters = await self._execute_scoring_phase(
                context, probe_results, framework_result
            )
            
            # Phase 4: Result Assembly
            print("\n📋 Phase 4: Result Assembly...")
            final_result = await self._assemble_results(
                context, scored_parameters, framework_result, time.time() - start_time
            )
            
            print(f"\n✅ Discovery Complete: {len(final_result.get('parameters', {}))} parameters")
            print(f"⏱️  Execution Time: {final_result.get('meta', {}).get('execution_time_ms', 0)}ms")
            
            return final_result
            
        except Exception as e:
            print(f"\n❌ Discovery Failed: {str(e)}")
            return self._create_error_result(request, str(e), time.time() - start_time)
    
    async def _execute_fingerprinting_phase(
        self, 
        context: DiscoveryContext
    ) -> Optional[DetectionResult]:
        """Execute framework fingerprinting phase."""
        try:
            # Make detection request using enhanced transport client
            sample_response = await self.framework_detector.make_detection_request(context)
            
            # Analyze framework
            framework_result = await self.framework_detector.detect_framework(
                context, sample_response
            )
            
            print(f"   Framework: {framework_result.detected_type}")
            print(f"   Confidence: {framework_result.confidence:.2f}")
            
            # Store framework info in context
            context.add_evidence('framework_detection', framework_result.dict())
            
            return framework_result
            
        except Exception as e:
            print(f"   Framework detection failed: {str(e)}")
            return None
    
    async def _execute_probing_phase(
        self, 
        context: DiscoveryContext,
        framework_result: Optional[DetectionResult]
    ) -> List[ProbeResult]:
        """Execute parameter probing phase."""
        probe_results = []
        
        # Get framework-specific strategies
        framework_type = framework_result.detected_type if framework_result else 'unknown'
        framework_strategies = self.framework_detector.get_framework_specific_strategies(framework_type)
        
        print(f"   Strategies: {', '.join(framework_strategies)}")
        
        # Create appropriate probes
        probes = self.probe_factory.create_probes_for_context(context)
        
        # Execute probes in priority order
        for probe in probes:
            if not probe.is_enabled():
                continue
                
            print(f"   Executing: {probe.name}")
            
            try:
                probe_start = time.time()
                result = await probe.execute(context)
                probe_time = time.time() - probe_start
                
                if result.success:
                    print(f"   ✓ {probe.name}: {len(result.parameters)} parameters ({probe_time:.2f}s)")
                    # Add discovered parameters to context
                    for param_name, param_info in result.parameters.items():
                        context.add_parameter(param_name, param_info)
                else:
                    print(f"   ✗ {probe.name}: {result.error or 'Failed'} ({probe_time:.2f}s)")
                
                probe_results.append(result)
                context.update_stats(f'probe_{probe.name}_time', probe_time)
                
            except Exception as e:
                print(f"   ✗ {probe.name}: Exception - {str(e)}")
                probe_results.append(probe.create_error_result(str(e)))
        
        return probe_results
    
    async def _execute_scoring_phase(
        self,
        context: DiscoveryContext,
        probe_results: List[ProbeResult],
        framework_result: Optional[DetectionResult]
    ) -> Dict[str, Any]:
        """Execute confidence scoring phase."""
        scored_parameters = {}
        
        for param_name in context.discovered_parameters.keys():
            # Calculate confidence for each parameter
            confidence_score = calculate_confidence(
                parameter_name=param_name,
                probe_results=probe_results,
                detection_results=[framework_result] if framework_result else [],
                evidence_sources=['probe', 'detection']
            )
            
            # Update parameter info with confidence
            param_info = context.discovered_parameters[param_name]
            if isinstance(param_info, dict):
                param_info['confidence'] = confidence_score.score
                param_info['evidence'] = confidence_score.evidence
                param_info['sources'] = confidence_score.sources
            
            scored_parameters[param_name] = confidence_score
        
        # Filter by confidence threshold
        filtered_parameters = filter_parameters_by_confidence(scored_parameters, 0.3)
        
        print(f"   Parameters with confidence ≥0.3: {len(filtered_parameters)}")
        
        return scored_parameters
    
    async def _assemble_results(
        self,
        context: DiscoveryContext,
        scored_parameters: Dict[str, Any],
        framework_result: Optional[DetectionResult],
        execution_time: float
    ) -> Dict[str, Any]:
        """Assemble final discovery results."""
        # Filter parameters for final output
        final_parameters = {}
        for param_name, confidence_score in scored_parameters.items():
            if confidence_score.score >= 0.3:  # Only include parameters with decent confidence
                param_info = context.discovered_parameters.get(param_name, {})
                final_parameters[param_name] = {
                    'name': param_name,
                    'location': param_info.get('location', 'body'),
                    'type': param_info.get('type', 'string'),
                    'required': param_info.get('required', False),
                    'confidence': confidence_score.score,
                    'evidence': confidence_score.evidence,
                    'sources': confidence_score.sources
                }
        
        # Assemble metadata
        metadata = {
            'total_parameters': len(final_parameters),
            'execution_time_ms': int(execution_time * 1000),
            'discovery_version': 'v2',
            'framework_detection': framework_result.dict() if framework_result else None,
            'probe_execution_stats': {
                result.metadata.get('probe_name'): result.get_execution_stats()
                for result in context.execution_stats.get('probe_results', [])
            }
        }
        
        return {
            'url': context.request.url,
            'method': context.request.method,
            'parameters': list(final_parameters.values()),
            'meta': metadata
        }
    
    def _create_error_result(
        self,
        request: DiscoveryRequest,
        error_message: str,
        execution_time: float
    ) -> Dict[str, Any]:
        """Create error result for failed discovery."""
        return {
            'url': request.url,
            'method': request.method,
            'parameters': [],
            'meta': {
                'total_parameters': 0,
                'execution_time_ms': int(execution_time * 1000),
                'discovery_version': 'v2',
                'error': error_message
            }
        }


# Backward compatibility wrapper
async def orchestrate_inference(
    url: str, 
    method: str = "POST", 
    max_time_seconds: int = 30
) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for existing orchestrate_inference function.
    
    Maintains compatibility with v1 interface while using v2 implementation.
    """
    from ..models import create_legacy_request
    from ..transport import RequestsHttpClient
    from ..probes import ProbeFactory
    from ..fingerprint import FrameworkDetector

    # Create v2 request from legacy parameters
    request = create_legacy_request(url, method, max_time_seconds)
    
    # Create dependencies
    http_client = RequestsHttpClient()
    probe_factory = ProbeFactory()
    framework_detector = FrameworkDetector(http_client)
    
    # Create and execute orchestrator
    orchestrator = DiscoveryOrchestrator(http_client, probe_factory, framework_detector)
    return await orchestrator.discover_parameters(request)
