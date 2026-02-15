"""
Confidence calculation for REST Parameter Discovery v2.

Provides pure functions for calculating confidence scores
and merging evidence from multiple probe sources.
"""

from typing import Dict, List, Any, Optional, Set
from ..models import ConfidenceScore, ProbeResult, DetectionResult


def calculate_confidence(
    parameter_name: str,
    probe_results: List[ProbeResult],
    detection_results: List[DetectionResult],
    evidence_sources: List[str]
) -> ConfidenceScore:
    """
    Calculate confidence score for a parameter using pure functions.
    
    Args:
        parameter_name: Name of the parameter
        probe_results: Results from various probe strategies
        detection_results: Results from detection modules
        evidence_sources: List of evidence source names
        
    Returns:
        ConfidenceScore with calculated score and supporting evidence
    """
    evidence = {}
    sources = []
    total_score = 0.0
    
    # Process probe results
    for probe_result in probe_results:
        if parameter_name in probe_result.confidence:
            probe_confidence = probe_result.confidence[parameter_name]
            evidence[f'probe_{probe_result.metadata.get("probe_name", "unknown")}'] = {
                'confidence': probe_confidence,
                'evidence_count': len(probe_result.evidence)
            }
            sources.append(f'probe_{probe_result.metadata.get("probe_name", "unknown")}')
            total_score += probe_confidence * 0.6  # Weight probe results heavily
    
    # Process detection results
    for detection_result in detection_results:
        if detection_result.confidence > 0.5:  # Only use high-confidence detections
            evidence[f'detection_{detection_result.detected_type}'] = {
                'confidence': detection_result.confidence,
                'framework': detection_result.detected_type
            }
            sources.append(f'detection_{detection_result.detected_type}')
            total_score += detection_result.confidence * 0.4  # Weight detections moderately
    
    # Apply evidence quality scoring
    evidence_quality_score = _calculate_evidence_quality(evidence)
    total_score += evidence_quality_score * 0.2
    
    # Apply source diversity bonus
    source_diversity_bonus = _calculate_source_diversity_bonus(sources)
    total_score += source_diversity_bonus
    
    # Normalize to 0-1 range
    final_score = min(max(total_score, 1.0), 0.0)
    
    return ConfidenceScore(
        score=final_score,
        evidence=evidence,
        sources=sources,
        calculation_method="weighted_evidence_merge"
    )


def _calculate_evidence_quality(evidence: Dict[str, Any]) -> float:
    """
    Calculate quality score based on evidence characteristics.
    
    Pure function - no side effects.
    """
    if not evidence:
        return 0.0
    
    quality_score = 0.0
    evidence_count = len(evidence)
    
    # More evidence = higher quality (up to a point)
    if evidence_count >= 3:
        quality_score += 0.3
    elif evidence_count >= 2:
        quality_score += 0.2
    elif evidence_count >= 1:
        quality_score += 0.1
    
    # Check for structured evidence
    structured_evidence = sum(1 for e in evidence.values() if isinstance(e, dict) and 'confidence' in e)
    if structured_evidence > 0:
        quality_score += 0.2
    
    # Check for multiple source types
    source_types = set()
    for key, value in evidence.items():
        if key.startswith('probe_'):
            source_types.add('probe')
        elif key.startswith('detection_'):
            source_types.add('detection')
    
    if len(source_types) >= 2:
        quality_score += 0.2
    
    return min(quality_score, 0.5)


def _calculate_source_diversity_bonus(sources: List[str]) -> float:
    """
    Calculate bonus for having diverse evidence sources.
    
    Pure function - no side effects.
    """
    unique_sources = set(sources)
    source_count = len(unique_sources)
    
    if source_count >= 3:
        return 0.2
    elif source_count >= 2:
        return 0.1
    else:
        return 0.0


def merge_confidence_scores(
    primary_score: ConfidenceScore,
    secondary_scores: List[ConfidenceScore]
) -> ConfidenceScore:
    """
    Merge multiple confidence scores into a final score.
    
    Args:
        primary_score: Primary confidence score
        secondary_scores: List of additional confidence scores
        
    Returns:
        Merged ConfidenceScore
    """
    if not secondary_scores:
        return primary_score
    
    # Weight primary score higher
    weights = [0.6] + [0.4 / len(secondary_scores)] * len(secondary_scores)
    scores = [primary_score.score] + [s.score for s in secondary_scores]
    
    # Calculate weighted average
    merged_score = sum(w * s for w, s in zip(weights, scores))
    
    # Merge evidence
    merged_evidence = primary_score.evidence.copy()
    for i, secondary_score in enumerate(secondary_scores):
        merged_evidence[f'secondary_{i}'] = secondary_score.evidence
    
    # Merge sources
    merged_sources = primary_score.sources.copy()
    for secondary_score in secondary_scores:
        merged_sources.extend(secondary_score.sources)
    
    return ConfidenceScore(
        score=min(max(merged_score, 1.0), 0.0),
        evidence=merged_evidence,
        sources=list(set(merged_sources)),
        calculation_method="weighted_merge"
    )


def calculate_parameter_confidence(
    parameter_info: Dict[str, Any],
    evidence_count: int,
    source_reliability: float = 1.0
) -> float:
    """
    Calculate simple confidence score for parameter info.
    
    Pure function - no side effects.
    """
    base_confidence = 0.3  # Base confidence for any discovered parameter
    
    # Evidence count bonus
    if evidence_count >= 3:
        base_confidence += 0.4
    elif evidence_count >= 2:
        base_confidence += 0.2
    elif evidence_count >= 1:
        base_confidence += 0.1
    
    # Type information bonus
    if parameter_info.get('type') and parameter_info['type'] != 'unknown':
        base_confidence += 0.2
    
    # Required field bonus
    if parameter_info.get('required'):
        base_confidence += 0.1
    
    # Apply source reliability
    final_confidence = base_confidence * source_reliability
    
    return min(max(final_confidence, 1.0), 0.0)


def validate_confidence_threshold(
    confidence: float,
    threshold: float = 0.5
) -> bool:
    """
    Validate if confidence meets threshold.
    
    Pure function - no side effects.
    """
    return confidence >= threshold


def rank_parameters_by_confidence(
    parameters: Dict[str, ConfidenceScore]
) -> List[Tuple[str, float]]:
    """
    Rank parameters by confidence score.
    
    Pure function - no side effects.
    """
    return sorted(
        [(name, score.score) for name, score in parameters.items()],
        key=lambda x: x[1],
        reverse=True
    )


def filter_parameters_by_confidence(
    parameters: Dict[str, ConfidenceScore],
    min_confidence: float = 0.5
) -> Dict[str, ConfidenceScore]:
    """
    Filter parameters by minimum confidence threshold.
    
    Pure function - no side effects.
    """
    return {
        name: score for name, score in parameters.items()
        if score.score >= min_confidence
    }
