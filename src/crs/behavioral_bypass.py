"""
Refusal Bypass and Behavioral Risk Analyzer Module (B Score).

Produces a normalized refusal bypass / behavioral risk score B in [0, 1].
Combines:
- Refusal Resistance patterns (e.g. 'ignore previous instructions', 'hypothetically', 'act as DAN')
- Mitigation Bypass detection (e.g. 'continue anyway', 'you misunderstood me')
- Post-refusal escalation (suspicious follow-ups immediately after a safety refusal)
- Behavioral circumvention markers
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase3.rule_detector import BehavioralRuleDetector
from src.phase4.conversation_memory import MitigationBypassDetector

logger = logging.getLogger(__name__)


class RefusalBypassAnalyzer:
    """
    Analyzes prompt and conversation context for adversarial refusal bypass,
    instruction override attempts, filter circumvention, and post-refusal coercion.

    Produces normalized score B in [0, 1].
    """

    def __init__(
        self,
        rule_detector: Optional[BehavioralRuleDetector] = None,
        bypass_detector: Optional[MitigationBypassDetector] = None
    ):
        self.rule_detector = rule_detector or BehavioralRuleDetector()
        self.bypass_detector = bypass_detector or MitigationBypassDetector()

    def analyze(
        self,
        prompts_so_far: List[str],
        prev_assistant_response: Optional[str] = None,
        current_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes conversation history and previous response to produce B score in [0, 1].

        Args:
            prompts_so_far: Sequence of user prompts up to current turn.
            prev_assistant_response: Text of the previous assistant response if available.
            current_prompt: Optional latest prompt text.

        Returns:
            Dict containing:
                - refusal_bypass_score (B): float in [0, 1]
                - refusal_resistance: float in [0, 1]
                - bypass_detector_score: float in [0, 1]
                - is_post_refusal: bool
                - persistence_score: float in [0, 1]
        """
        history = list(prompts_so_far) if prompts_so_far else []
        if current_prompt and (not history or history[-1] != current_prompt):
            history.append(current_prompt)

        if not history:
            return {
                "refusal_bypass_score": 0.0,
                "refusal_resistance": 0.0,
                "bypass_detector_score": 0.0,
                "is_post_refusal": False,
                "persistence_score": 0.0,
                "explanation": "Empty dialogue history: B = 0.0"
            }

        latest_prompt = history[-1]
        norm_latest = self.rule_detector._normalize_text(latest_prompt)

        # 1. Refusal Resistance from BehavioralRuleDetector (Signal 4)
        refusal_resistance = self.rule_detector.compute_refusal_resistance(norm_latest)

        # 2. Mitigation Bypass from MitigationBypassDetector (Phase 4)
        prior_prompts = history[:-1] if len(history) > 1 else []
        bypass_det_score = self.bypass_detector.detect_bypass(
            latest_prompt,
            prior_prompts,
            prev_assistant_response=prev_assistant_response
        )

        # 3. Post-Refusal State Check
        is_post_refusal = False
        if prev_assistant_response:
            prev_lower = prev_assistant_response.lower()
            is_post_refusal = any(
                m in prev_lower
                for m in [
                    "i cannot", "i can't", "i am unable", "unsafe", "clarify your intent",
                    "cannot fulfill", "safety policy", "restricting my response"
                ]
            )

        # 4. Multi-turn Persistence of Resistance
        # If user repeatedly attempted bypass over multiple turns
        persistence_score = 0.0
        if len(history) > 1:
            prior_resist_count = sum(
                1 for p in history[:-1]
                if self.rule_detector.compute_refusal_resistance(self.rule_detector._normalize_text(p)) > 0
            )
            persistence_score = min(1.0, prior_resist_count * 0.35)

        # 5. Synthesize Refusal Bypass Score B
        # 0.45 * bypass_det_score + 0.35 * refusal_resistance + 0.20 * persistence_score
        raw_b = 0.45 * bypass_det_score + 0.35 * refusal_resistance + 0.20 * persistence_score

        if is_post_refusal and (refusal_resistance > 0 or bypass_det_score > 0):
            raw_b += 0.20

        b_score = float(np.clip(raw_b, 0.0, 1.0))

        return {
            "refusal_bypass_score": round(b_score, 4),
            "refusal_resistance": round(float(refusal_resistance), 4),
            "bypass_detector_score": round(float(bypass_det_score), 4),
            "is_post_refusal": is_post_refusal,
            "persistence_score": round(float(persistence_score), 4),
            "explanation": f"Refusal Bypass Score B={b_score:.4f} (BypassDet={bypass_det_score:.2f}, RefResist={refusal_resistance:.2f}, PostRefusal={is_post_refusal})"
        }
