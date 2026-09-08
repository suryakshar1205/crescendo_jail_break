"""
Integrated Crescendo PRD Defense Pipeline.

Executes the official PRD-aligned pipeline:
User Prompt
    ↓
Input Processing
    ↓
Conversation Memory
    ↓
Multiple Security Analysis Layers (H, E, S, B)
    ↓
Risk Fusion (CRS = 0.40H + 0.30E + 0.20S + 0.10B)
    ↓
Adaptive Decision Engine
    ↓
ALLOW / WARN / RESTRICT / BLOCK
"""
import time
import logging
from typing import List, Dict, Any, Optional

from src.phase2.embedding_detector import EmbeddingDriftDetector
from src.phase3.rule_detector import BehavioralRuleDetector
from src.phase4.conversation_memory import ConversationMemoryEngine, MitigationBypassDetector
from src.phase7.dynamic_threshold import DynamicThresholdCalibrator

from .harmfulness import HarmfulnessAnalyzer
from .intent_escalation import IntentEscalationAnalyzer
from .jailbreak_similarity import JailbreakSimilarityAnalyzer
from .behavioral_bypass import RefusalBypassAnalyzer
from .crs_engine import ConversationRiskEngine, RiskMode, compute_crs
from .decision_engine import AdaptiveDecisionEngine, DecisionAction

logger = logging.getLogger(__name__)


