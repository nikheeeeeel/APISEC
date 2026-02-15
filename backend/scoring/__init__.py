"""
Scoring module for REST Parameter Discovery v2.

This module provides pure functions for confidence calculation,
evidence merging, and parameter ranking without side effects.
"""

from .confidence_calculator import (
    calculate_confidence,
    merge_confidence_scores,
    calculate_parameter_confidence,
    validate_confidence_threshold,
    rank_parameters_by_confidence,
    filter_parameters_by_confidence
)

__all__ = [
    'calculate_confidence',
    'merge_confidence_scores',
    'calculate_parameter_confidence',
    'validate_confidence_threshold',
    'rank_parameters_by_confidence',
    'filter_parameters_by_confidence'
]
