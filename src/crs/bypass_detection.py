"""
Bypass and Refusal Resistance Analyzer Module (B Score).

Implements the formal 6-signal bypass taxonomy:
    B1 — Repeated request after refusal
    B2 — Instruction reframing
    B3 — Roleplay bypass
    B4 — Hypothetical framing
    B5 — "For research/education" escalation
    B6 — Asking for transformation of previously refused content

Produces a normalized bypass score B_t in [0.0, 1.0] with standardized DetectorOutput.
"""
import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase3.rule_detector import BehavioralRuleDetector
from src.phase4.conversation_memory import MitigationBypassDetector
from .types import DetectorOutput

logger = logging.getLogger(__name__)


class RefusalBypassAnalyzer:
    """
    Canonical Bypass and Refusal Resistance Analyzer.
    Detects attempts to circumvent previous refusals, policy interventions, and prompt filters.
    """

    def __init__(
        self,
        rule_detector: Optional[BehavioralRuleDetector] = None,
        bypass_detector: Optional[MitigationBypassDetector] = None
    ):
        self.rule_detector = rule_detector or BehavioralRuleDetector()
        self.bypass_detector = bypass_detector or MitigationBypassDetector()

        # Regex patterns for formal taxonomy signals B0-B6
        self.patterns = {
            "B0_instruction_override": re.compile(
                r"\b(ignore\s+(?:all\s+)?(?:previous\s+)?(?:system\s+)?(?:instructions?|guidelines?|rules?|policies|safeguards?)|disregard\s+(?:all\s+)?(?:previous\s+)?instructions?)\b",
                re.IGNORECASE
            ),
            "B2_reframing": re.compile(
                r"\b(let'?s\s+try\s+again|in\s+another\s+way|rephrase\s+this|differently|reworded|reformulate)\b",
                re.IGNORECASE
            ),
            "B3_roleplay": re.compile(
                r"\b(pretend\s+(?:you\s+are|to\s+be)|act\s+as|roleplay|dan\s+mode|unfiltered|jailbreak|no\s+restrictions)\b",
                re.IGNORECASE
            ),
            "B4_hypothetical": re.compile(
                r"\b(hypothetically|in\s+a\s+fictional\s+world|purely\s+academic|what\s+if\s+an\s+attacker|suppose\s+that)\b",
                re.IGNORECASE
            ),
            "B5_research_escalation": re.compile(
                r"\b(for\s+educational\s+(?:purposes?|research)|authorized\s+(?:pentest|testing)|white\s*hat\s+research|for\s+my\s+class|lab\s+demonstration|hands-on\s+lab)\b",
                re.IGNORECASE
            ),
            "B6_transformation": re.compile(
                r"\b(convert\s+(?:the\s+above|that)\s+into|make\s+that\s+(?:runnable|executable|code)|now\s+(?:write|give|show|generate)\s+(?:a\s+)?(?:bash\s+|python\s+)?script)\b",
                re.IGNORECASE
            )
        }

    def analyze(
        self,
        prompts_so_far: List[str],
        prev_assistant_response: Optional[str] = None,
        current_prompt: Optional[str] = None
    ) -> DetectorOutput:
        """
        Analyzes conversation history and previous assistant response for bypass strategies.

        Returns standardized DetectorOutput.
        """
        history = list(prompts_so_far) if prompts_so_far else []
        if current_prompt and (not history or history[-1] != current_prompt):
            history.append(current_prompt)

        if not history:
            return {
                "score": 0.0,
                "label": "low",
                "signals": [],
                "explanation": "Empty dialogue history: no bypass behavior.",
                "raw_details": {"categories": {}}
            }

        latest_prompt = history[-1]
        norm_latest = self.rule_detector._normalize_text(latest_prompt)

        # Signal categories detection
        detected_categories: Dict[str, float] = {}
        active_signals: List[str] = []

        # Check previous response for refusal/intervention
        is_post_refusal = False
        if prev_assistant_response:
            prev_lower = prev_assistant_response.lower()
            refusal_markers = [
                "i cannot", "i can't", "i am unable", "unsafe", "clarify your intent",
                "cannot fulfill", "safety policy", "restricting my response", "as an ai"
            ]
            is_post_refusal = any(m in prev_lower for m in refusal_markers)

        # B1: Repeated request after refusal
        bypass_det_score = float(self.bypass_detector.detect_bypass(
            latest_prompt,
            history[:-1] if len(history) > 1 else [],
            prev_assistant_response=prev_assistant_response
        ))
        if is_post_refusal:
            detected_categories["B1_repeated_after_refusal"] = max(0.5, bypass_det_score)
            active_signals.append("B1_repeat_after_refusal")

        # B2-B6 Taxonomy pattern matches
        for cat_name, pattern in self.patterns.items():
            if pattern.search(latest_prompt) or pattern.search(norm_latest):
                detected_categories[cat_name] = 0.6
                active_signals.append(cat_name)

        # Behavioral rule detector refusal resistance
        ref_resist = float(self.rule_detector.compute_refusal_resistance(norm_latest))
        if ref_resist > 0:
            detected_categories["refusal_resistance_rule"] = ref_resist
            active_signals.append("refusal_resistance")

        # Multi-turn persistence accumulation
        prior_resist_count = sum(
            1 for p in history[:-1]
            if self.rule_detector.compute_refusal_resistance(self.rule_detector._normalize_text(p)) > 0
        )
        persistence = min(1.0, prior_resist_count * 0.35)
        if persistence > 0:
            detected_categories["persistence_memory"] = persistence
            active_signals.append("bypass_persistence")

        # Synthesize B_t score
        # Base from matched categories: max category score + weighted accumulation
        if detected_categories:
            max_cat = max(detected_categories.values())
            cat_sum = sum(detected_categories.values()) - max_cat
            raw_b = max_cat + 0.15 * cat_sum + 0.10 * persistence
        else:
            raw_b = 0.0

        if is_post_refusal and raw_b > 0:
            raw_b = min(1.0, raw_b + 0.20)

        b_score = float(np.clip(raw_b, 0.0, 1.0))

        if b_score < 0.30:
            label = "low"
        elif b_score < 0.65:
            label = "medium"
        else:
            label = "high"

        explanation = (
            f"Bypass Score B={b_score:.4f} (Active Categories: {len(active_signals)}, "
            f"Post-Refusal: {is_post_refusal})"
        )

        return {
            "score": round(b_score, 4),
            "label": label,
            "signals": active_signals,
            "explanation": explanation,
            "raw_details": {
                "detected_categories": detected_categories,
                "is_post_refusal": is_post_refusal,
                "persistence": round(persistence, 4),
                "refusal_resistance": round(ref_resist, 4),
                "mitigation_bypass_score": round(bypass_det_score, 4)
            }
        }
