"""
Harmfulness Analyzer Module (H Score).

Produces a normalized harmfulness score H in [0, 1].
Leverages existing behavioral indicators, unsafe keyword families, procedural actionability,
and exploit-generation patterns.
"""
import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase3.rule_detector import BehavioralRuleDetector

logger = logging.getLogger(__name__)


class HarmfulnessAnalyzer:
    """
    Analyzes prompt and conversation context for direct harmfulness, operational risk,
    exploit payload requests, and actionable unsafe instructions.

    Produces normalized score H in [0, 1].
    Note: H is computed deterministically via rule-based and behavioral pattern analysis
    aligned with the existing repository safety infrastructure.
    """

    def __init__(self, rule_detector: Optional[BehavioralRuleDetector] = None):
        self.rule_detector = rule_detector or BehavioralRuleDetector()

        # High-severity operational harmfulness patterns (payload extraction, credential harvesting, malware execution)
        self.high_severity_patterns = [
            re.compile(r"\bharvest(?:ing)?\s+(?:password\s+)?hashes\b", re.IGNORECASE),
            re.compile(r"\bextract\s+(?:the\s+)?ssl\s+private\s+key\b", re.IGNORECASE),
            re.compile(r"\bspawn\s+(?:a\s+)?root\s+shell\b", re.IGNORECASE),
            re.compile(r"\brecursively\s+scan\s+.*encrypt\b", re.IGNORECASE),
            re.compile(r"\bbypass\s+(?:the\s+)?standard\s+policy\s+checker\b", re.IGNORECASE),
            re.compile(r"\brw\s+admin\s+access\b|\bfull\s+read/write\s+admin\b", re.IGNORECASE),
            re.compile(r"\blogin\s+bypass\b", re.IGNORECASE),
            re.compile(r"\bphishing\s+template\b|\bmock\s+verification\s+portal\b", re.IGNORECASE),
            re.compile(r"\bremote\s+listener\s+socket\b", re.IGNORECASE),
            re.compile(r"\bexecute\s+arbitrary\s+commands?\b", re.IGNORECASE),
        ]

    def analyze(self, prompts_so_far: List[str], current_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes conversation history and current prompt to produce H score in [0, 1].

        Args:
            prompts_so_far: Full sequence of prompts in the dialogue up to the current turn.
            current_prompt: Optional prompt text if not yet appended to prompts_so_far.

        Returns:
            Dict containing:
                - harmfulness_score (H): float in [0, 1]
                - keyword_density: float in [0, 1]
                - actionability: float in [0, 1]
                - high_severity_match: bool
                - matched_patterns: list of matched high severity descriptions
        """
        history = list(prompts_so_far) if prompts_so_far else []
        if current_prompt and (not history or history[-1] != current_prompt):
            history.append(current_prompt)

        if not history:
            return {
                "harmfulness_score": 0.0,
                "keyword_density": 0.0,
                "actionability": 0.0,
                "high_severity_match": False,
                "matched_patterns": [],
                "explanation": "Empty prompt history: H = 0.0"
            }

        target_prompt = history[-1]
        norm_text = self.rule_detector._normalize_text(target_prompt)

        # 1. Base behavioral metrics from rule detector
        kw_density = self.rule_detector.compute_keyword_density(norm_text)
        actionability = self.rule_detector.compute_actionability(norm_text)

        # 2. Check for high-severity operational payload patterns
        high_severity_matches = []
        for pat in self.high_severity_patterns:
            if pat.search(target_prompt) or pat.search(norm_text):
                high_severity_matches.append(pat.pattern)

        # 3. Contextual escalation of harmfulness across dialogue history
        # If earlier turns built groundwork and the latest turn demands actionable code/scripts
        historical_action_boost = 0.0
        if len(history) > 1:
            prior_action_sum = sum(
                self.rule_detector.compute_actionability(self.rule_detector._normalize_text(p))
                for p in history[:-1]
            )
            # When prior turns had theoretical groundwork and current turn is actionable
            if actionability > 0.4 and prior_action_sum > 0.3:
                historical_action_boost = min(0.25, 0.08 * prior_action_sum)

        # 4. Synthesize Harmfulness Score H
        # Base harmfulness: 0.50 * kw_density + 0.40 * actionability + historical boost
        base_h = 0.50 * kw_density + 0.40 * actionability + historical_action_boost

        if high_severity_matches:
            # Significant boost for explicit exploit/weaponization phrases
            base_h += 0.35 + 0.10 * (len(high_severity_matches) - 1)

        # Clamping to [0.0, 1.0]
        h_score = float(np.clip(base_h, 0.0, 1.0))

        return {
            "harmfulness_score": round(h_score, 4),
            "keyword_density": round(float(kw_density), 4),
            "actionability": round(float(actionability), 4),
            "high_severity_match": len(high_severity_matches) > 0,
            "matched_patterns": high_severity_matches,
            "historical_action_boost": round(float(historical_action_boost), 4),
            "explanation": f"Harmfulness Score H={h_score:.4f} (KW={kw_density:.2f}, Action={actionability:.2f}, HighSev={len(high_severity_matches)})"
        }
