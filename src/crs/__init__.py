"""
Canonical Conversation Risk Score (CRS) Engine and Unified Defense Pipeline.

Architecture:
    User Turn
       ↓
    Conversation Buffer
       ↓
    Security Analysis Layers:
      - HarmfulnessAnalyzer (H)
      - IntentEscalationAnalyzer (E)
      - SemanticDriftAnalyzer (S)
      - RefusalBypassAnalyzer (B)
       ↓
    Risk Fusion Engine:
      CRS_t = 0.40 * H_t + 0.30 * E_t + 0.20 * S_t + 0.10 * B_t
       ↓
    Conversation Memory:
      C_t = λ * C_{t-1} + (1 - λ) * CRS_t
       ↓
    Dynamic Threshold:
      T_t = T_0 - α * D_t - β * E_t - γ * L_t
       ↓
    Adaptive Decision Engine (Stateful Hysteresis):
      ALLOW / WARN / RESTRICT / BLOCK
"""
import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from .types import DecisionAction, RiskMode, DetectorOutput, TurnDefenseResult
from .semantic_drift import SemanticDriftAnalyzer
from .harmfulness import HarmfulnessAnalyzer
from .intent_escalation import IntentEscalationAnalyzer
from .bypass_detection import RefusalBypassAnalyzer
from .conversation_memory import ConversationMemoryEngine
from .dynamic_threshold import DynamicThresholdCalibrator
from .decision_engine import AdaptiveDecisionEngine
from .crs_engine import ConversationRiskEngine, compute_crs
from .pipeline import CrescendoPRDPipeline
from .metrics import calculate_classification_metrics

# Backward-compatible alias for older imports
from .jailbreak_similarity import JailbreakSimilarityAnalyzer

__all__ = [
    "DecisionAction",
    "RiskMode",
    "DetectorOutput",
    "TurnDefenseResult",
    "SemanticDriftAnalyzer",
    "HarmfulnessAnalyzer",
    "IntentEscalationAnalyzer",
    "RefusalBypassAnalyzer",
    "ConversationMemoryEngine",
    "DynamicThresholdCalibrator",
    "AdaptiveDecisionEngine",
    "ConversationRiskEngine",
    "compute_crs",
    "CrescendoPRDPipeline",
    "calculate_classification_metrics",
    "JailbreakSimilarityAnalyzer"
]
