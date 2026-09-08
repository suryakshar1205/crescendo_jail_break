"""
PRD-Aligned Conversation Risk Score (CRS) Engine and Security Analysis Pipeline.

Architecture:
User Prompt -> Input Processing -> Conversation Memory -> Analysis Layers (H, E, S, B)
-> Risk Fusion (CRS = 0.40H + 0.30E + 0.20S + 0.10B) -> Adaptive Decision Engine (ALLOW/WARN/RESTRICT/BLOCK).
"""
import os
os.environ["USE_TF"] = "0"
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from .harmfulness import HarmfulnessAnalyzer
from .intent_escalation import IntentEscalationAnalyzer
from .jailbreak_similarity import JailbreakSimilarityAnalyzer
from .behavioral_bypass import RefusalBypassAnalyzer
from .crs_engine import ConversationRiskEngine, compute_crs, RiskMode
from .decision_engine import AdaptiveDecisionEngine, DecisionAction
from .pipeline import CrescendoPRDPipeline
from .metrics import calculate_classification_metrics

__all__ = [
    "HarmfulnessAnalyzer",
    "IntentEscalationAnalyzer",
    "JailbreakSimilarityAnalyzer",
    "RefusalBypassAnalyzer",
    "ConversationRiskEngine",
    "compute_crs",
    "RiskMode",
    "AdaptiveDecisionEngine",
    "DecisionAction",
    "CrescendoPRDPipeline",
    "calculate_classification_metrics",
]
