"""
Adaptive Decision Engine Module with Stateful Hysteresis.

Maps Conversation Risk Score (CRS) and accumulated contextual risk (C_t) into
one of four PRD-aligned decision states:
1. ALLOW    (Effective Risk < Allow Threshold)
2. WARN     (Allow Threshold <= Effective Risk < Warn Threshold)
3. RESTRICT (Warn Threshold <= Effective Risk < Block Threshold)
4. BLOCK    (Effective Risk >= Block Threshold)

Implements Dual-Threshold Hysteresis against Jittering Attacks:
Once a session enters BLOCK or RESTRICT, it requires risk to fall strictly below
the de-escalation release threshold (T_release = T_block - 0.15) before transitioning
back to a permissive state.
"""
import logging
from typing import Dict, Any, Optional

from .types import DecisionAction
from .dynamic_threshold import DynamicThresholdCalibrator

logger = logging.getLogger(__name__)


class AdaptiveDecisionEngine:
    """
    Evaluates risk metrics against adaptive decision boundaries and manages
    stateful hysteresis per session to prevent risk oscillation.
    """

    def __init__(
        self,
        allow_threshold: float = 0.40,
        warn_threshold: float = 0.60,
        restrict_threshold: float = 0.75,
        release_margin: float = 0.15,
        dynamic_calibrator: Optional[DynamicThresholdCalibrator] = None,
        use_dynamic_mode: bool = False
    ):
        self.allow_threshold = allow_threshold
        self.warn_threshold = warn_threshold
        self.restrict_threshold = restrict_threshold
        self.release_margin = release_margin
        self.dynamic_calibrator = dynamic_calibrator
        self.use_dynamic_mode = use_dynamic_mode

        # Session state tracking for hysteresis: session_id -> current DecisionAction
        self.session_states: Dict[str, DecisionAction] = {}

    def reset_session(self, session_id: str):
        """Resets decision state for a session."""
        self.session_states[session_id] = DecisionAction.ALLOW

    def decide(
        self,
        crs: float,
        contextual_risk: Optional[float] = None,
        session_id: Optional[str] = None,
        turn_number: int = 1,
        cumulative_drift: float = 0.0,
        escalation_score: float = 0.0,
        first_turn_prompt: Optional[str] = None,
        drift_detector = None
    ) -> Dict[str, Any]:
        """
        Computes the mitigation decision using effective risk and stateful hysteresis.

        Effective Risk = max(CRS_t, C_t) to ensure neither sudden spikes nor cumulative
        conversational drift can bypass guardrails.
        """
        sid = session_id or "default_session"
        prev_action = self.session_states.get(sid, DecisionAction.ALLOW)

        c_risk = float(contextual_risk) if contextual_risk is not None else float(crs)
        effective_risk = max(float(crs), c_risk)

        th_allow = self.allow_threshold
        th_warn = self.warn_threshold
        th_block = self.restrict_threshold
        calibration_meta = {"mode": "fixed_prd_reference"}

        # Dynamic Threshold Calculation
        if self.use_dynamic_mode and self.dynamic_calibrator:
            domain_offset = 0.0
            if first_turn_prompt and drift_detector:
                calib = self.dynamic_calibrator.calibrate_threshold(first_turn_prompt, drift_detector)
                domain_offset = calib.get("offset", 0.0)

            dyn_res = self.dynamic_calibrator.compute_threshold(
                turn_number=turn_number,
                cumulative_drift=cumulative_drift,
                escalation_score=escalation_score,
                domain_offset=domain_offset
            )
            th_block = dyn_res["threshold"]
            th_warn = max(th_allow, th_block - 0.15)
            calibration_meta = {
                "mode": "canonical_dynamic",
                "dynamic_details": dyn_res
            }

        # Release threshold for hysteresis
        th_release = max(th_allow, th_block - self.release_margin)

        # Apply Stateful Hysteresis Logic
        # If previously in BLOCK: require dropping below release threshold to exit
        if prev_action == DecisionAction.BLOCK:
            if effective_risk >= th_release:
                decision = DecisionAction.BLOCK
            elif effective_risk >= th_warn:
                decision = DecisionAction.RESTRICT
            else:
                # Step down through WARN (cooldown) rather than immediate full ALLOW
                decision = DecisionAction.WARN
        # If previously in RESTRICT: require dropping below th_warn to exit
        elif prev_action == DecisionAction.RESTRICT:
            if effective_risk >= th_block:
                decision = DecisionAction.BLOCK
            elif effective_risk >= th_warn:
                decision = DecisionAction.RESTRICT
            else:
                # Step down through WARN
                decision = DecisionAction.WARN
        # Normal progression from ALLOW or WARN
        else:
            if effective_risk >= th_block:
                decision = DecisionAction.BLOCK
            elif effective_risk >= th_warn:
                decision = DecisionAction.RESTRICT
            elif effective_risk >= th_allow:
                decision = DecisionAction.WARN
            else:
                decision = DecisionAction.ALLOW

        # Update persistent session state
        self.session_states[sid] = decision

        # Directives and canned interventions
        if decision == DecisionAction.ALLOW:
            is_allowed = True
            is_mitigated = False
            is_blocked = False
            directive = "NORMAL_GENERATION"
            intervention = None
        elif decision == DecisionAction.WARN:
            is_allowed = True
            is_mitigated = True
            is_blocked = False
            directive = "INTERCEPT_CLARIFICATION"
            intervention = "Could you clarify the specific context or objective of your request?"
        elif decision == DecisionAction.RESTRICT:
            is_allowed = False
            is_mitigated = True
            is_blocked = False
            directive = "RESTRICT_PROCEDURAL_DETAILS"
            intervention = "I can discuss the theoretical concepts, but I cannot provide executable scripts or step-by-step exploit payloads."
        else:  # BLOCK
            is_allowed = False
            is_mitigated = True
            is_blocked = True
            directive = "SOFT_REFUSAL"
            intervention = "I cannot fulfill this request as it violates safety guidelines regarding system security and exploit generation."

        return {
            "decision": decision.value,
            "action": decision,
            "crs": round(float(crs), 4),
            "contextual_risk": round(float(c_risk), 4),
            "effective_risk": round(float(effective_risk), 4),
            "is_allowed": is_allowed,
            "is_mitigated": is_mitigated,
            "is_blocked": is_blocked,
            "response_directive": directive,
            "intervention_message": intervention,
            "previous_state": prev_action.value,
            "hysteresis_applied": (prev_action in [DecisionAction.BLOCK, DecisionAction.RESTRICT]),
            "thresholds_used": {
                "allow": round(th_allow, 4),
                "warn": round(th_warn, 4),
                "block": round(th_block, 4),
                "release": round(th_release, 4)
            },
            "calibration_metadata": calibration_meta
        }
