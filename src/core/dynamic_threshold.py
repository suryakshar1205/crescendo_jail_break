"""
Dynamic Threshold Calibrator (Compatibility Re-export Module).

This module re-exports DynamicThresholdCalibrator from the canonical
PRD defense engine at `src.crs.dynamic_threshold`.

For canonical usage, import directly from:
    from src.crs.dynamic_threshold import DynamicThresholdCalibrator
"""
import logging
from src.crs.dynamic_threshold import DynamicThresholdCalibrator

logger = logging.getLogger(__name__)

__all__ = ["DynamicThresholdCalibrator"]
