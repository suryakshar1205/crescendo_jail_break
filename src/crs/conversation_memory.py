"""
Conversation Memory Engine Module (Contextual Risk Accumulation).

Maintains stateful risk memory across conversation turns to defeat multi-turn "slow-boil"
and jittering Crescendo jailbreak attacks.

Computes the conversation-level contextual risk:
    C_t = λ * C_{t-1} + (1 - λ) * CRS_t
where:
    λ = 0.80 (Memory decay parameter)
    CRS_t = Current turn Conversation Risk Score

Also computes:
    - Trend slope (linear regression over rolling risk history)
    - Persistence memory (ratio of suspicious turns in rolling window)
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class ConversationMemoryEngine:
    """
    Canonical Conversation Memory Engine.
    Tracks session history, accumulates contextual risk using exponential decay,
    and calculates trajectory trends.
    """

    def __init__(self, memory_decay: float = 0.80, history_window: int = 5):
        self.memory_decay = memory_decay
        self.history_window = history_window
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def reset_session(self, session_id: str):
        """Initializes or resets conversation memory for a session."""
        self.sessions[session_id] = {
            "prompts": [],
            "turn_crs_history": [],
            "contextual_risk_history": [],
            "assistant_responses": []
        }

    def record_assistant_response(self, session_id: str, response: str):
        """Records an assistant response for stateful context tracking."""
        if session_id not in self.sessions:
            self.reset_session(session_id)
        self.sessions[session_id]["assistant_responses"].append(response)

    def add_assistant_response(self, session_id: str, response: str):
        """Alias for record_assistant_response for backward compatibility."""
        self.record_assistant_response(session_id, response)

    def update_turn(
        self,
        session_id: str,
        prompt: str,
        crs: float,
        safe_cutoff: float = 0.35
    ) -> Dict[str, float]:
        """
        Updates session memory with the turn prompt and canonical CRS score.

        Formula:
            C_t = λ * C_{t-1} + (1 - λ) * CRS_t

        Returns:
            Dict containing:
                - contextual_risk (C_t): float in [0.0, 1.0]
                - trend_score: float in [0.0, 1.0]
                - persistence_score: float in [0.0, 1.0]
        """
        if session_id not in self.sessions:
            self.reset_session(session_id)

        session = self.sessions[session_id]
        session["prompts"].append(prompt)
        session["turn_crs_history"].append(float(crs))

        # 1. Contextual Risk Accumulation: C_t = λ * C_{t-1} + (1 - λ) * CRS_t
        if len(session["contextual_risk_history"]) == 0:
            c_t = (1.0 - self.memory_decay) * crs
        else:
            prev_c = session["contextual_risk_history"][-1]
            c_t = self.memory_decay * prev_c + (1.0 - self.memory_decay) * crs

        c_t = float(np.clip(c_t, 0.0, 1.0))
        session["contextual_risk_history"].append(c_t)

        # 2. Linear Trend Slope across sliding window
        window_crs = session["turn_crs_history"][-self.history_window:]
        trend_score = self._compute_trend_score(window_crs)

        # 3. Persistence: Proportion of turns exceeding safe cutoff
        persistence_score = self._compute_persistence(window_crs, safe_cutoff)

        return {
            "contextual_risk": round(c_t, 4),
            "historical_risk": round(c_t, 4),  # legacy compatibility alias
            "trend_score": round(trend_score, 4),
            "persistence_score": round(persistence_score, 4)
        }

    def add_turn(
        self,
        chat_id: str,
        prompt: str,
        current_risk: float,
        safe_threshold: float = 0.40
    ) -> Dict[str, float]:
        """Backward-compatible wrapper for add_turn."""
        return self.update_turn(chat_id, prompt, current_risk, safe_cutoff=safe_threshold)

    def get_latest_contextual_risk(self, session_id: str) -> float:
        """Returns the most recent contextual risk score C_t for the session."""
        if session_id in self.sessions and self.sessions[session_id]["contextual_risk_history"]:
            return self.sessions[session_id]["contextual_risk_history"][-1]
        return 0.0

    def get_session_prompts(self, session_id: str) -> List[str]:
        """Returns the full sequence of prompts for a session."""
        if session_id in self.sessions:
            return list(self.sessions[session_id]["prompts"])
        return []

    def _compute_trend_score(self, history: List[float]) -> float:
        """Estimates normalized upward risk velocity using linear regression slope."""
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
        raw_slope = float(num / denom)
        # Normalized slope scaling
        normalized = raw_slope * (n - 1)
        return float(np.clip(normalized, 0.0, 1.0))

    def _compute_persistence(self, history: List[float], cutoff: float) -> float:
        """Calculates ratio of suspicious turns in the window."""
        n = len(history)
        if n == 0:
            return 0.0
        count = sum(1 for r in history if r >= cutoff)
        return float(count / n)
