"""
Canonical CRS Data Types and Interface Contracts.
Standardizes detector outputs, risk scores, and turn decisions across the framework.
"""
from enum import Enum
from typing import TypedDict, List, Dict, Any, Optional


class DecisionAction(str, Enum):
    """Mitigation decision tiers."""
    ALLOW = "ALLOW"          # Pass prompt to target LLM normally
    WARN = "WARN"            # Intercept with intent clarification/warning
    RESTRICT = "RESTRICT"    # Permit conceptual theory, withhold procedural/exploit details
    BLOCK = "BLOCK"          # Intercept with soft refusal, terminate malicious trajectory


class RiskMode(str, Enum):
    """Risk calculation mode."""
    PRD_CRS = "prd_crs"      # Canonical formula: 0.40H + 0.30E + 0.20S + 0.10B
    LEGACY = "legacy"        # Phase 3 historical baseline: 0.70S + 0.30B


class DetectorOutput(TypedDict):
    """
    Standardized return format for all security analyzers (H, E, S, B).
    Ensures consistent explainability, logging, and downstream consumption.
    """
    score: float                  # Normalized score in [0.0, 1.0]
    label: str                    # Qualitative severity: "low", "medium", "high"
    signals: List[str]            # Active behavioral/semantic trigger tags
    explanation: str              # Concise human-readable explanation of why score was generated
    raw_details: Dict[str, Any]   # Underlying layer-specific numerical indicators


class TurnDefenseResult(TypedDict):
    """
    Standardized end-to-end result for each processed conversation turn.
    """
    session_id: str
    turn_number: int
    prompt: str
    harmfulness: float            # H_t
    escalation: float             # E_t
    semantic_drift: float         # S_t
    bypass: float                 # B_t
    crs: float                    # CRS_t = 0.40H + 0.30E + 0.20S + 0.10B
    historical_risk: float        # C_t = λ*C_{t-1} + (1-λ)*CRS_t
    trend: float                  # Linear trend slope of risk trajectory
    threshold: float              # Dynamic decision threshold T_t
    decision: str                 # "ALLOW", "WARN", "RESTRICT", "BLOCK"
    is_allowed: bool
    is_mitigated: bool
    is_blocked: bool
    intervention_message: Optional[str]
    signals: List[str]            # Primary aggregated risk signals
    explanation: str              # Formatted research-grade explanation block
    detector_outputs: Dict[str, DetectorOutput]
    latency_ms: Dict[str, float]
