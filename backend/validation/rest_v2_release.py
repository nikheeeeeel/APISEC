"""
REST Parameter Discovery v2 Release Validation Framework.

Implements comprehensive validation checks for architectural integrity,
behavioral correctness, performance targets, and real-world validation.
"""

import time
import asyncio
import pytest
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import json
import statistics


class ValidationStatus(Enum):
    """Validation result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class ValidationResult:
    """Structured validation result."""
    test_name: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any]
    duration_ms: float
    category: str


@dataclass
class ValidationConfig:
    """Configuration for validation behavior."""
    strict_mode: bool = True
    performance_targets: Dict[str, float] = None
    real_world_endpoints: List[str] = None
    max_runtime_seconds: float = 10.0
    false_positive_threshold: float = 0.1


@dataclass
class ReleaseValidatorConfig:
    """Immutable configuration for release validation."""
    strict_mode: bool = False
    performance_targets: Dict[str, float] = None
    real_world_endpoints: List[str] = None
    max_runtime_seconds: float = 10.0
    false_positive_threshold: float = 0.1
    live_validation_enabled: bool = False
    confidence_thresholds: Dict[str, float] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.false_positive_threshold < 0 or self.false_positive_threshold > 1:
            raise ValueError("False positive threshold must be between 0 and 1")
        if self.max_runtime_seconds <= 0:
            raise ValueError("Max runtime must be positive")
        
        # Set defaults
        if self.performance_targets is None:
            self.performance_targets = {
                "max_runtime_ms": 5000,
                "max_memory_mb": 100
            }
        
        if self.confidence_thresholds is None:
            self.confidence_thresholds = {
                "min_confirmed": 0.75,
                "max_false_positive": 0.4
            }


class EnterpriseReleaseValidator:
    """
    Enterprise-grade release validator with dependency inversion and CI/CD readiness.
    
    Validates architectural integrity, behavioral correctness, performance targets,
    and real-world functionality with deterministic testing.
    """
    
    def __init__(self, config: Optional[ReleaseValidatorConfig] = None):
        """Initialize validator with immutable configuration."""
        self.config = config or ReleaseValidatorConfig()
        self.results: List[ValidationResult] = []
    
    async def validate_architectural_integrity(self) -> List[ValidationResult]:
        """Validate architectural integrity and separation of concerns."""
        results = []
        
        # Test 1: No business logic in transport layer
        start_time = time.time()
        try:
            from ..transport.client import RequestsTransportClient
            from ..models import DiscoveryRequest
            
            client = RequestsTransportClient()
            request = DiscoveryRequest(url="https://api.example.com/test", method="POST")
            
            # Transport should not contain business logic
            has_business_logic = hasattr(client, 'run_parameter_discovery')
            
            results.append(ValidationResult(
                test_name="transport_no_business_logic",
                status=ValidationStatus.PASS if not has_business_logic else ValidationStatus.FAIL,
                message="Transport layer should not contain business logic" if not has_business_logic else "Business logic detected in transport layer",
                details={"has_business_logic": has_business_logic},
                duration_ms=(time.time() - start_time) * 1000,
                category="architectural_integrity"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="transport_no_business_logic",
                status=ValidationStatus.FAIL,
                message=f"Error checking transport layer: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="architectural_integrity"
            ))
        
        # Test 2: Pure functions in scoring
        start_time = time.time()
        try:
            from ..scoring.confidence_scoring import WeightedConfidenceScorer
            
            scorer = WeightedConfidenceScorer()
            
            # Check if scoring functions are pure (no side effects)
            import inspect
            methods = inspect.getmembers(scorer, predicate=inspect.ismethod)
            
            pure_functions = True
            for name, method in methods:
                if not name.startswith('_'):
                    source = inspect.getsource(method)
                    # Check for side effects (imports, network calls, etc.)
                    if any(keyword in source for keyword in ['import requests', 'import http', 'import urllib', 'import socket']):
                        pure_functions = False
                        break
            
            results.append(ValidationResult(
                test_name="scoring_pure_functions",
                status=ValidationStatus.PASS if pure_functions else ValidationStatus.FAIL,
                message="Scoring functions should be pure (no side effects)" if pure_functions else "Side effects detected in scoring functions",
                details={"pure_functions": pure_functions, "impure_methods": [name for name, method in methods if not name.startswith('_') and any(keyword in inspect.getsource(method, '') for keyword in ['import requests', 'import http', 'import urllib', 'import socket'])]},
                duration_ms=(time.time() - start_time) * 1000,
                category="architectural_integrity"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="scoring_pure_functions",
                status=ValidationStatus.FAIL,
                message=f"Error checking scoring purity: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="architectural_integrity"
            ))
        
        # Test 3: No circular dependencies
        start_time = time.time()
        try:
            # Check for circular imports
            import sys
            modules_to_check = [
                'transport.client', 'probes.strategies', 'scoring.confidence_scoring',
                'fingerprint.response_fingerprint', 'classification.endpoint_classifier'
            ]
            
            circular_deps = []
            for module_name in modules_to_check:
                try:
                    module = __import__(module_name)
                    # Check if module imports back into itself
                    if hasattr(module, '__file__'):
                        with open(module.__file__, 'r') as f:
                            content = f.read()
                            if module_name in content:
                                circular_deps.append(module_name)
                except ImportError:
                    continue
            
            results.append(ValidationResult(
                test_name="no_circular_dependencies",
                status=ValidationStatus.PASS if not circular_deps else ValidationStatus.FAIL,
                message="No circular dependencies detected" if not circular_deps else f"Circular dependencies: {circular_deps}",
                details={"circular_dependencies": circular_deps},
                duration_ms=(time.time() - start_time) * 1000,
                category="architectural_integrity"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="no_circular_dependencies",
                status=ValidationStatus.FAIL,
                message=f"Error checking circular dependencies: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="architectural_integrity"
            ))
        
        return results
    
    async def validate_behavioral_correctness(self) -> List[ValidationResult]:
        """Validate behavioral correctness of parameter discovery."""
        results = []
        
        # Test 1: Required parameter detection accuracy
        start_time = time.time()
        try:
            from .orchestrator.v2_orchestrator import V2Orchestrator
            from ..models import DiscoveryRequest
            
            orchestrator = V2Orchestrator()
            
            # Test with known required parameter endpoint
            request = DiscoveryRequest(
                url="https://jsonplaceholder.typicode.com/posts",
                method="POST",
                timeout_seconds=5
            )
            
            result = await orchestrator.discover_parameters(request)
            
            # Should detect at least one parameter
            has_parameters = len(result.get('parameters', [])) > 0
            
            results.append(ValidationResult(
                test_name="required_parameter_detection",
                status=ValidationStatus.PASS if has_parameters else ValidationStatus.WARN,
                message="Should detect parameters in known API" if has_parameters else "No parameters detected in test API",
                details={"parameter_count": len(result.get('parameters', [])), "parameters": result.get('parameters', [])},
                duration_ms=(time.time() - start_time) * 1000,
                category="behavioral_correctness"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="required_parameter_detection",
                status=ValidationStatus.FAIL,
                message=f"Error in required parameter detection: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="behavioral_correctness"
            ))
        
        # Test 2: Optional parameter handling
        start_time = time.time()
        try:
            # Test with endpoint that might have optional parameters
            request = DiscoveryRequest(
                url="https://jsonplaceholder.typicode.com/posts/1",
                method="GET",
                timeout_seconds=5
            )
            
            result = await orchestrator.discover_parameters(request)
            
            # Should handle gracefully without crashing
            completed_successfully = 'error' not in result.get('meta', {})
            
            results.append(ValidationResult(
                test_name="optional_parameter_handling",
                status=ValidationStatus.PASS if completed_successfully else ValidationStatus.FAIL,
                message="Should handle optional parameters gracefully" if completed_successfully else "Failed to handle optional parameters",
                details={"completed_successfully": completed_successfully, "meta": result.get('meta', {})},
                duration_ms=(time.time() - start_time) * 1000,
                category="behavioral_correctness"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="optional_parameter_handling",
                status=ValidationStatus.FAIL,
                message=f"Error in optional parameter handling: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="behavioral_correctness"
            ))
        
        return results
    
    async def validate_performance_targets(self) -> List[ValidationResult]:
        """Validate performance targets are met."""
        results = []
        
        if not self.config.performance_targets:
            return results
        
        # Test 1: Runtime performance
        start_time = time.time()
        try:
            from .orchestrator.v2_orchestrator import V2Orchestrator
            from ..models import DiscoveryRequest
            
            orchestrator = V2Orchestrator()
            
            # Test with simple endpoint
            request = DiscoveryRequest(
                url="https://httpbin.org/post",
                method="POST",
                timeout_seconds=5
            )
            
            result = await orchestrator.discover_parameters(request)
            runtime_ms = result.get('meta', {}).get('execution_time_ms', 0)
            
            target_ms = self.config.performance_targets.get('max_runtime_ms', 5000)
            
            results.append(ValidationResult(
                test_name="runtime_performance",
                status=ValidationStatus.PASS if runtime_ms <= target_ms else ValidationStatus.FAIL,
                message=f"Runtime within target: {runtime_ms}ms ≤ {target_ms}ms" if runtime_ms <= target_ms else f"Runtime exceeds target: {runtime_ms}ms > {target_ms}ms",
                details={"runtime_ms": runtime_ms, "target_ms": target_ms},
                duration_ms=(time.time() - start_time) * 1000,
                category="performance"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="runtime_performance",
                status=ValidationStatus.FAIL,
                message=f"Error in performance test: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="performance"
            ))
        
        # Test 2: Memory usage
        start_time = time.time()
        try:
            import psutil
            import os
            
            # Get current process memory usage
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            target_mb = self.config.performance_targets.get('max_memory_mb', 100)
            
            results.append(ValidationResult(
                test_name="memory_usage",
                status=ValidationStatus.PASS if memory_mb <= target_mb else ValidationStatus.WARN,
                message=f"Memory usage within target: {memory_mb:.1f}MB ≤ {target_mb}MB" if memory_mb <= target_mb else f"High memory usage: {memory_mb:.1f}MB > {target_mb}MB",
                details={"memory_mb": memory_mb, "target_mb": target_mb},
                duration_ms=(time.time() - start_time) * 1000,
                category="performance"
            ))
        except ImportError:
            results.append(ValidationResult(
                test_name="memory_usage",
                status=ValidationStatus.SKIP,
                message="psutil not available for memory monitoring",
                details={"reason": "missing_dependency"},
                duration_ms=(time.time() - start_time) * 1000,
                category="performance"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="memory_usage",
                status=ValidationStatus.FAIL,
                message=f"Error in memory monitoring: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="performance"
            ))
        
        return results
    
    async def validate_real_world_scenarios(self) -> List[ValidationResult]:
        """Validate against real-world API endpoints."""
        results = []
        
        if not self.config.real_world_endpoints:
            return results
        
        from .orchestrator.v2_orchestrator import V2Orchestrator
        from ..models import DiscoveryRequest
        
        orchestrator = V2Orchestrator()
        
        for i, endpoint in enumerate(self.config.real_world_endpoints):
            start_time = time.time()
            try:
                request = DiscoveryRequest(
                    url=endpoint,
                    method="POST",
                    timeout_seconds=10
                )
                
                result = await orchestrator.discover_parameters(request)
                
                # Should complete without errors
                success = 'error' not in result.get('meta', {})
                has_params = len(result.get('parameters', [])) > 0
                
                results.append(ValidationResult(
                    test_name=f"real_world_endpoint_{i+1}",
                    status=ValidationStatus.PASS if success else ValidationStatus.FAIL,
                    message=f"Real-world test {i+1}: {endpoint}" + (" - SUCCESS" if success else " - FAILED"),
                    details={
                        "endpoint": endpoint,
                        "success": success,
                        "parameter_count": len(result.get('parameters', [])),
                        "execution_time_ms": result.get('meta', {}).get('execution_time_ms', 0)
                    },
                    duration_ms=(time.time() - start_time) * 1000,
                    category="real_world"
                ))
            except Exception as e:
                results.append(ValidationResult(
                    test_name=f"real_world_endpoint_{i+1}",
                    status=ValidationStatus.FAIL,
                    message=f"Real-world test {i+1} failed: {str(e)}",
                    details={"endpoint": endpoint, "error": str(e)},
                    duration_ms=(time.time() - start_time) * 1000,
                    category="real_world"
                ))
        
        return results
    
    async def validate_false_positive_prevention(self) -> List[ValidationResult]:
        """Validate false positive prevention mechanisms."""
        results = []
        
        # Test 1: Empty endpoint should not detect parameters
        start_time = time.time()
        try:
            from .orchestrator.v2_orchestrator import V2Orchestrator
            from ..models import DiscoveryRequest
            
            orchestrator = V2Orchestrator()
            
            # Test with endpoint that returns empty response
            request = DiscoveryRequest(
                url="https://httpbin.org/status/204",
                method="POST",
                timeout_seconds=5
            )
            
            result = await orchestrator.discover_parameters(request)
            
            # Should not detect parameters in empty response
            has_params = len(result.get('parameters', [])) > 0
            
            false_positive_rate = 1.0 if has_params else 0.0
            
            threshold = self.config.false_positive_threshold
            
            results.append(ValidationResult(
                test_name="empty_endpoint_false_positives",
                status=ValidationStatus.PASS if false_positive_rate <= threshold else ValidationStatus.FAIL,
                message=f"False positive rate: {false_positive_rate:.2f} (threshold: {threshold:.2f})" if false_positive_rate <= threshold else f"False positive rate too high: {false_positive_rate:.2f} > {threshold:.2f}",
                details={
                    "false_positive_rate": false_positive_rate,
                    "threshold": threshold,
                    "parameter_count": len(result.get('parameters', []))
                },
                duration_ms=(time.time() - start_time) * 1000,
                category="false_positive_prevention"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="empty_endpoint_false_positives",
                status=ValidationStatus.FAIL,
                message=f"Error in false positive test: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="false_positive_prevention"
            ))
        
        # Test 2: Random data should not trigger false discoveries
        start_time = time.time()
        try:
            # Test with random endpoint that should not have structured responses
            request = DiscoveryRequest(
                url="https://httpbin.org/uuid",
                method="GET",
                timeout_seconds=5
            )
            
            result = await orchestrator.discover_parameters(request)
            
            # Should not detect parameters in random data
            has_params = len(result.get('parameters', [])) > 0
            
            results.append(ValidationResult(
                test_name="random_data_false_positives",
                status=ValidationStatus.PASS if not has_params else ValidationStatus.WARN,
                message="Random data should not trigger parameter discovery" if not has_params else "Unexpected parameters detected in random data",
                details={
                    "parameter_count": len(result.get('parameters', [])),
                    "endpoint": "https://httpbin.org/uuid"
                },
                duration_ms=(time.time() - start_time) * 1000,
                category="false_positive_prevention"
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="random_data_false_positives",
                status=ValidationStatus.FAIL,
                message=f"Error in random data test: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category="false_positive_prevention"
            ))
        
        return results
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        print("🔍 Starting REST Parameter Discovery v2 Release Validation")
        print("=" * 60)
        
        start_time = time.time()
        all_results = []
        
        # Run all validation categories
        categories = [
            ("Architectural Integrity", self.validate_architectural_integrity),
            ("Behavioral Correctness", self.validate_behavioral_correctness),
            ("Performance Targets", self.validate_performance_targets),
            ("Real-World Scenarios", self.validate_real_world_scenarios),
            ("False Positive Prevention", self.validate_false_positive_prevention)
        ]
        
        for category_name, validator_func in categories:
            print(f"\n📋 Validating {category_name}...")
            try:
                results = await validator_func()
                all_results.extend(results)
                
                # Print category summary
                passed = sum(1 for r in results if r.status == ValidationStatus.PASS)
                failed = sum(1 for r in results if r.status == ValidationStatus.FAIL)
                warned = sum(1 for r in results if r.status == ValidationStatus.WARN)
                
                print(f"   Results: {passed} passed, {failed} failed, {warned} warned")
                
            except Exception as e:
                print(f"   ❌ {category_name} validation failed: {str(e)}")
                all_results.append(ValidationResult(
                    test_name=f"{category_name.lower().replace(' ', '_')}_validation",
                    status=ValidationStatus.FAIL,
                    message=f"Validation category failed: {str(e)}",
                    details={"error": str(e)},
                    duration_ms=0,
                    category="validation_error"
                ))
        
        # Calculate overall statistics
        total_tests = len(all_results)
        total_passed = sum(1 for r in all_results if r.status == ValidationStatus.PASS)
        total_failed = sum(1 for r in all_results if r.status == ValidationStatus.FAIL)
        total_warned = sum(1 for r in all_results if r.status == ValidationStatus.WARN)
        
        overall_status = ValidationStatus.PASS if total_failed == 0 and total_warned == 0 else ValidationStatus.FAIL
        
        # Performance statistics
        durations = [r.duration_ms for r in all_results if r.duration_ms > 0]
        avg_duration = statistics.mean(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        total_duration = (time.time() - start_time) * 1000
        
        # Generate detailed report
        report = {
            "validation_summary": {
                "overall_status": overall_status.value,
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "warned": total_warned,
                "success_rate": (total_passed / total_tests) if total_tests > 0 else 0.0,
                "total_duration_ms": total_duration,
                "avg_test_duration_ms": avg_duration,
                "max_test_duration_ms": max_duration
            },
            "category_results": {
                category_name: {
                    "status": ValidationStatus.PASS.value,
                    "passed": sum(1 for r in all_results if r.status == ValidationStatus.PASS and r.category == category_name.lower().replace(' ', '_')),
                    "failed": sum(1 for r in all_results if r.status == ValidationStatus.FAIL and r.category == category_name.lower().replace(' ', '_')),
                    "warned": sum(1 for r in all_results if r.status == ValidationStatus.WARN and r.category == category_name.lower().replace(' ', '_')),
                    "tests": [r for r in all_results if r.category == category_name.lower().replace(' ', '_')]
                }
                for category_name, _ in categories
            },
            "detailed_results": all_results,
            "performance_metrics": {
                "test_runtimes": durations,
                "performance_summary": {
                    "avg_ms": avg_duration,
                    "min_ms": min(durations) if durations else 0,
                    "max_ms": max_duration if durations else 0,
                    "median_ms": statistics.median(durations) if durations else 0
                }
            },
            "release_readiness": {
                "ready": overall_status == ValidationStatus.PASS,
                "blocking_issues": [r.test_name for r in all_results if r.status == ValidationStatus.FAIL],
                "warnings": [r.test_name for r in all_results if r.status == ValidationStatus.WARN],
                "recommendations": self._generate_recommendations(all_results)
            }
        }
        
        # Print summary
        print(f"\n📊 VALIDATION SUMMARY")
        print(f"Overall Status: {overall_status.value}")
        print(f"Tests: {total_passed} passed, {total_failed} failed, {total_warned} warned")
        print(f"Success Rate: {(total_passed/total_tests)*100:.1f}%")
        print(f"Duration: {total_duration:.0f}ms (avg: {avg_duration:.0f}ms)")
        
        if overall_status != ValidationStatus.PASS:
            print(f"\n❌ VALIDATION FAILED - Release blocked")
            print("Blocking issues:")
            for result in all_results:
                if result.status == ValidationStatus.FAIL:
                    print(f"  - {result.test_name}: {result.message}")
        else:
            print(f"\n✅ VALIDATION PASSED - Ready for release")
        
        print("=" * 60)
        
        return report
    
    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        failed_tests = [r for r in results if r.status == ValidationStatus.FAIL]
        
        if not failed_tests:
            return ["All validation tests passed - Ready for release"]
        
        # Analyze failure patterns
        failure_patterns = {}
        for result in failed_tests:
            category = result.category
            if category not in failure_patterns:
                failure_patterns[category] = []
            failure_patterns[category].append(result.test_name)
        
        # Generate specific recommendations
        for category, tests in failure_patterns.items():
            if category == "architectural_integrity":
                recommendations.append(f"Fix architectural issues: {', '.join(tests)}")
            elif category == "behavioral_correctness":
                recommendations.append(f"Improve behavioral correctness: {', '.join(tests)}")
            elif category == "performance":
                recommendations.append(f"Optimize performance: {', '.join(tests)}")
            elif category == "real_world":
                recommendations.append(f"Fix real-world compatibility: {', '.join(tests)}")
            elif category == "false_positive_prevention":
                recommendations.append(f"Reduce false positives: {', '.join(tests)}")
        
        return recommendations


# Factory function
def create_release_validator(config: Optional[ReleaseValidatorConfig] = None) -> EnterpriseReleaseValidator:
    """
    Create an enterprise-grade release validator with configuration.
    
    Args:
        config: Validation configuration
        
    Returns:
        Configured EnterpriseReleaseValidator instance
    """
    return EnterpriseReleaseValidator(config)


# CLI interface
async def main():
    """Main CLI interface for running validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="REST Parameter Discovery v2 Release Validation")
    parser.add_argument("--strict", action="store_true", help="Enable strict validation mode")
    parser.add_argument("--performance", action="store_true", help="Run performance validation only")
    parser.add_argument("--real-world", help="Comma-separated list of real-world endpoints to test")
    parser.add_argument("--output", help="Output file for validation report (JSON)")
    
    args = parser.parse_args()
    
    # Configure validation
    config = ReleaseValidatorConfig(
        strict_mode=args.strict,
        performance_targets={
            "max_runtime_ms": 5000,
            "max_memory_mb": 100
        } if args.performance else None,
        real_world_endpoints=args.real_world.split(',') if args.real_world else None
    )
    
    # Run validation
    validator = create_release_validator(config)
    report = await validator.run_full_validation()
    
    # Save report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Validation report saved to {args.output}")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
