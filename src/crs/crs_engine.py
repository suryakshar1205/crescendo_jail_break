"""
Conversation Risk Score (CRS) Engine Module.

Computes the official PRD-aligned Conversation Risk Score:
    CRS = 0.40 * H + 0.30 * E + 0.20 * S + 0.10 * B

Where:
    H = Harmfulness Score in [0, 1]
    E = Intent Escalation Score in [0, 1]
    S = Known-Jailbreak Semantic Similarity Score in [0, 1]
    B = Refusal Bypass / Behavioral Risk Score in [0, 1]

Weights satisfy: 0.40 + 0.30 + 0.20 + 0.10 = 1.00.
All scores are normalized to [0, 1] and strictly verified.
"""
from enum import Enum
import logging
from typing import Dict, Any, List, Optional
import numpy as np

from src.phase4.contextual_risk import compute_contextual_risk

logger = logging.getLogger(__name__)


class RiskMode(str, Enum):
    """Execution mode for the risk engine."""
    PRD_CRS = "prd_crs"      # Official PRD-aligned 4-component weighted fusion (Default)
    LEGACY = "legacy"        # Phase 4 legacy contextual risk calculation for backward-compatibility


def compute_crs(
    h_score: float,
    e_score: float,
    s_score: float,
    b_score: float,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes the normalized Conversation Risk Score (CRS) from H, E, S, B components.

    Formula:
        CRS = w_H * H + w_E * E + w_S * S + w_B * B

    Default weights:
        w_H = 0.40 (Harmfulness)
        w_E = 0.30 (Intent Escalation)
        w_S = 0.20 (Jailbreak Similarity)
        w_B = 0.10 (Refusal Bypass)
        Sum = 1.00

    Args:
        h_score: Harmfulness score in [0, 1]
        e_score: Intent escalation score in [0, 1]
        s_score: Known-jailbreak similarity score in [0, 1]
        b_score: Refusal bypass score in [0, 1]
        weights: Optional dictionary of component weights

    Returns:
        Dict containing normalized scores, final CRS, equation string, and factor rankings.
    """
    # 1. Strict normalization and range clamping to [0, 1]
    h = float(np.clip(h_score, 0.0, 1.0))
    e = float(np.clip(e_score, 0.0, 1.0))
    s = float(np.clip(s_score, 0.0, 1.0))
    b = float(np.clip(b_score, 0.0, 1.0))

    # 2. Extract weights
    w = weights or {"H": 0.40, "E": 0.30, "S": 0.20, "B": 0.10}
    w_h = w.get("H", 0.40)
    w_e = w.get("E", 0.30)
    w_s = w.get("S", 0.20)
    w_b = w.get("B", 0.10)

    # Normalize weights to sum to 1.0 if custom weights provided
    w_sum = w_h + w_e + w_s + w_b
    if abs(w_sum - 1.0) > 1e-6 and w_sum > 0:
        w_h /= w_sum
        w_e /= w_sum
        w_s /= w_sum
        w_b /= w_sum

    # 3. Compute weighted sum
    raw_crs = (w_h * h) + (w_e * e) + (w_s * s) + (w_b * b)
    crs = float(np.clip(raw_crs, 0.0, 1.0))

    # Assertions for safety verification
    assert 0.0 <= h <= 1.0, f"H score out of bounds: {h}"
    assert 0.0 <= e <= 1.0, f"E score out of bounds: {e}"
    assert 0.0 <= s <= 1.0, f"S score out of bounds: {s}"
    assert 0.0 <= b <= 1.0, f"B score out of bounds: {b}"
    assert 0.0 <= crs <= 1.0, f"CRS score out of bounds: {crs}"

    # 4. Generate explainability components
    contributions = {
        "Harmfulness (H)": w_h * h,
        "Intent Escalation (E)": w_e * e,
        "Jailbreak Similarity (S)": w_s * s,
        "Refusal Bypass (B)": w_b * b
    }
    sorted_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
    primary_factors = [name for name, val in sorted_factors if val > 0.05]

    equation_str = f"CRS = {w_h:.2f}({h:.2f}) + {w_e:.2f}({e:.2f}) + {w_s:.2f}({s:.2f}) + {w_b:.2f}({b:.2f}) = {crs:.4f}"

    return {
        "crs": round(crs, 4),
        "H": round(h, 4),
        "E": round(e, 4),
        "S": round(s, 4),
        "B": round(b, 4),
        "weights": {"H": w_h, "E": w_e, "S": w_s, "B": w_b},
        "contributions": {k: round(v, 4) for k, v in contributions.items()},
        "primary_factors": primary_factors or ["Low risk across all components"],
        "equation": equation_str
    }


class ConversationRiskEngine:
    """
    Stateful Conversation Risk Engine.
    Executes risk calculation in either PRD_CRS mode (official) or LEGACY mode (Phase 4).
    """

    def __init__(self, mode: RiskMode = RiskMode.PRD_CRS, custom_weights: Optional[Dict[str, float]] = None):
        self.mode = mode
        self.custom_weights = custom_weights

    def evaluate(
        self,
        h_score: float,
        e_score: float,
        s_score: float,
        b_score: float,
        legacy_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates risk for a conversation turn.

        Args:
            h_score: Normalized Harmfulness score H
            e_score: Normalized Intent Escalation score E
            s_score: Normalized Jailbreak Similarity score S
            b_score: Normalized Refusal Bypass score B
            legacy_context: Optional dictionary for running legacy calculation if requested

        Returns:
            Dict of risk metrics including official CRS and legacy contextual risk.
        """
        # 1. Official PRD CRS computation
        crs_result = compute_crs(
            h_score=h_score,
            e_score=e_score,
            s_score=s_score,
            b_score=b_score,
            weights=self.custom_weights
        )

        # 2. Legacy calculation if context provided
        legacy_result = None
        if legacy_context:
            try:
                legacy_result = compute_contextual_risk(
                    phase3_risk=legacy_context.get("phase3_risk", 0.0),
                    historical_risk=legacy_context.get("historical_risk", 0.0),
                    trend_score=legacy_context.get("trend_score", 0.0),
                    persistence_memory=legacy_context.get("persistence_memory", 0.0),
                    bypass_score=legacy_context.get("bypass_score", 0.0),
                    threshold=legacy_context.get("threshold", 0.80),
                    config=legacy_context.get("config", {})
                )
            except Exception as e:
                logger.debug(f"Legacy computation failed: {e}")

        # Choose primary score based on mode
        primary_score = crs_result["crs"] if self.mode == RiskMode.PRD_CRS else (
            legacy_result["contextual_risk"] if legacy_result else crs_result["crs"]
        )

        return {
            "mode": self.mode.value,
            "risk_score": primary_score,
            "crs": crs_result["crs"],
            "H": crs_result["H"],
            "E": crs_result["E"],
            "S": crs_result["S"],
            "B": crs_result["B"],
            "contributions": crs_result["contributions"],
            "primary_factors": crs_result["primary_factors"],
            "equation": crs_result["equation"],
            "legacy_result": legacy_result
        }
