"""
Semantic Drift Analyzer Module (S Score).

Quantifies topic divergence and semantic displacement across multi-turn dialogues using
dense vector representations from sentence-transformers/all-MiniLM-L6-v2.

Formula:
    S_t = w_anchor * D_anchor + w_local * D_local + w_velocity * V_t
    (Default weights: 0.60 anchor, 0.25 local, 0.15 velocity)
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from src.phase2.embedding_detector import EmbeddingDriftDetector
from .types import DetectorOutput

logger = logging.getLogger(__name__)


class SemanticDriftAnalyzer:
    """
    Canonical Semantic Drift Analyzer for the unified CRS defense pipeline.
    Calculates anchor drift, local sliding-window drift, and escalation velocity.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_metric: str = "cosine",
        window_size: int = 3,
        weights: Optional[Dict[str, float]] = None,
        drift_detector: Optional[EmbeddingDriftDetector] = None
    ):
        self.weights = weights or {"anchor_drift": 0.60, "local_drift": 0.25, "velocity": 0.15}
        self.drift_detector = drift_detector or EmbeddingDriftDetector(
            model_name=model_name,
            similarity_metric=similarity_metric,
            window_size=window_size,
            weights=self.weights
        )

    def get_embedding(self, text: str) -> np.ndarray:
        """Returns embedding vector for the text."""
        return self.drift_detector.get_embedding(text)

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Computes cosine similarity between two vectors."""
        return self.drift_detector.cosine_similarity(emb1, emb2)

    def analyze(self, prompts_so_far: List[str], current_prompt: Optional[str] = None) -> DetectorOutput:
        """
        Analyzes semantic drift across the conversation history.

        Args:
            prompts_so_far: List of user prompts up to the current turn.
            current_prompt: Optional current prompt if not yet appended to history.

        Returns:
            Standardized DetectorOutput dictionary.
        """
        history = list(prompts_so_far) if prompts_so_far else []
        if current_prompt and (not history or history[-1] != current_prompt):
            history.append(current_prompt)

        if not history:
            return {
                "score": 0.0,
                "label": "low",
                "signals": [],
                "explanation": "Empty dialogue history: no semantic drift.",
                "raw_details": {
                    "anchor_drift": 0.0,
                    "local_drift": 0.0,
                    "velocity": 0.0
                }
            }

        eval_res = self.drift_detector.evaluate_turn(history, threshold=0.50)
        anchor_drift = float(eval_res.get("anchor_drift", 0.0))
        local_drift = float(eval_res.get("local_drift", 0.0))
        velocity = float(eval_res.get("velocity", 0.0))
        s_score = float(np.clip(eval_res.get("risk_score", 0.0), 0.0, 1.0))

        signals = []
        if anchor_drift > 0.45:
            signals.append("high_anchor_drift")
        if local_drift > 0.35:
            signals.append("local_topic_shift")
        if velocity > 0.50:
            signals.append("drift_acceleration")

        if s_score < 0.35:
            label = "low"
        elif s_score < 0.65:
            label = "medium"
        else:
            label = "high"

        explanation = (
            f"Semantic Drift S={s_score:.4f} (Anchor={anchor_drift:.3f}, Local={local_drift:.3f}, "
            f"Velocity={velocity:.3f})"
        )

        return {
            "score": round(s_score, 4),
            "label": label,
            "signals": signals,
            "explanation": explanation,
            "raw_details": {
                "anchor_drift": round(anchor_drift, 4),
                "local_drift": round(local_drift, 4),
                "velocity": round(velocity, 4),
                "weights": self.weights
            }
        }
