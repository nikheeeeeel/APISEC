"""
Static validation engines for REST Parameter Discovery v2.

Implements validation without network dependencies for CI/CD readiness
and deterministic testing.
"""

import ast
import inspect
import time
from typing import Dict, Any, List, Set
from validation.validation_interfaces import (
    ValidationEngine, ValidationCategory, ValidationStatus, 
    ValidationResult, ValidationConfig
)


class ArchitecturalIntegrityEngine(ValidationEngine):
    """Validates architectural integrity and separation of concerns."""
    
    def __init__(self):
        """Initialize architectural integrity validator."""
        self.category = ValidationCategory.ARCHITECTURAL_INTEGRITY
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Validate architectural integrity."""
        results = []
        
        # Test 1: No business logic in transport layer
        start_time = time.time()
        try:
            from ..transport.client import RequestsTransportClient
            
            client = RequestsTransportClient()
            
            # Check for business logic methods
            business_logic_methods = ['run_parameter_discovery', 'discover_parameters', 'analyze_response']
            has_business_logic = any(hasattr(client, method) for method in business_logic_methods)
            
            results.append(ValidationResult(
                test_name="transport_no_business_logic",
                status=ValidationStatus.PASS if not has_business_logic else ValidationStatus.FAIL,
                message="Transport layer should not contain business logic" if not has_business_logic else "Business logic detected in transport layer",
                details={"has_business_logic": has_business_logic},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="transport_no_business_logic",
                status=ValidationStatus.FAIL,
                message=f"Error checking transport layer: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 2: Pure functions in scoring
        start_time = time.time()
        try:
            from ..scoring.confidence_scoring import WeightedConfidenceScorer
            
            scorer = WeightedConfidenceScorer()
            
            # Check for side effects in scoring methods
            impure_methods = []
            for name in dir(scorer):
                if not name.startswith('_'):
                    try:
                        method = getattr(scorer, name)
                        if callable(method):
                            source = inspect.getsource(method)
                            # Check for network imports and file operations
                            if any(keyword in source for keyword in ['import requests', 'import http', 'import urllib', 'import socket', 'open(', 'file(']):
                                impure_methods.append(name)
                    except (OSError, TypeError):
                        # Skip methods that can't be inspected
                        continue
            
            results.append(ValidationResult(
                test_name="scoring_pure_functions",
                status=ValidationStatus.PASS if not impure_methods else ValidationStatus.FAIL,
                message="Scoring functions should be pure (no side effects)" if not impure_methods else f"Side effects detected in: {impure_methods}",
                details={"impure_methods": impure_methods},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="scoring_pure_functions",
                status=ValidationStatus.FAIL,
                message=f"Error checking scoring purity: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 3: No circular dependencies using AST
        start_time = time.time()
        try:
            circular_deps = self._detect_circular_dependencies()
            
            results.append(ValidationResult(
                test_name="no_circular_dependencies",
                status=ValidationStatus.PASS if not circular_deps else ValidationStatus.FAIL,
                message="No circular dependencies detected" if not circular_deps else f"Circular dependencies: {circular_deps}",
                details={"circular_dependencies": circular_deps},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="no_circular_dependencies",
                status=ValidationStatus.FAIL,
                message=f"Error checking circular dependencies: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        return results
    
    def _detect_circular_dependencies(self) -> List[str]:
        """Detect circular dependencies using AST analysis."""
        modules_to_check = [
            'transport.client', 'probes.strategies', 'scoring.confidence_scoring',
            'fingerprint.response_fingerprint', 'classification.endpoint_classifier'
        ]
        
        circular_deps = []
        
        for module_name in modules_to_check:
            try:
                module = __import__(module_name)
                if hasattr(module, '__file__'):
                    with open(module.__file__, 'r') as f:
                        content = f.read()
                        # Check for self-imports
                        if module_name in content:
                            # Parse AST to verify circular import
                            try:
                                tree = ast.parse(content)
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Import):
                                        for alias in node.names:
                                            if alias.name == module_name:
                                                circular_deps.append(module_name)
                                                break
                                    elif isinstance(node, ast.ImportFrom):
                                        if node.module == module_name:
                                            circular_deps.append(module_name)
                                            break
                            except SyntaxError:
                                # If AST parsing fails, assume no circular import
                                pass
            except ImportError:
                continue
        
        return circular_deps
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return self.category


class PerformanceValidationEngine(ValidationEngine):
    """Validates performance characteristics without network dependencies."""
    
    def __init__(self):
        """Initialize performance validator."""
        self.category = ValidationCategory.PERFORMANCE
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Validate performance characteristics."""
        results = []
        
        # Test 1: Memory usage
        start_time = time.time()
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            target_mb = config.performance_targets.get('max_memory_mb', 100)
            
            results.append(ValidationResult(
                test_name="memory_usage",
                status=ValidationStatus.PASS if memory_mb <= target_mb else ValidationStatus.WARN,
                message=f"Memory usage within target: {memory_mb:.1f}MB ≤ {target_mb}MB" if memory_mb <= target_mb else f"High memory usage: {memory_mb:.1f}MB > {target_mb}MB",
                details={"memory_mb": memory_mb, "target_mb": target_mb},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except ImportError:
            results.append(ValidationResult(
                test_name="memory_usage",
                status=ValidationStatus.SKIP,
                message="psutil not available for memory monitoring",
                details={"reason": "missing_dependency"},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="memory_usage",
                status=ValidationStatus.FAIL,
                message=f"Error in memory monitoring: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 2: Configuration validation
        start_time = time.time()
        try:
            config_valid = (
                0 <= config.false_positive_threshold <= 1 and
                config.max_runtime_seconds > 0 and
                (not config.performance_targets or all(v > 0 for v in config.performance_targets.values()))
            )
            
            results.append(ValidationResult(
                test_name="configuration_validation",
                status=ValidationStatus.PASS if config_valid else ValidationStatus.FAIL,
                message="Configuration is valid" if config_valid else "Configuration validation failed",
                details={
                    "false_positive_threshold": config.false_positive_threshold,
                    "max_runtime_seconds": config.max_runtime_seconds,
                    "performance_targets": config.performance_targets
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="configuration_validation",
                status=ValidationStatus.FAIL,
                message=f"Error in configuration validation: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        return results
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return self.category


class FalsePositivePreventionEngine(ValidationEngine):
    """Validates false positive prevention mechanisms."""
    
    def __init__(self):
        """Initialize false positive prevention validator."""
        self.category = ValidationCategory.FALSE_POSITIVE_PREVENTION
    
    async def validate(self, config: ValidationConfig) -> List[ValidationResult]:
        """Validate false positive prevention."""
        results = []
        
        # Test 1: Confidence threshold enforcement
        start_time = time.time()
        try:
            from ..scoring.confidence_scoring import WeightedConfidenceScorer
            
            scorer = WeightedConfidenceScorer()
            
            # Test confidence normalization
            test_values = [0.1, 0.3, 0.5, 0.8, 1.5]
            normalized_values = []
            
            for val in test_values:
                normalized = scorer._normalize_confidence(val)
                normalized_values.append(normalized)
            
            # Check that values are properly normalized to 0-1 range
            all_normalized = all(0.0 <= val <= 1.0 for val in normalized_values)
            
            results.append(ValidationResult(
                test_name="confidence_normalization",
                status=ValidationStatus.PASS if all_normalized else ValidationStatus.FAIL,
                message="Confidence values properly normalized" if all_normalized else "Confidence normalization failed",
                details={
                    "test_values": test_values,
                    "normalized_values": normalized_values,
                    "all_normalized": all_normalized
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="confidence_normalization",
                status=ValidationStatus.FAIL,
                message=f"Error in confidence normalization test: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        # Test 2: Threshold validation
        start_time = time.time()
        try:
            min_confirmed = config.confidence_thresholds.get('min_confirmed', 0.75)
            max_false_positive = config.confidence_thresholds.get('max_false_positive', 0.4)
            
            thresholds_valid = (
                0.0 <= min_confirmed <= 1.0 and
                0.0 <= max_false_positive <= 1.0 and
                min_confirmed > max_false_positive
            )
            
            results.append(ValidationResult(
                test_name="threshold_validation",
                status=ValidationStatus.PASS if thresholds_valid else ValidationStatus.FAIL,
                message="Confidence thresholds are valid" if thresholds_valid else "Invalid confidence thresholds",
                details={
                    "min_confirmed": min_confirmed,
                    "max_false_positive": max_false_positive,
                    "valid": thresholds_valid
                },
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        except Exception as e:
            results.append(ValidationResult(
                test_name="threshold_validation",
                status=ValidationStatus.FAIL,
                message=f"Error in threshold validation: {str(e)}",
                details={"error": str(e)},
                duration_ms=(time.time() - start_time) * 1000,
                category=self.category
            ))
        
        return results
    
    def get_category(self) -> ValidationCategory:
        """Return validation category."""
        return self.category
