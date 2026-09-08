"""
Canonical Crescendo PRD Defense Pipeline.

Executes the unified defense architecture:
User Turn
   ↓
Conversation History
   ↓
Semantic Drift Detector (S)
   ↓
Harmfulness Detector (H)
   ↓
Intent Escalation Detector (E)
   ↓
Bypass Detector (B)
   ↓
CRS Engine: CRS_t = 0.40H + 0.30E + 0.20S + 0.10B
   ↓
Conversation Memory: C_t = λ*C_{t-1} + (1-λ)*CRS_t
   ↓
Dynamic Threshold: T_t = T_0 - α*D_t - β*E_t - γ*L_t
   ↓
Decision Engine (with Dual-Threshold Hysteresis)
   ↓
ALLOW / WARN / RESTRICT / BLOCK
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

from .types import RiskMode, DecisionAction, TurnDefenseResult
from .semantic_drift import SemanticDriftAnalyzer
from .jailbreak_similarity import JailbreakSimilarityAnalyzer
from .harmfulness import HarmfulnessAnalyzer
from .intent_escalation import IntentEscalationAnalyzer
from .bypass_detection import RefusalBypassAnalyzer
from .conversation_memory import ConversationMemoryEngine
from .dynamic_threshold import DynamicThresholdCalibrator
from .decision_engine import AdaptiveDecisionEngine
from .crs_engine import ConversationRiskEngine, compute_crs
from .resource_profiler import ResourceProfiler

logger = logging.getLogger(__name__)


class CrescendoPRDPipeline:
    """
    Canonical End-to-End Defense Pipeline.
    Manages session tracking, coordinates security analyzers (H, E, S, B), computes CRS,
    accumulates conversation contextual risk, adapts dynamic thresholds, and enforces
    stateful decision hysteresis with research-grade explainability.
    """

    def __init__(
        self,
        risk_mode: RiskMode = RiskMode.PRD_CRS,
        attacks_dataset_path: str = "data/attacks/crescendo_attacks.json",
        memory_decay: Optional[float] = None,
        history_window: Optional[int] = None,
        allow_threshold: Optional[float] = None,
        warn_threshold: Optional[float] = None,
        restrict_threshold: Optional[float] = None,
        release_margin: Optional[float] = None,
        use_dynamic_mode: Optional[bool] = None,
        config_path: Optional[str] = "configs/master_defense_config.json"
    ):
        self.risk_mode = risk_mode

        # Load centralized master configuration if available
        cfg: Dict[str, Any] = {}
        if config_path and os.path.exists(config_path):
            try:
                import json
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load master config {config_path}: {e}")

        # Resolve hyperparameters from explicit args -> master config -> defaults
        mem_cfg = cfg.get("memory", {})
        dyn_cfg = cfg.get("dynamic_threshold", {})
        dec_cfg = cfg.get("decision", {})
        weights_cfg = cfg.get("crs_weights", None)

        self.memory_decay = memory_decay if memory_decay is not None else mem_cfg.get("decay_lambda", 0.80)
        self.history_window = history_window if history_window is not None else mem_cfg.get("history_window", 5)
        self.allow_threshold = allow_threshold if allow_threshold is not None else dec_cfg.get("allow_threshold", 0.40)
        self.warn_threshold = warn_threshold if warn_threshold is not None else dec_cfg.get("warn_threshold", 0.60)
        self.restrict_threshold = restrict_threshold if restrict_threshold is not None else dec_cfg.get("restrict_threshold", 0.75)
        self.release_margin = release_margin if release_margin is not None else dec_cfg.get("release_margin", 0.15)
        self.use_dynamic_mode = use_dynamic_mode if use_dynamic_mode is not None else dec_cfg.get("use_dynamic_mode", True)

        self.attacks_dataset_path = attacks_dataset_path

        # 1. Canonical Analyzers
        self.drift_analyzer = SemanticDriftAnalyzer(window_size=3)
        self.similarity_analyzer: Optional[JailbreakSimilarityAnalyzer] = None
        
        path_valid = False
        if isinstance(self.attacks_dataset_path, list):
            path_valid = any(os.path.exists(p) for p in self.attacks_dataset_path)
        elif isinstance(self.attacks_dataset_path, str) and self.attacks_dataset_path:
            path_valid = os.path.exists(self.attacks_dataset_path)

        if path_valid:
            try:
                self.similarity_analyzer = JailbreakSimilarityAnalyzer(
                    drift_detector=self.drift_analyzer.drift_detector,
                    dataset_path=self.attacks_dataset_path
                )
            except Exception as e:
                logger.warning(f"Could not initialize JailbreakSimilarityAnalyzer: {e}")

        self.harmfulness_analyzer = HarmfulnessAnalyzer()
        self.intent_analyzer = IntentEscalationAnalyzer()
        self.bypass_analyzer = RefusalBypassAnalyzer()

        # 2. Stateful Memory & Dynamic Thresholding
        self.memory_engine = ConversationMemoryEngine(
            memory_decay=self.memory_decay,
            history_window=self.history_window
        )
        self.dynamic_calibrator = DynamicThresholdCalibrator(
            base_threshold=dyn_cfg.get("base_threshold", self.restrict_threshold),
            min_threshold=dyn_cfg.get("min_threshold", 0.60),
            max_threshold=dyn_cfg.get("max_threshold", 0.85),
            alpha=dyn_cfg.get("alpha", 0.10),
            beta=dyn_cfg.get("beta", 0.15),
            gamma=dyn_cfg.get("gamma", 0.05)
        )

        # 3. Risk Engine and Decision Engine with Hysteresis
        self.risk_engine = ConversationRiskEngine(mode=self.risk_mode, custom_weights=weights_cfg)
        self.decision_engine = AdaptiveDecisionEngine(
            allow_threshold=self.allow_threshold,
            warn_threshold=self.warn_threshold,
            restrict_threshold=self.restrict_threshold,
            release_margin=self.release_margin,
            dynamic_calibrator=self.dynamic_calibrator,
            use_dynamic_mode=self.use_dynamic_mode
        )

        # 4. Resource & Hardware Profiler
        self.profiler = ResourceProfiler()

        # Active session histories: session_id -> list of turn records
        self.active_sessions: Dict[str, List[Dict[str, Any]]] = {}

    def reset_session(self, session_id: str):
        """Resets conversation history, memory state, and hysteresis for a session."""
        self.memory_engine.reset_session(session_id)
        self.decision_engine.reset_session(session_id)
        self.active_sessions[session_id] = []

    def process_turn(
        self,
        session_id: str,
        user_prompt: str,
        prev_assistant_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a single conversation turn through the canonical defense architecture.
        """
        t_start = time.perf_counter()

        # 1. Input Processing & History Tracking
        t_pre_start = time.perf_counter()
        if session_id not in self.active_sessions:
            self.reset_session(session_id)

        session_history = self.active_sessions[session_id]
        prompts_so_far = [turn["prompt"] for turn in session_history] + [user_prompt]
        turn_number = len(prompts_so_far)
        first_turn_prompt = prompts_so_far[0]
        if prev_assistant_response:
            self.memory_engine.record_assistant_response(session_id, prev_assistant_response)
        t_pre_ms = (time.perf_counter() - t_pre_start) * 1000

        # 2. Semantic Drift Layer (S)
        t_s_start = time.perf_counter()
        s_out = self.drift_analyzer.analyze(prompts_so_far)
        s_score = s_out["score"]
        anchor_drift = s_out["raw_details"].get("anchor_drift", 0.0)
        t_s_ms = (time.perf_counter() - t_s_start) * 1000

        # Known-Jailbreak Semantic Similarity Layer (FAISS index search)
        t_sim_start = time.perf_counter()
        t_sim_ms = 0.0
        if self.similarity_analyzer and self.similarity_analyzer.indexed_texts:
            sim_res = self.similarity_analyzer.score(prompts_so_far)
            sim_val = sim_res.get("jailbreak_similarity_score", 0.0)
            if sim_val > s_score:
                s_score = max(s_score, sim_val)
                if "known_jailbreak_match" not in s_out["signals"]:
                    s_out["signals"].append("known_jailbreak_match")
            t_sim_ms = (time.perf_counter() - t_sim_start) * 1000

        # 3. Harmfulness Layer (H)
        t_h_start = time.perf_counter()
        h_out = self.harmfulness_analyzer.analyze(prompts_so_far)
        h_score = h_out["score"]
        t_h_ms = (time.perf_counter() - t_h_start) * 1000

        # 4. Intent Escalation Layer (E)
        t_e_start = time.perf_counter()
        # Retrieve previous memory signals for escalation trend if available
        prior_mem = (
            {"trend_score": session_history[-1].get("trend", 0.0), "persistence_score": session_history[-1].get("persistence", 0.0)}
            if session_history else {}
        )
        e_out = self.intent_analyzer.analyze(prompts_so_far, memory_signals=prior_mem)
        e_score = e_out["score"]
        t_e_ms = (time.perf_counter() - t_e_start) * 1000

        # 5. Bypass & Refusal Resistance Layer (B)
        t_b_start = time.perf_counter()
        b_out = self.bypass_analyzer.analyze(
            prompts_so_far=prompts_so_far,
            prev_assistant_response=prev_assistant_response
        )
        b_score = b_out["score"]
        t_b_ms = (time.perf_counter() - t_b_start) * 1000

        # 6. Canonical Risk Fusion: CRS_t = 0.40H + 0.30E + 0.20S + 0.10B
        t_crs_start = time.perf_counter()
        legacy_ctx = {
            "phase3_risk": 0.70 * s_score + 0.30 * b_score,
            "historical_risk": session_history[-1].get("historical_risk", 0.0) if session_history else 0.0,
            "trend_score": prior_mem.get("trend_score", 0.0),
            "persistence_memory": prior_mem.get("persistence_score", 0.0),
            "bypass_score": b_score,
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

        # 7. Conversation Memory Context Accumulation: C_t = λ*C_{t-1} + (1-λ)*CRS_t
        t_mem_start = time.perf_counter()
        mem_res = self.memory_engine.update_turn(
            session_id=session_id,
            prompt=user_prompt,
            crs=crs
        )
        c_t = mem_res["contextual_risk"]
        trend_val = mem_res["trend_score"]
        persistence_val = mem_res["persistence_score"]
        t_mem_ms = (time.perf_counter() - t_mem_start) * 1000

        # 8. Adaptive Decision Engine with Stateful Hysteresis
        t_dec_start = time.perf_counter()
        dec_res = self.decision_engine.decide(
            crs=crs,
            contextual_risk=c_t,
            session_id=session_id,
            turn_number=turn_number,
            cumulative_drift=anchor_drift,
            escalation_score=e_score,
            first_turn_prompt=first_turn_prompt,
            drift_detector=self.drift_analyzer.drift_detector
        )
        t_dec_ms = (time.perf_counter() - t_dec_start) * 1000

        t_total_ms = (time.perf_counter() - t_start) * 1000

        # Combine active signals
        all_signals = list(set(s_out["signals"] + h_out["signals"] + e_out["signals"] + b_out["signals"]))

        # Latency breakdown
        latency_breakdown = {
            "preprocessing_ms": round(t_pre_ms, 3),
            "semantic_drift_s_ms": round(t_s_ms, 3),
            "jailbreak_similarity_s_ms": round(t_sim_ms, 3),
            "harmfulness_h_ms": round(t_h_ms, 3),
            "intent_escalation_e_ms": round(t_e_ms, 3),
            "bypass_detection_b_ms": round(t_b_ms, 3),
            "refusal_bypass_b_ms": round(t_b_ms, 3),
            "crs_fusion_ms": round(t_crs_ms, 3),
            "memory_accumulation_ms": round(t_mem_ms, 3),
            "decision_generation_ms": round(t_dec_ms, 3),
            "total_turn_latency_ms": round(t_total_ms, 3)
        }

        # Formatted Explainability Block (Priority 5)
        decision_label = dec_res["decision"]
        threshold_val = dec_res["thresholds_used"]["block"]
        explain_text = (
            f"\nConversation Risk Analysis (Turn {turn_number})\n"
            f"─────────────────────────────────────────────────\n"
            f"Harmfulness (H)      : {h_score:.4f} ({h_out['label']})\n"
            f"Intent Escalation (E): {e_score:.4f} ({e_out['label']})\n"
            f"Semantic Drift (S)   : {s_score:.4f} ({s_out['label']})\n"
            f"Bypass Behavior (B)  : {b_score:.4f} ({b_out['label']})\n"
            f"\n"
            f"CRS_t                : {crs:.4f}\n"
            f"Contextual Risk C_t  : {c_t:.4f}\n"
            f"Trajectory Trend     : {trend_val:+.4f}\n"
            f"Dynamic Threshold    : {threshold_val:.4f}\n"
            f"Decision             : {decision_label}\n"
            f"\n"
            f"Active Signals       :\n"
            + ("\n".join([f"  • {s}" for s in all_signals]) if all_signals else "  • None (Safe Dialogue)")
        )

        explanation_report = {
            "summary": f"Turn {turn_number} Action: {decision_label} (CRS: {crs:.4f}, C_t: {c_t:.4f})",
            "text": explain_text,
            "equation": risk_res["equation"],
            "component_scores": {
                "H (Harmfulness)": h_score,
                "E (Intent Escalation)": e_score,
                "S (Semantic Drift)": s_score,
                "B (Refusal Bypass)": b_score
            },
            "primary_factors": risk_res["primary_factors"],
            "decision_details": dec_res,
            "legacy_result": risk_res.get("legacy_result")
        }
        # Backward compatibility for legacy tests
        if risk_res.get("legacy_result"):
            dec_res["legacy_result"] = risk_res["legacy_result"]

        turn_record = {
            "session_id": session_id,
            "turn_number": turn_number,
            "prompt": user_prompt,
            "H": h_score,
            "E": e_score,
            "S": s_score,
            "B": b_score,
            "harmfulness": h_score,
            "escalation": e_score,
            "semantic_drift": s_score,
            "bypass": b_score,
            "crs": crs,
            "historical_risk": c_t,
            "contextual_risk": c_t,
            "trend": trend_val,
            "persistence": persistence_val,
            "threshold": threshold_val,
            "decision": decision_label,
            "is_allowed": dec_res["is_allowed"],
            "is_mitigated": dec_res["is_mitigated"],
            "is_blocked": dec_res["is_blocked"],
            "intervention_message": dec_res["intervention_message"],
            "signals": all_signals,
            "detector_outputs": {
                "H": h_out,
                "E": e_out,
                "S": s_out,
                "B": b_out
            },
            "latency": latency_breakdown,
            "latency_ms": latency_breakdown,
            "latency_breakdown": latency_breakdown,
            "hardware": self.profiler.get_hardware_snapshot(),
            "token_overhead": self.profiler.calculate_token_overhead(user_prompt, dec_res["intervention_message"]),
            "explanation": explanation_report,
            "explain_text": explain_text
        }

        # Persist to session history
        self.active_sessions[session_id].append(turn_record)
        return turn_record
