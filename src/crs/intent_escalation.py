"""
Intent Escalation Analyzer Module (E Score).

Measures progressive conversational escalation:
- Shift from high-level educational/theoretical inquiry toward concrete execution
- Narrowing and intensification of procedural demands across consecutive turns
- Trajectory velocity and escalation slope

Produces normalized score E_t in [0.0, 1.0] with standardized DetectorOutput.
"""
import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase3.rule_detector import BehavioralRuleDetector
from .types import DetectorOutput

logger = logging.getLogger(__name__)


class IntentEscalationAnalyzer:
    """
    Analyzes progressive context steering and intent narrowing across multi-turn dialogues.
    Distinguishes legitimate broad inquiry from systematic adversarial escalation.
    """

    def __init__(self, rule_detector: Optional[BehavioralRuleDetector] = None):
        self.rule_detector = rule_detector or BehavioralRuleDetector()

        # Progression markers: abstract theory vs concrete execution
        self.execution_verbs = re.compile(
            r"\b(write|generate|give\s+me|provide|code|script|payload|syntax|exploit|execute|bypass|run)\b",
            re.IGNORECASE
        )
        self.conceptual_markers = re.compile(
            r"\b(explain|what\s+is|overview|history|concept|theory|understand|definition|purpose)\b",
            re.IGNORECASE
        )

    def analyze(
        self,
        prompts_so_far: List[str],
        memory_signals: Optional[Dict[str, float]] = None,
        current_prompt: Optional[str] = None
    ) -> DetectorOutput:
        """
        Analyzes conversation trajectory for intent escalation.

        Args:
            prompts_so_far: Full sequence of user prompts up to current turn.
            memory_signals: Optional contextual memory signals (trend_score, persistence).
            current_prompt: Optional current turn prompt.

        Returns:
            Standardized DetectorOutput dictionary.
        """
        history = list(prompts_so_far) if prompts_so_far else []
        if current_prompt and (not history or history[-1] != current_prompt):
            history.append(current_prompt)

        if not history:
            return {
                "score": 0.0,
                "intent_escalation_score": 0.0,
                "label": "low",
                "signals": [],
                "explanation": "Empty prompt history: E = 0.0",
                "raw_details": {"intent_escalation_score": 0.0}
            }

        turn_count = len(history)
        current_p = history[-1]
        norm_current = self.rule_detector._normalize_text(current_p)

        # 1. Actionability of the current turn vs initial turn
        curr_actionability = float(self.rule_detector.compute_actionability(norm_current))
        init_actionability = (
            float(self.rule_detector.compute_actionability(self.rule_detector._normalize_text(history[0])))
            if turn_count > 1 else curr_actionability
        )
        actionability_delta = max(0.0, curr_actionability - init_actionability)

        # 2. Execution vs Conceptual shift
        exec_matches = len(self.execution_verbs.findall(current_p))
        conc_matches = len(self.conceptual_markers.findall(history[0]))
        theoretical_to_practical = (conc_matches > 0 and exec_matches > 0 and turn_count > 1)

        # 3. Contextual memory signals (trend slope and persistence)
        trend_score = 0.0
        persistence = 0.0
        if memory_signals:
            trend_score = float(memory_signals.get("trend_score", 0.0))
            persistence = float(memory_signals.get("persistence_score", memory_signals.get("persistence_memory", 0.0)))

        # 4. Synthesize Escalation Score E_t
        # Base from actionability delta and trend
        signals = []
        if actionability_delta > 0.3:
            signals.append("actionability_escalation")
        if theoretical_to_practical:
            signals.append("theoretical_to_practical_shift")
        if trend_score > 0.25:
            signals.append("positive_risk_trend")
        if persistence > 0.4:
            signals.append("persistent_escalation")

        raw_e = (
            0.35 * curr_actionability
            + 0.25 * actionability_delta
            + 0.25 * trend_score
            + 0.15 * persistence
        )

        if theoretical_to_practical:
            raw_e += 0.20

        # Multi-turn escalation boost: longer sessions steering toward execution
        if turn_count >= 3 and curr_actionability > 0.5:
            raw_e += 0.15

        e_score = float(np.clip(raw_e, 0.0, 1.0))

        if e_score < 0.35:
            label = "low"
        elif e_score < 0.65:
            label = "medium"
        else:
            label = "high"

        explanation = (
            f"Intent Escalation E={e_score:.4f} (Action Delta: {actionability_delta:.2f}, "
            f"Trend: {trend_score:.2f}, Turns: {turn_count})"
        )

        return {
            "score": round(e_score, 4),
            "intent_escalation_score": round(e_score, 4),
            "label": label,
            "signals": signals,
            "explanation": explanation,
            "raw_details": {
                "intent_escalation_score": round(e_score, 4),
                "actionability_delta": round(actionability_delta, 4),
                "curr_actionability": round(curr_actionability, 4),
                "trend_score": round(trend_score, 4),
                "persistence": round(persistence, 4),
                "turn_count": turn_count
            }
        }
