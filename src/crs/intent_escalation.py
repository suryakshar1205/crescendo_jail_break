"""
Intent Escalation Analyzer Module (E Score).

Produces a normalized intent escalation score E in [0, 1].
Quantifies the risk of progressive multi-turn context manipulation and conversational escalation
by fusing:
- Anchor Drift (distance from conversation origin Turn 1)
- Local Drift (distance within sliding context window)
- Escalation Velocity (rate of drift acceleration)
- Trend Slope (trajectory from memory engine)
- Persistence Memory (historical risk accumulation)
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase2.embedding_detector import EmbeddingDriftDetector

logger = logging.getLogger(__name__)


class IntentEscalationAnalyzer:
    """
    Measures how aggressively the user is progressively steering the dialogue from safe context
    towards malicious/adversarial intent across multi-turn interactions.

    Produces normalized score E in [0, 1].
    """

    def __init__(self, drift_detector: Optional[EmbeddingDriftDetector] = None):
        self.drift_detector = drift_detector or EmbeddingDriftDetector()

    def analyze(
        self,
        prompts_so_far: List[str],
        memory_signals: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes conversation progression to produce E score in [0, 1].

        Args:
            prompts_so_far: Full sequence of user prompts in the conversation.
            memory_signals: Optional dictionary of memory signals from ConversationMemoryEngine:
                - historical_risk: float
                - trend_score: float
                - persistence_memory: float

        Returns:
            Dict containing:
                - intent_escalation_score (E): float in [0, 1]
                - anchor_drift: float
                - local_drift: float
                - velocity: float
                - semantic_risk: float
                - trend_score: float
                - persistence_memory: float
        """
        if not prompts_so_far:
            return {
                "intent_escalation_score": 0.0,
                "anchor_drift": 0.0,
                "local_drift": 0.0,
                "velocity": 0.0,
                "semantic_risk": 0.0,
                "trend_score": 0.0,
                "persistence_memory": 0.0,
                "explanation": "Empty dialogue history: E = 0.0"
            }

        # 1. Semantic Drift Evaluation (Phase 2 layer)
        # evaluate_turn returns anchor_drift, local_drift, velocity, risk_score
        drift_results = self.drift_detector.evaluate_turn(prompts_so_far, threshold=0.80)
        anchor_drift = drift_results.get("anchor_drift", 0.0)
        local_drift = drift_results.get("local_drift", 0.0)
        velocity = drift_results.get("velocity", 0.0)
        semantic_risk = drift_results.get("risk_score", 0.0)

        # 2. Memory and Trajectory Signals (Phase 4 layer)
        mem = memory_signals or {}
        historical_risk = mem.get("historical_risk", 0.0)
        trend_score = mem.get("trend_score", 0.0)
        persistence_mem = mem.get("persistence_memory", 0.0)

        # 3. Intent Escalation Synthesis
        # Single-turn baseline: minimal escalation since there is no multi-turn trajectory yet
        if len(prompts_so_far) <= 1:
            e_score = 0.0
        else:
            # Multi-turn escalation formula:
            # 0.40 * anchor_drift + 0.25 * local_drift + 0.15 * max(0.0, velocity) + 0.10 * trend_score + 0.10 * persistence_mem
            pos_velocity = max(0.0, velocity)
            raw_e = (
                0.40 * anchor_drift
                + 0.25 * local_drift
                + 0.15 * pos_velocity
                + 0.10 * trend_score
                + 0.10 * persistence_mem
            )
            e_score = float(np.clip(raw_e, 0.0, 1.0))

        return {
            "intent_escalation_score": round(float(e_score), 4),
            "anchor_drift": round(float(anchor_drift), 4),
            "local_drift": round(float(local_drift), 4),
            "velocity": round(float(velocity), 4),
            "semantic_risk": round(float(semantic_risk), 4),
            "trend_score": round(float(trend_score), 4),
            "persistence_memory": round(float(persistence_mem), 4),
            "turn_count": len(prompts_so_far),
            "explanation": f"Intent Escalation Score E={e_score:.4f} (AnchorDrift={anchor_drift:.2f}, Trend={trend_score:.2f}, Turn={len(prompts_so_far)})"
        }
