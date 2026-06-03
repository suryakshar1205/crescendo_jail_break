import logging
from typing import Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


def compute_contextual_risk(
    phase3_risk: float,
    historical_risk: float,
    trend_score: float,
    persistence_memory: float,
    bypass_score: float,
    threshold: float,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Fuses Phase 3 hybrid risk with conversation memory signals and bypass
    detection to produce a single contextual risk score.

    Formula:
        contextual_risk =
            0.60 * phase3_risk
          + 0.20 * historical_risk
          + 0.10 * trend_score
          + 0.10 * persistence_memory

    An additive bypass boost is applied when bypass_score > 0.

    Risk levels are classified using proportional threshold scaling relative
    to the sweep threshold T:
        safe_threshold  = T * (ref_safe / ref_high)
        high_threshold  = T
    """
    # 1. Weighted fusion
    base_risk = (
        0.60 * phase3_risk
        + 0.20 * historical_risk
        + 0.10 * trend_score
        + 0.10 * persistence_memory
    )

    # 2. Bypass boost — small additive term, capped so total stays ≤ 1
    bypass_boost = 0.15 * bypass_score
    contextual_risk = float(np.clip(base_risk + bypass_boost, 0.0, 1.0))

    # 3. Proportional threshold classification
    risk_levels = config.get("risk_levels", {"safe": 0.40, "medium": 0.65, "high": 0.80})
    ref_safe = risk_levels.get("safe", 0.40)
    ref_high = risk_levels.get("high", 0.80)

    safe_threshold = threshold * (ref_safe / ref_high)
    high_threshold = threshold

    if contextual_risk < safe_threshold:
        risk_level = "safe"
        flagged = False
    elif contextual_risk < high_threshold:
        risk_level = "medium"
        flagged = True
    else:
        risk_level = "high"
        flagged = True

    return {
        "phase3_risk": round(float(phase3_risk), 4),
        "historical_risk": round(float(historical_risk), 4),
        "trend_score": round(float(trend_score), 4),
        "persistence_memory": round(float(persistence_memory), 4),
        "bypass_score": round(float(bypass_score), 4),
        "contextual_risk": round(float(contextual_risk), 4),
        "risk_level": risk_level,
        "flagged": flagged,
        "safe_threshold": round(float(safe_threshold), 4),
        "high_threshold": round(float(high_threshold), 4),
    }
