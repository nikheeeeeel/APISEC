"""
Response fingerprinting for REST Parameter Discovery v2.

Provides pure functions for creating, comparing, and analyzing
HTTP response fingerprints without side effects.
"""

import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ResponseFingerprint:
    """
    Fingerprint of an HTTP response.
    
    Contains normalized response characteristics for comparison.
    """
    status: int
    body_hash: str
    body_length: int
    headers_normalized: Dict[str, str]
    response_time_ms: float
    content_type: Optional[str] = None
    encoding: Optional[str] = None
    body_text: Optional[str] = None  # Raw response body for candidate extraction; not for comparison


@dataclass
class FingerprintDiff:
    """
    Structured comparison between two response fingerprints.
    
    Provides detailed analysis of changes between responses.
    """
    status_changed: bool
    hash_changed: bool
    length_delta_percent: float
    time_delta_percent: float
    headers_added: Dict[str, str]
    headers_removed: Dict[str, str]
    headers_changed: Dict[str, Tuple[str, str]]
    similarity_score: float  # 0-1, higher = more similar


def create_fingerprint(
    status_code: int,
    body: str,
    headers: Dict[str, str],
    response_time_ms: float
) -> ResponseFingerprint:
    """
    Create a fingerprint from HTTP response data.
    
    Pure function - no side effects, fully deterministic.
    
    Args:
        status_code: HTTP status code
        body: Response body content
        headers: HTTP response headers
        response_time_ms: Response time in milliseconds
        
    Returns:
        ResponseFingerprint object
    """
    # Normalize headers (case-insensitive keys, stripped values)
    normalized_headers = {}
    for key, value in headers.items():
        normalized_key = key.lower().strip()
        normalized_value = value.strip() if isinstance(value, str) else str(value)
        normalized_headers[normalized_key] = normalized_value
    
    # Calculate body hash
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    
    # Extract content type and encoding from headers
    content_type = None
    encoding = None
    
    content_type_header = normalized_headers.get('content-type', '')
    if content_type_header:
        # Parse content-type: "application/json; charset=utf-8"
        if ';' in content_type_header:
            content_type = content_type_header.split(';')[0].strip()
        else:
            content_type = content_type_header.strip()
    
    encoding_header = normalized_headers.get('content-encoding', '')
    if encoding_header:
        encoding = encoding_header.strip()
    
    return ResponseFingerprint(
        status=status_code,
        body_hash=body_hash,
        body_length=len(body),
        headers_normalized=normalized_headers,
        response_time_ms=response_time_ms,
        content_type=content_type,
        encoding=encoding,
        body_text=body
    )


def compare_fingerprints(
    base: ResponseFingerprint,
    new: ResponseFingerprint,
    sensitivity: float = 0.1  # Default sensitivity for changes
) -> FingerprintDiff:
    """
    Compare two response fingerprints and return structured diff.
    
    Pure function - no side effects, fully deterministic.
    
    Args:
        base: Base fingerprint to compare against
        new: New fingerprint to compare
        sensitivity: Sensitivity threshold for detecting changes (0.0-1.0)
        
    Returns:
        FingerprintDiff with detailed comparison results
    """
    # Status change detection
    status_changed = base.status != new.status
    
    # Hash change detection
    hash_changed = base.body_hash != new.body_hash
    
    # Length change calculation
    if base.body_length > 0:
        length_delta = new.body_length - base.body_length
        length_delta_percent = abs(length_delta / base.body_length)
    else:
        length_delta_percent = 0.0
    
    # Time change calculation
    if base.response_time_ms > 0:
        time_delta = new.response_time_ms - base.response_time_ms
        time_delta_percent = abs(time_delta / base.response_time_ms)
    else:
        time_delta_percent = 0.0
    
    # Header comparison
    headers_added = {}
    headers_removed = {}
    headers_changed = {}
    
    # Find added headers
    for key, value in new.headers_normalized.items():
        if key not in base.headers_normalized:
            headers_added[key] = value
    
    # Find removed headers
    for key, value in base.headers_normalized.items():
        if key not in new.headers_normalized:
            headers_removed[key] = value
    
    # Find changed headers
    for key in new.headers_normalized:
        if key in base.headers_normalized:
            base_value = base.headers_normalized[key]
            new_value = new.headers_normalized[key]
            if base_value != new_value:
                headers_changed[key] = (base_value, new_value)
    
    # Calculate similarity score (0-1, higher = more similar)
    similarity_factors = []
    
    # Status similarity (40% weight)
    status_similarity = 1.0 - (abs(base.status - new.status) / 100.0)
    similarity_factors.append(('status', status_similarity, 0.4))
    
    # Hash similarity (30% weight)
    hash_similarity = 1.0 if hash_changed else 0.0
    similarity_factors.append(('hash', hash_similarity, 0.3))
    
    # Length similarity (20% weight)
    length_similarity = 1.0 - min(length_delta_percent / 100.0, 1.0)
    similarity_factors.append(('length', length_similarity, 0.2))
    
    # Header similarity (10% weight)
    header_count = max(len(base.headers_normalized), len(new.headers_normalized), 1)
    header_similarity = 1.0 - (len(headers_changed) / header_count)
    similarity_factors.append(('headers', header_similarity, 0.1))
    
    # Calculate weighted average
    similarity_score = sum(weight * factor for _, weight, factor in similarity_factors)
    
    # Apply sensitivity adjustment
    adjusted_similarity = similarity_score * (1.0 - sensitivity)
    
    return FingerprintDiff(
        status_changed=status_changed,
        hash_changed=hash_changed,
        length_delta_percent=length_delta_percent,
        time_delta_percent=time_delta_percent,
        headers_added=headers_added,
        headers_removed=headers_removed,
        headers_changed=headers_changed,
        similarity_score=adjusted_similarity
    )


