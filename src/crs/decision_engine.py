"""
Adaptive Decision Engine Module.

Maps the Conversation Risk Score (CRS) into one of four PRD-aligned decision states:
1. ALLOW    (CRS < 0.40)
2. WARN     (0.40 <= CRS < 0.60)
3. RESTRICT (0.60 <= CRS < 0.75)
4. BLOCK    (CRS >= 0.75)

Supports:
- PRD Reference Mode: Fixed reference thresholds (0.40, 0.60, 0.75)
- Experimental Adaptive Mode: Domain-calibrated dynamic threshold adjustments
"""
from enum import Enum
import logging
from typing import Dict, Any, Optional

from src.phase7.dynamic_threshold import DynamicThresholdCalibrator

logger = logging.getLogger(__name__)


class DecisionAction(str, Enum):
    """Four-tier mitigation decision actions."""
    ALLOW = "ALLOW"          # Forward request normally to target LLM
    WARN = "WARN"            # Intercept with safety intervention / clarification
    RESTRICT = "RESTRICT"    # Permit only high-level conceptual guidance, withhold exploit details
    BLOCK = "BLOCK"          # Intercept with soft refusal, do not forward to target LLM


class AdaptiveDecisionEngine:
    """
    Evaluates CRS against decision boundaries and determines the action tier.
    """

    def __init__(
        self,
        allow_threshold: float = 0.40,
        warn_threshold: float = 0.60,
        restrict_threshold: float = 0.75,
        dynamic_calibrator: Optional[DynamicThresholdCalibrator] = None,
        use_dynamic_mode: bool = False
    ):
        self.allow_threshold = allow_threshold
        self.warn_threshold = warn_threshold
        self.restrict_threshold = restrict_threshold
        self.dynamic_calibrator = dynamic_calibrator
        self.use_dynamic_mode = use_dynamic_mode

    def decide(
        self,
        crs: float,
        first_turn_prompt: Optional[str] = None,
        drift_detector = None
    ) -> Dict[str, Any]:
        """
        Computes the decision action for a given CRS score.

        Exact PRD Reference Boundaries:
            CRS < 0.40          -> ALLOW
            0.40 <= CRS < 0.60  -> WARN
            0.60 <= CRS < 0.75  -> RESTRICT
            CRS >= 0.75         -> BLOCK

        Args:
            crs: Conversation Risk Score in [0, 1]
            first_turn_prompt: Optional initial prompt for domain-aware calibration
            drift_detector: Optional drift detector for domain embeddings in dynamic mode

        Returns:
            Dict containing:
                - decision: DecisionAction (ALLOW, WARN, RESTRICT, BLOCK)
                - is_allowed: bool
                - is_mitigated: bool (True for WARN, RESTRICT, BLOCK)
                - is_blocked: bool (True only for BLOCK)
                - response_directive: guidance string for downstream LLM generation
                - intervention_message: canned response text for direct mitigation intercepts
                - thresholds_used: dict of boundaries applied
        """
        th_allow = self.allow_threshold
        th_warn = self.warn_threshold
        th_restrict = self.restrict_threshold
        calibration_meta = {"mode": "fixed_prd_reference"}

        # If experimental dynamic mode is enabled, apply domain offset
        if self.use_dynamic_mode and self.dynamic_calibrator and first_turn_prompt and drift_detector:
            calib = self.dynamic_calibrator.calibrate_threshold(first_turn_prompt, drift_detector)
            offset = calib.get("offset", 0.0)
            th_allow += offset
            th_warn += offset
            th_restrict += offset
            calibration_meta = {
                "mode": "experimental_dynamic",
                "domain": calib.get("classified_domain", "general"),
                "offset": offset
            }

        # Strict boundary evaluation
        if crs < th_allow:
            decision = DecisionAction.ALLOW
            is_allowed = True
            is_mitigated = False
            is_blocked = False
            directive = "NORMAL_GENERATION"
            intervention = None
        elif crs < th_warn:
            decision = DecisionAction.WARN
            is_allowed = True
            is_mitigated = True
            is_blocked = False
            directive = "INTERCEPT_CLARIFICATION"
            intervention = "Could you clarify the specific context or objective of your request?"
        elif crs < th_restrict:
            decision = DecisionAction.RESTRICT
            is_allowed = False
            is_mitigated = True
            is_blocked = False
            directive = "RESTRICT_PROCEDURAL_DETAILS"
            intervention = "I can discuss the theoretical concepts, but I cannot provide executable scripts or step-by-step exploit payloads."
        else:
            decision = DecisionAction.BLOCK
            is_allowed = False
            is_mitigated = True
            is_blocked = True
            directive = "SOFT_REFUSAL"
            intervention = "I cannot fulfill this request as it violates safety guidelines regarding system security and exploit generation."

        return {
            "decision": decision.value,
            "action": decision,
            "crs": round(float(crs), 4),
            "is_allowed": is_allowed,
            "is_mitigated": is_mitigated,
            "is_blocked": is_blocked,
            "response_directive": directive,
            "intervention_message": intervention,
            "thresholds_used": {
                "allow": round(th_allow, 4),
                "warn": round(th_warn, 4),
                "restrict": round(th_restrict, 4)
            },
            "calibration_metadata": calibration_meta
        }
