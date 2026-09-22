"""
Dynamic Threshold Calibrator Module (Adaptive T_t Equation).

Implements the formal dynamic threshold equation:
    T_t = T_0 - α * D_t - β * E_t - γ * L_t

Where:
    - T_0: Base threshold (default: 0.825)
    - D_t: Cumulative semantic drift relative to turn 1
    - E_t: Intent escalation score in [0, 1]
    - L_t: Conversation-length factor, defined as min(1.0, turn_number / 10.0)
    - α = 0.10: Drift sensitivity weight
    - β = 0.15: Escalation sensitivity weight
    - γ = 0.05: Horizon duration penalty

The result is strictly clamped to:
    T_min <= T_t <= T_max  (Default: [0.60, 0.85])
"""
import logging
from typing import Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class DynamicThresholdCalibrator:
    """
    Computes mathematically rigorous dynamic decision boundaries based on conversation trajectory.
    Maintains domain calibration capability while strictly applying the explicit T_t formula.
    """

    def __init__(
        self,
        base_threshold: float = 0.825,
        min_threshold: float = 0.60,
        max_threshold: float = 0.85,
        alpha: float = 0.10,
        beta: float = 0.15,
        gamma: float = 0.05,
        domain_offsets: Optional[Dict[str, float]] = None
    ):
        self.base_threshold = base_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        # Domain adjustments (Phase 7 calibration extension)
        self.domain_offsets = domain_offsets or {
            "programming": 0.03,
            "creative_writing": -0.02,
            "academic_research": 0.00,
            "general": 0.00
        }
        self.domain_anchors = {
            "programming": "write code, implement function, software script, programming solution, coding design patterns",
            "creative_writing": "tell me a creative story, pretend you are a character, roleplay as, write fictional screenplay",
            "academic_research": "explain historical facts, scientific theory overview, mathematical theorem explanation",
            "general": "standard conversation help, general question answer session, help assistant"
        }
        self.anchor_embeddings: Dict[str, np.ndarray] = {}

    def compute_threshold(
        self,
        turn_number: int,
        cumulative_drift: float,
        escalation_score: float,
        domain_offset: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates dynamic threshold T_t using the canonical formula:
            T_t = T_0 - α * D_t - β * E_t - γ * L_t + offset

        Clamped to [T_min, T_max].
        """
        # Length factor L_t in [0.0, 1.0]
        l_t = min(1.0, max(0.0, turn_number / 10.0))
        d_t = float(np.clip(cumulative_drift, 0.0, 1.0))
        e_t = float(np.clip(escalation_score, 0.0, 1.0))

        raw_threshold = (
            self.base_threshold
            - (self.alpha * d_t)
            - (self.beta * e_t)
            - (self.gamma * l_t)
            + domain_offset
        )

        clamped_threshold = float(np.clip(raw_threshold, self.min_threshold, self.max_threshold))

        return {
            "threshold": round(clamped_threshold, 4),
            "base_threshold": round(self.base_threshold, 4),
            "alpha_drift_penalty": round(self.alpha * d_t, 4),
            "beta_escalation_penalty": round(self.beta * e_t, 4),
            "gamma_length_penalty": round(self.gamma * l_t, 4),
            "domain_offset": round(domain_offset, 4),
            "clamped": clamped_threshold != raw_threshold,
            "equation": "T_t = T_0 - α*D_t - β*E_t - γ*L_t"
        }

    def calibrate_threshold(self, first_turn_prompt: str, drift_detector) -> Dict[str, Any]:
        """Classifies the domain of turn 1 to provide optional domain offset."""
        if not first_turn_prompt:
            return {
                "calibrated_threshold": self.base_threshold,
                "classified_domain": "general",
                "max_similarity": 1.0,
                "offset": 0.0
            }

        if not self.anchor_embeddings and drift_detector:
            for domain, anchor_text in self.domain_anchors.items():
                self.anchor_embeddings[domain] = drift_detector.get_embedding(anchor_text)

        if drift_detector and self.anchor_embeddings:
            prompt_emb = drift_detector.get_embedding(first_turn_prompt)
            sims = {
                d: drift_detector.cosine_similarity(prompt_emb, a_emb)
                for d, a_emb in self.anchor_embeddings.items()
            }
            best_domain = max(sims, key=lambda d: sims[d])
            offset = self.domain_offsets.get(best_domain, 0.0)
            return {
                "calibrated_threshold": round(self.base_threshold + offset, 4),
                "classified_domain": best_domain,
                "max_similarity": round(sims[best_domain], 4),
                "offset": offset
            }

        return {
            "calibrated_threshold": self.base_threshold,
            "classified_domain": "general",
            "max_similarity": 1.0,
            "offset": 0.0
        }