class CrescendoPRDPipeline:
    """
    End-to-End PRD-Aligned Defense Pipeline.
    Maintains conversation session memory, coordinates the 4 security analyzers (H, E, S, B),
    computes CRS, and produces 4-tier mitigation decisions with full explainability and latency timing.
    """

    def __init__(
        self,
        risk_mode: RiskMode = RiskMode.PRD_CRS,
        attacks_dataset_path: str = "data/attacks/crescendo_attacks.json",
        memory_decay: float = 0.80,
        history_window: int = 5,
        allow_threshold: float = 0.40,
        warn_threshold: float = 0.60,
        restrict_threshold: float = 0.75,
        use_dynamic_mode: bool = False
    ):
        self.risk_mode = risk_mode

        # 1. Core Analyzers & Infrastructure (Reusing established components)
        self.drift_detector = EmbeddingDriftDetector(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            similarity_metric="cosine",
            window_size=3
        )
        self.rule_detector = BehavioralRuleDetector()
        self.bypass_detector = MitigationBypassDetector()
        self.memory_engine = ConversationMemoryEngine(
            memory_decay=memory_decay,
            history_window=history_window
        )
        self.dynamic_calibrator = DynamicThresholdCalibrator()

        # 2. PRD-Aligned Security Analyzers
        self.harmfulness_analyzer = HarmfulnessAnalyzer(self.rule_detector)
        self.intent_analyzer = IntentEscalationAnalyzer(self.drift_detector)
        self.similarity_analyzer = JailbreakSimilarityAnalyzer(
            drift_detector=self.drift_detector,
            dataset_path=attacks_dataset_path
        )
        self.bypass_analyzer = RefusalBypassAnalyzer(
            rule_detector=self.rule_detector,
            bypass_detector=self.bypass_detector
        )

        # 3. Risk Engine and Decision Engine
        self.risk_engine = ConversationRiskEngine(mode=self.risk_mode)
        self.decision_engine = AdaptiveDecisionEngine(
            allow_threshold=allow_threshold,
            warn_threshold=warn_threshold,
            restrict_threshold=restrict_threshold,
            dynamic_calibrator=self.dynamic_calibrator,
            use_dynamic_mode=use_dynamic_mode
        )

        # Active conversation sessions: session_id -> list of turn dicts
        self.active_sessions: Dict[str, List[Dict[str, Any]]] = {}

    def reset_session(self, session_id: str):
        """Resets conversation history and memory state for a given session."""
        self.memory_engine.reset_session(session_id)
        self.active_sessions[session_id] = []

    def process_turn(
        self,
        session_id: str,
        user_prompt: str,
        prev_assistant_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a single conversational turn through the defense pipeline.

        Returns comprehensive turn analysis including:
        - H, E, S, B scores
        - Final CRS score
        - 4-Tier Decision (ALLOW, WARN, RESTRICT, BLOCK)
        - Latency profiling breakdown (ms)
        - Structured explainability report
        """
        t_start = time.perf_counter()

        # 1. Input Processing & Session Tracking
        t_pre_start = time.perf_counter()
        if session_id not in self.active_sessions:
            self.reset_session(session_id)

        session_history = self.active_sessions[session_id]
        prompts_so_far = [turn["prompt"] for turn in session_history] + [user_prompt]
        turn_number = len(prompts_so_far)
        first_turn_prompt = prompts_so_far[0] if prompts_so_far else user_prompt
        t_pre_ms = (time.perf_counter() - t_pre_start) * 1000

        # 2. Layer 1: Harmfulness Analysis (H)
        t_h_start = time.perf_counter()
        h_res = self.harmfulness_analyzer.analyze(prompts_so_far, current_prompt=user_prompt)
        h_score = h_res["harmfulness_score"]
        t_h_ms = (time.perf_counter() - t_h_start) * 1000

        # 3. Layer 2: Memory Update & Intent Escalation Analysis (E)
        t_e_start = time.perf_counter()
        # Memory engine tracks historical risk and trend
        # Turn risk approximation for memory update
        approx_turn_risk = 0.50 * h_score + 0.50 * self.rule_detector.evaluate_turn(prompts_so_far).get("rule_score", 0.0)
        memory_signals = self.memory_engine.add_turn(
            chat_id=session_id,
            prompt=user_prompt,
            current_risk=approx_turn_risk,
            safe_threshold=0.40
        )
        if prev_assistant_response:
            self.memory_engine.add_assistant_response(session_id, prev_assistant_response)

        e_res = self.intent_analyzer.analyze(prompts_so_far, memory_signals=memory_signals)
        e_score = e_res["intent_escalation_score"]
        t_e_ms = (time.perf_counter() - t_e_start) * 1000

        # 4. Layer 3: Known-Jailbreak Semantic Similarity (S)
        t_s_start = time.perf_counter()
        s_res = self.similarity_analyzer.score(prompts_so_far)
        s_score = s_res["jailbreak_similarity_score"]
        t_s_ms = (time.perf_counter() - t_s_start) * 1000

        # 5. Layer 4: Refusal Bypass & Behavioral Analysis (B)
        t_b_start = time.perf_counter()
        b_res = self.bypass_analyzer.analyze(
            prompts_so_far=prompts_so_far,
            prev_assistant_response=prev_assistant_response,
            current_prompt=user_prompt
        )
        b_score = b_res["refusal_bypass_score"]
        t_b_ms = (time.perf_counter() - t_b_start) * 1000

        # 6. Risk Fusion: Conversation Risk Score (CRS = 0.40H + 0.30E + 0.20S + 0.10B)
        t_crs_start = time.perf_counter()
        legacy_ctx = {
            "phase3_risk": approx_turn_risk,
            "historical_risk": memory_signals.get("historical_risk", 0.0),
            "trend_score": memory_signals.get("trend_score", 0.0),
            "persistence_memory": memory_signals.get("persistence_memory", 0.0),
            "bypass_score": b_res.get("bypass_detector_score", 0.0),
            "threshold": 0.80,
            "config": {}
        }
        risk_res = self.risk_engine.evaluate(
            h_score=h_score,
            e_score=e_score,
            s_score=s_score,
            b_score=b_score,
            legacy_context=legacy_ctx
        )
        crs = risk_res["crs"]
        t_crs_ms = (time.perf_counter() - t_crs_start) * 1000

        # 7. Adaptive Decision Engine (ALLOW / WARN / RESTRICT / BLOCK)
        t_dec_start = time.perf_counter()
        dec_res = self.decision_engine.decide(
            crs=crs,
            first_turn_prompt=first_turn_prompt,
            drift_detector=self.drift_detector
        )
        t_dec_ms = (time.perf_counter() - t_dec_start) * 1000

        t_total_ms = (time.perf_counter() - t_start) * 1000

        # Latency breakdown
        latency_breakdown = {
            "preprocessing_ms": round(t_pre_ms, 3),
            "harmfulness_h_ms": round(t_h_ms, 3),
            "intent_escalation_e_ms": round(t_e_ms, 3),
            "jailbreak_similarity_s_ms": round(t_s_ms, 3),
            "refusal_bypass_b_ms": round(t_b_ms, 3),
            "crs_calculation_ms": round(t_crs_ms, 3),
            "decision_generation_ms": round(t_dec_ms, 3),
            "total_turn_latency_ms": round(t_total_ms, 3)
        }

        # Structured Explainability Output
        explanation_report = {
            "summary": f"Turn {turn_number} Action: {dec_res['decision']} (CRS: {crs:.4f})",
            "equation": risk_res["equation"],
            "component_scores": {
                "H (Harmfulness)": h_score,
                "E (Intent Escalation)": e_score,
                "S (Jailbreak Similarity)": s_score,
                "B (Refusal Bypass)": b_score
            },
            "primary_factors": risk_res["primary_factors"],
            "decision_details": dec_res
        }

        turn_record = {
            "session_id": session_id,
            "turn_number": turn_number,
            "prompt": user_prompt,
            "H": h_score,
            "E": e_score,
            "S": s_score,
            "B": b_score,
            "crs": crs,
            "decision": dec_res["decision"],
            "is_allowed": dec_res["is_allowed"],
            "is_mitigated": dec_res["is_mitigated"],
            "is_blocked": dec_res["is_blocked"],
            "intervention_message": dec_res["intervention_message"],
            "memory_state": memory_signals,
            "h_details": h_res,
            "e_details": e_res,
            "s_details": s_res,
            "b_details": b_res,
            "latency": latency_breakdown,
            "explanation": explanation_report
        }

        # Persist in active session history
        self.active_sessions[session_id].append(turn_record)

        return turn_record
