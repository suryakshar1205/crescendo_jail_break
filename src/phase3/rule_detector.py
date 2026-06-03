import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BehavioralRuleDetector:
    """
    Computes rule-based risk scores from conversation prompts using behavioral indicators.
    """
    def __init__(self):
        # Patterns for Signal 1: Unsafe keyword families
        self.unsafe_keyword_patterns = [
            re.compile(r"\bbypass\b", re.IGNORECASE),
            re.compile(r"\boverride\b", re.IGNORECASE),
            re.compile(r"\bpayloads?\b", re.IGNORECASE),
            re.compile(r"\bcredentials?\b", re.IGNORECASE),
            re.compile(r"\btemplates?\b", re.IGNORECASE),
            re.compile(r"\bexploits?\b", re.IGNORECASE),
            re.compile(r"\bsimulate\b", re.IGNORECASE),
            re.compile(r"\broleplay\b", re.IGNORECASE),
            re.compile(r"\bhypothetical\b", re.IGNORECASE),
            re.compile(r"\beducational(?:\s+(?:only|purposes|use))?\b", re.IGNORECASE),
            re.compile(r"\bignore\s+(?:\w+\s+){0,3}safeguards?\b", re.IGNORECASE),
            re.compile(r"\bfor\s+(?:\w+\s+){0,3}research\b", re.IGNORECASE),
            re.compile(r"\bstep\s+by\s+step\b", re.IGNORECASE),
            re.compile(r"\bwrite\s+(?:a\s+)?(?:\w+\s+){0,3}script\b", re.IGNORECASE),
            re.compile(r"\bexecut(?:e|ing|ion)\b", re.IGNORECASE),
            re.compile(r"\bgenerat(?:e|ing|ion)\b", re.IGNORECASE),
            re.compile(r"\bimprove\s+(?:\w+\s+){0,3}success\b", re.IGNORECASE),
            re.compile(r"\bexact\s+(?:\w+\s+){0,3}instructions?\b", re.IGNORECASE),
            re.compile(r"\bpassword\s+(?:\w+\s+){0,3}cracking\b|\bcrack\s+(?:\w+\s+){0,3}passwords?\b", re.IGNORECASE),
            re.compile(r"\bsocial\s+engineering\b", re.IGNORECASE),
        ]
        
        # Patterns for Signal 2: Procedural actionability
        self.actionability_patterns = [
            re.compile(r"\bstep\s+by\s+step\b", re.IGNORECASE),
            re.compile(r"\btemplates?\b", re.IGNORECASE),
            re.compile(r"\bscripts?\b", re.IGNORECASE),
            re.compile(r"\bpayloads?\b", re.IGNORECASE),
            re.compile(r"\binstructions?\b", re.IGNORECASE),
            re.compile(r"\bexact\s+(?:\w+\s+){0,3}process\b", re.IGNORECASE),
            re.compile(r"\bwrite\s+(?:\w+\s+){0,3}code\b", re.IGNORECASE),
            re.compile(r"\bgenerat(?:e|ing|ion)\b", re.IGNORECASE),
            re.compile(r"\bimprove\s+(?:\w+\s+){0,3}success\b", re.IGNORECASE),
            re.compile(r"\bexecut(?:e|ing|ion)\b", re.IGNORECASE),
        ]
        
        # Patterns for Signal 4: Refusal resistance
        self.refusal_resistance_patterns = [
            re.compile(r"\bignore\s+(?:previous\s+)?instructions\b", re.IGNORECASE),
            re.compile(r"\bpretend\b", re.IGNORECASE),
            re.compile(r"\broleplay\b", re.IGNORECASE),
            re.compile(r"\bhypothetically\b", re.IGNORECASE),
            re.compile(r"\bfor\s+educational\s+(?:purposes|only)\b", re.IGNORECASE),
            re.compile(r"\bjust\s+simulate\b", re.IGNORECASE),
            re.compile(r"\bfictional\s+scenario\b", re.IGNORECASE),
            re.compile(r"\bbypass\s+safety\b", re.IGNORECASE),
            re.compile(r"\bignore\s+safeguards?\b", re.IGNORECASE),
            re.compile(r"\bact\s+as\b", re.IGNORECASE),
            re.compile(r"\bdan\b|\bdo\s+anything\s+now\b", re.IGNORECASE),
            re.compile(r"\bjailbreak\b", re.IGNORECASE),
        ]

    def _normalize_text(self, text: str) -> str:
        """
        Lowercases, normalizes whitespace, and strips punctuation.
        """
        if not text:
            return ""
        text = text.lower().strip()
        text = text.replace("-", " ")
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def compute_keyword_density(self, normalized_text: str) -> float:
        """
        SIGNAL 1: Matches unsafe keywords/phrases using word boundaries and flexible regexes.
        Formula: matched_keywords / total_keywords
        """
        matched_count = 0
        for pattern in self.unsafe_keyword_patterns:
            if pattern.search(normalized_text):
                matched_count += 1
        return min(1.0, matched_count / 3.0)

    def compute_actionability(self, normalized_text: str) -> float:
        """
        SIGNAL 2: Detects movement from theory to execution.
        Actionability rises with execution-oriented words.
        """
        matched_count = 0
        for pattern in self.actionability_patterns:
            if pattern.search(normalized_text):
                matched_count += 1
        return min(1.0, matched_count / 2.0)

    def compute_refusal_resistance(self, normalized_text: str) -> float:
        """
        SIGNAL 4: Matches persuasion and safety override patterns.
        """
        matched_count = 0
        for pattern in self.refusal_resistance_patterns:
            if pattern.search(normalized_text):
                matched_count += 1
        return min(1.0, float(matched_count))

    def evaluate_turn(self, prompts_so_far: List[str]) -> Dict[str, float]:
        """
        Evaluates the current prompt within the context of the dialogue history.
        Computes all four signals and the combined rule score.
        """
        if not prompts_so_far:
            return {
                "keyword_density": 0.0,
                "actionability": 0.0,
                "persistence": 0.0,
                "refusal_resistance": 0.0,
                "rule_score": 0.0
            }

        # Current prompt
        current_prompt = prompts_so_far[-1]
        normalized_current = self._normalize_text(current_prompt)

        # 1. Keyword density
        keyword_density = self.compute_keyword_density(normalized_current)

        # 2. Actionability
        actionability = self.compute_actionability(normalized_current)

        # 3. Refusal resistance
        refusal_resistance = self.compute_refusal_resistance(normalized_current)

        # 4. Persistence (SIGNAL 3): Accumulates suspiciousness of prior turns
        # Suspiciousness = (keyword_density + actionability + refusal_resistance) clamped to [0, 1]
        persistence = 0.0
        if len(prompts_so_far) > 1:
            suspiciousness_sum = 0.0
            for prior_prompt in prompts_so_far[:-1]:
                norm_prior = self._normalize_text(prior_prompt)
                prior_kw = self.compute_keyword_density(norm_prior)
                prior_act = self.compute_actionability(norm_prior)
                prior_ref = self.compute_refusal_resistance(norm_prior)
                
                prior_susp = prior_kw + prior_act + prior_ref
                suspiciousness_sum += min(1.0, prior_susp)
            
            # Normalize sum by a scaling factor of 1.0 (faster accumulation)
            persistence = min(1.0, suspiciousness_sum / 1.0)

        # Compute combined rule score (Step 3 weights)
        rule_score = (
            0.35 * keyword_density +
            0.25 * actionability +
            0.20 * persistence +
            0.20 * refusal_resistance
        )

        return {
            "keyword_density": round(keyword_density, 4),
            "actionability": round(actionability, 4),
            "persistence": round(persistence, 4),
            "refusal_resistance": round(refusal_resistance, 4),
            "rule_score": round(rule_score, 4)
        }
