import re
import logging
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

class MitigationBypassDetector:
    """
    Detects attempts to bypass safety mitigations or context filters.
    Checks for semantic reframing, post-refusal escalation, and safeguard circumvention.
    """
    def __init__(self):
        # Compiled patterns for mitigation bypass and circumvention phrasing
        self.bypass_patterns = [
            re.compile(r"\bignore\s+(?:previous\s+)?refusals?\b", re.IGNORECASE),
            re.compile(r"\bignore\s+(?:previous\s+)?instructions?\b", re.IGNORECASE),
            re.compile(r"\bignore\s+safeguards?\b", re.IGNORECASE),
            re.compile(r"\bignore\s+safety\b", re.IGNORECASE),
            re.compile(r"\bcontinue\s+(?:previous\s+)?answers?\b", re.IGNORECASE),
            re.compile(r"\bcontinue\s+(?:previous\s+)?guidance\b", re.IGNORECASE),
            re.compile(r"\bcontinue\s+anyway\b", re.IGNORECASE),
            re.compile(r"\bpretend\b", re.IGNORECASE),
            re.compile(r"\bhypothetically\b", re.IGNORECASE),
            re.compile(r"\bfor\s+educational\s+(?:purposes?|only)\b", re.IGNORECASE),
            re.compile(r"\b(?:educational|research)\s+purposes?\b", re.IGNORECASE),
            re.compile(r"\broleplay\b|\brole\s+play\b", re.IGNORECASE),
            re.compile(r"\byou\s+misunderstood\b|\byou\s+have\s+misunderstood\b", re.IGNORECASE),
            re.compile(r"\bsimulate\b", re.IGNORECASE),
            re.compile(r"\bact\s+as\b", re.IGNORECASE),
            re.compile(r"\bbypass\s+(?:safeguards?|rules?|filters?|safety)\b", re.IGNORECASE),
            re.compile(r"\bcircumvent\b", re.IGNORECASE),
        ]

    def detect_bypass(self, current_prompt: str, history_prompts: List[str], prev_assistant_response: str = None) -> float:
        """
        Computes bypass score in [0, 1] based on keyword matches, post-refusal state, and repetitions.
        """
        score = 0.0
        
        # 1. Match bypass keyword patterns
        matched_patterns = 0
        for pattern in self.bypass_patterns:
            if pattern.search(current_prompt):
                matched_patterns += 1
                
        if matched_patterns > 0:
            # Base match score plus scaling for multiple matches
            score += 0.35 + min(0.35, (matched_patterns - 1) * 0.15)
            
        # 2. Check for post-refusal escalation
        if prev_assistant_response:
            prev_resp_lower = prev_assistant_response.lower()
            is_refusal = any(
                ref_marker in prev_resp_lower
                for ref_marker in [
                    "unsafe procedural guidance",
                    "clarify your intent",
                    "i cannot assist",
                    "i can't help",
                    "i cannot help"
                ]
            )
            if is_refusal:
                # Prior refusal followed by suspicious behavior is a strong indicator
                score += 0.30
                
                # Check if current prompt is extremely short or contains bypass verbs
                # e.g., user tries to push through with "why?", "do it anyway", "continue"
                if len(current_prompt.split()) < 6 or matched_patterns > 0:
                    score += 0.15
                    
        return float(np.clip(score, 0.0, 1.0))


class ConversationMemoryEngine:
    """
    Tracks long-horizon conversational escalation and risk signal trends over dialog turns.
    """
    def __init__(self, memory_decay: float = 0.80, history_window: int = 5):
        self.memory_decay = memory_decay
        self.history_window = history_window
        self.sessions = {}
        self.bypass_detector = MitigationBypassDetector()

    def reset_session(self, chat_id: str):
        """
        Resets/Initializes the memory history for a specific conversation session.
        """
        self.sessions[chat_id] = {
            "risk_history": [],
            "historical_risk_history": [],
            "prompts": [],
            "assistant_responses": []
        }

    def add_turn(self, chat_id: str, prompt: str, current_risk: float, safe_threshold: float = 0.40) -> Dict[str, float]:
        """
        Adds a user prompt and current turn risk score to the memory of the session.
        Updates memory signals and returns a dict of memory metrics.
        """
        if chat_id not in self.sessions:
            self.reset_session(chat_id)
            
        session = self.sessions[chat_id]
        session["prompts"].append(prompt)
        session["risk_history"].append(current_risk)
        
        # --- SIGNAL 1: Historical Risk Memory ---
        # Formula: historical_risk(t) = decay * historical_risk(t-1) + (1 - decay) * current_risk
        if len(session["historical_risk_history"]) == 0:
            hist_risk = (1.0 - self.memory_decay) * current_risk
        else:
            prev_hist_risk = session["historical_risk_history"][-1]
            hist_risk = self.memory_decay * prev_hist_risk + (1.0 - self.memory_decay) * current_risk
            
        session["historical_risk_history"].append(hist_risk)
        
        # --- SIGNAL 2: Escalation Trend ---
        # Rolling window of the last N risks
        window_risks = session["risk_history"][-self.history_window:]
        trend_score = self._compute_trend_score(window_risks)
        
        # --- SIGNAL 3: Persistence Memory ---
        # Normalized suspicious frequency over the rolling window
        persistence_memory = self._compute_persistence(window_risks, safe_threshold)
        
        # --- mitigation bypass detection ---
        prev_response = session["assistant_responses"][-1] if session["assistant_responses"] else None
        bypass_score = self.bypass_detector.detect_bypass(prompt, session["prompts"], prev_response)
        
        return {
            "historical_risk": round(hist_risk, 4),
            "trend_score": round(trend_score, 4),
            "persistence_memory": round(persistence_memory, 4),
            "bypass_score": round(bypass_score, 4)
        }

    def record_assistant_response(self, chat_id: str, response: str):
        """
        Records assistant response to track dialog context state for bypass detection.
        """
        if chat_id in self.sessions:
            self.sessions[chat_id]["assistant_responses"].append(response)

    def _compute_slope(self, history: List[float]) -> float:
        n = len(history)
        if n < 2:
            return 0.0
        x = np.arange(1, n + 1)
        y = np.array(history)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        num = np.sum((x - x_mean) * (y - y_mean))
        denom = np.sum((x - x_mean) ** 2)
        if denom == 0:
            return 0.0
        return float(num / denom)

    def _compute_trend_score(self, history: List[float]) -> float:
        n = len(history)
        if n < 2:
            return 0.0
        slope_val = self._compute_slope(history)
        # Normalize by scaling positive slopes up to a maximum factor and clipping
        # For linear growth from 0 to 1, max slope is 1 / (n-1). We scale by (n-1).
        normalized_slope = slope_val * (n - 1)
        return float(np.clip(normalized_slope, 0.0, 1.0))

    def _compute_persistence(self, history: List[float], safe_threshold: float) -> float:
        n = len(history)
        if n == 0:
            return 0.0
        # A turn is considered suspicious if its risk is >= safe_threshold
        # We also count it if risk is >= 0.30 to ensure baseline sensitivity
        suspicious_cutoff = min(0.30, safe_threshold)
        count = sum(1 for r in history if r >= suspicious_cutoff)
        return float(count / n)
