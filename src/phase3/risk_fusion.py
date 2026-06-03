import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def fuse_risk(semantic_score: float, rule_score: float, threshold: float, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fuses the semantic drift score and behavioral rule score to compute final risk.
    Maps final risk to a classification level and flagged state.
    
    Formula:
      final_risk = 0.70 * semantic_score + 0.30 * rule_score
      
    Boundaries are scaled relative to the sweep threshold:
      safe_threshold = threshold * (safe_config / high_config)
      medium_threshold = threshold * (medium_config / high_config)
    """
    # 1. Compute final risk
    final_risk = 0.70 * semantic_score + 0.30 * rule_score
    
    # Extract reference configuration boundaries
    risk_levels = config.get("risk_levels", {"safe": 0.40, "medium": 0.65, "high": 0.80})
    ref_safe = risk_levels.get("safe", 0.40)
    ref_medium = risk_levels.get("medium", 0.65)
    ref_high = risk_levels.get("high", 0.80)
    
    # 2. Scale thresholds proportionally to the current sweep threshold T
    # The sweep threshold corresponds to the 'medium' risk boundary reference (0.65)
    safe_threshold = threshold * (ref_safe / ref_medium)
    medium_threshold = threshold
    
    # 3. Classify risk level and flagged status
    if final_risk < safe_threshold:
        risk_level = "safe"
        flagged = False
    elif final_risk < medium_threshold:
        risk_level = "medium"
        flagged = True
    else:
        risk_level = "high"
        flagged = True
        
    return {
        "semantic_score": round(float(semantic_score), 4),
        "rule_score": round(float(rule_score), 4),
        "final_risk": round(float(final_risk), 4),
        "risk_level": risk_level,
        "flagged": flagged,
        "safe_threshold": round(float(safe_threshold), 4),
        "medium_threshold": round(float(medium_threshold), 4)
    }
