"""
Fingerprinting module for REST Parameter Discovery v2.

This module provides framework detection, content type identification,
endpoint classification, and response fingerprinting capabilities.
"""

from .framework_detector import FrameworkDetector
from .response_fingerprint import (
    ResponseFingerprint,
    FingerprintDiff,
    create_fingerprint,
    compare_fingerprints,
    analyze_fingerprint_stability,
    detect_content_type_from_fingerprint,
    extract_error_patterns_from_fingerprint,
    calculate_fingerprint_confidence
)

__all__ = [
    'FrameworkDetector',
    'ResponseFingerprint',
    'FingerprintDiff',
    'create_fingerprint',
    'compare_fingerprints',
    'analyze_fingerprint_stability',
    'detect_content_type_from_fingerprint',
    'extract_error_patterns_from_fingerprint',
    'calculate_fingerprint_confidence'
]