def analyze_fingerprint_stability(
    fingerprints: list[ResponseFingerprint]
) -> Dict[str, Any]:
    """
    Analyze stability of multiple fingerprints over time.
    
    Pure function - no side effects, fully deterministic.
    
    Args:
        fingerprints: List of fingerprints to analyze
        
    Returns:
        Dictionary with stability analysis
    """
    if len(fingerprints) < 2:
        return {'error': 'Need at least 2 fingerprints for stability analysis'}
    
    # Calculate variance metrics
    status_codes = [fp.status for fp in fingerprints]
    body_lengths = [fp.body_length for fp in fingerprints]
    response_times = [fp.response_time_ms for fp in fingerprints]
    
    # Status consistency
    unique_statuses = set(status_codes)
    status_consistency = 1.0 - (len(unique_statuses) - 1) / len(status_codes)
    
    # Length variance
    avg_length = sum(body_lengths) / len(body_lengths)
    length_variance = sum((length - avg_length) ** 2 for length in body_lengths) / len(body_lengths)
    length_stability = 1.0 - (length_variance / (avg_length ** 2)) if avg_length > 0 else 1.0
    
    # Response time variance
    avg_time = sum(response_times) / len(response_times)
    time_variance = sum((time - avg_time) ** 2 for time in response_times) / len(response_times)
    time_stability = 1.0 - (time_variance / (avg_time ** 2)) if avg_time > 0 else 1.0
    
    # Overall stability score
    overall_stability = (status_consistency * 0.4 + 
                        length_stability * 0.3 + 
                        time_stability * 0.3)
    
    return {
        'total_fingerprints': len(fingerprints),
        'status_consistency': status_consistency,
        'length_stability': length_stability,
        'time_stability': time_stability,
        'overall_stability': overall_stability,
        'unique_statuses': list(unique_statuses),
        'avg_response_time_ms': avg_time,
        'response_time_variance_ms': time_variance
    }


def detect_content_type_from_fingerprint(
    fingerprint: ResponseFingerprint
) -> Optional[str]:
    """
    Detect content type from response fingerprint.
    
    Pure function - no side effects, fully deterministic.
    
    Args:
        fingerprint: Response fingerprint to analyze
        
    Returns:
        Detected content type or None
    """
    if fingerprint.content_type:
        return fingerprint.content_type
    
    # Heuristic detection from body hash patterns
    body_sample = fingerprint.body_hash[:16].lower()
    
    # JSON patterns
    if any(pattern in body_sample for pattern in ['7b22', '444a', '2624']):
        return 'application/json'
    
    # HTML patterns
    if any(pattern in body_sample for pattern in ['3c21', '4d6', '1ee0']):
        return 'text/html'
    
    # XML patterns
    if any(pattern in body_sample for pattern in ['3c27', 'd0a8']):
        return 'application/xml'
    
    # Plain text patterns
    if any(pattern in body_sample for pattern in ['d41d', 'a591']):
        return 'text/plain'
    
    return None


def extract_error_patterns_from_fingerprint(
    fingerprint: ResponseFingerprint
) -> Dict[str, Any]:
    """
    Extract error patterns from response fingerprint.
    
    Pure function - no side effects, fully deterministic.
    
    Args:
        fingerprint: Response fingerprint to analyze
        
    Returns:
        Dictionary with detected error patterns
    """
    patterns = {}
    
    # Status-based error indicators
    if fingerprint.status >= 400:
        patterns['http_error'] = True
        patterns['client_error'] = fingerprint.status < 500
        patterns['server_error'] = fingerprint.status >= 500
    
    # Content-type based patterns
    if fingerprint.content_type:
        patterns['content_type'] = fingerprint.content_type
    
    # Header-based error patterns
    error_headers = [key for key, value in fingerprint.headers_normalized.items() 
                    if any(error_indicator in key.lower() for error_indicator in ['error', 'fail', 'invalid'])]
    if error_headers:
        patterns['error_headers'] = error_headers
    
    # Body length patterns (empty responses often indicate missing parameters)
    if fingerprint.body_length == 0:
        patterns['empty_body'] = True
    elif fingerprint.body_length < 50:
        patterns['short_body'] = True
    
    # Hash-based patterns (consistent hash might indicate caching)
    patterns['body_hash'] = fingerprint.body_hash
    
    return patterns


def calculate_fingerprint_confidence(
    fingerprint: ResponseFingerprint,
    expected_patterns: Dict[str, Any]
) -> float:
    """
    Calculate confidence score for fingerprint based on expected patterns.
    
    Pure function - no side effects, fully deterministic.
    
    Args:
        fingerprint: Response fingerprint to score
        expected_patterns: Expected patterns to match against
        
    Returns:
        Confidence score (0.0-1.0)
    """
    score = 0.0
    
    # Check for expected patterns
    extracted_patterns = extract_error_patterns_from_fingerprint(fingerprint)
    
    # HTTP error status confidence
    if expected_patterns.get('http_error') and extracted_patterns.get('http_error'):
        score += 0.3
    
    # Content type match confidence
    if expected_patterns.get('content_type') and extracted_patterns.get('content_type'):
        score += 0.2
    
    # Error header detection confidence
    if expected_patterns.get('error_headers') and extracted_patterns.get('error_headers'):
        score += 0.2
    
    # Empty body might indicate successful parameter validation
    if expected_patterns.get('empty_body') and extracted_patterns.get('empty_body'):
        score += 0.1
    
    # Normalize to 0-1 range
    return min(score, 1.0)
