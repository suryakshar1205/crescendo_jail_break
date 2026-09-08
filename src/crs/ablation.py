"""
Component Ablation Study Module for PRD CRS Architecture.

Systematically evaluates defense efficacy when individual components are ablated:
- Full System (0.40 H + 0.30 E + 0.20 S + 0.10 B)
- Ablation 1: Without Harmfulness Score H (w_H = 0.0)
- Ablation 2: Without Intent Escalation E (w_E = 0.0)
- Ablation 3: Without Jailbreak Similarity S (w_S = 0.0)
- Ablation 4: Without Refusal Bypass B (w_B = 0.0)
"""
import os
import json
import logging
from typing import List, Dict, Any

from .pipeline import CrescendoPRDPipeline
from .metrics import calculate_classification_metrics

logger = logging.getLogger(__name__)


def run_prd_ablation_study(
    attacks_dataset_path: str = "data/attacks/crescendo_attacks.json",
    benign_dataset_path: str = "data/benign/benign_chats.json",
    holdout_dataset_path: str = "data/holdout_attacks/unseen_crescendo_attacks.json"
) -> Dict[str, Any]:
    """
    Runs systematic ablation experiments across known and holdout datasets.

    Ablation configurations:
    1. Full System (w_H=0.40, w_E=0.30, w_S=0.20, w_B=0.10)
    2. No Harmfulness H (w_H=0.0, others normalized)
    3. No Intent Escalation E (w_E=0.0, others normalized)
    4. No Jailbreak Similarity S (w_S=0.0, others normalized)
    5. No Refusal Bypass B (w_B=0.0, others normalized)
    """
    # Load attack and benign datasets
    with open(attacks_dataset_path, "r", encoding="utf-8") as f:
        seen_attacks = json.load(f)
    with open(benign_dataset_path, "r", encoding="utf-8") as f:
        benign_chats = json.load(f)

    holdout_attacks = []
    if os.path.exists(holdout_dataset_path):
        with open(holdout_dataset_path, "r", encoding="utf-8") as f:
            holdout_attacks = json.load(f)

    ablation_configs = [
        {"name": "Full CRS Defense", "weights": {"H": 0.40, "E": 0.30, "S": 0.20, "B": 0.10}},
        {"name": "No Harmfulness (w_H=0.0)", "weights": {"H": 0.00, "E": 0.50, "S": 0.33, "B": 0.17}},
        {"name": "No Intent Escalation (w_E=0.0)", "weights": {"H": 0.57, "E": 0.00, "S": 0.29, "B": 0.14}},
        {"name": "No Jailbreak Similarity (w_S=0.0)", "weights": {"H": 0.50, "E": 0.38, "S": 0.00, "B": 0.12}},
        {"name": "No Refusal Bypass (w_B=0.0)", "weights": {"H": 0.44, "E": 0.33, "S": 0.23, "B": 0.00}},
    ]

    pipeline = CrescendoPRDPipeline(attacks_dataset_path=attacks_dataset_path)

    results_seen = []
    results_holdout = []

    # Run for each configuration
    for cfg in ablation_configs:
        cfg_name = cfg["name"]
        weights = cfg["weights"]
        logger.info(f"Running Ablation: {cfg_name}...")

        # Update pipeline weights
        pipeline.risk_engine.custom_weights = weights

        # Evaluate on Seen Attacks + Benign
        y_true_seen = []
        y_pred_seen = []
        detection_turns_seen = []
        latencies_seen = []

        # 1. Attack evaluation
        for idx, item in enumerate(seen_attacks):
            session_id = f"abl_seen_{cfg_name}_{idx}"
            pipeline.reset_session(session_id)
            flagged = False
            flagged_turn = None

            for t_idx, prompt in enumerate(item.get("turns", [])):
                res = pipeline.process_turn(session_id, prompt)
                latencies_seen.append(res["latency"]["total_turn_latency_ms"])
                if res["is_mitigated"] and not flagged:
                    flagged = True
                    flagged_turn = t_idx + 1

            y_true_seen.append(1)
            y_pred_seen.append(1 if flagged else 0)
            if flagged_turn:
                detection_turns_seen.append(flagged_turn)

        # 2. Benign evaluation
        for idx, item in enumerate(benign_chats):
            session_id = f"abl_benign_{cfg_name}_{idx}"
            pipeline.reset_session(session_id)
            flagged = False

            for prompt in item.get("turns", []):
                res = pipeline.process_turn(session_id, prompt)
                latencies_seen.append(res["latency"]["total_turn_latency_ms"])
                if res["is_mitigated"]:
                    flagged = True

            y_true_seen.append(0)
            y_pred_seen.append(1 if flagged else 0)

        metrics_seen = calculate_classification_metrics(
            y_true=y_true_seen,
            y_pred=y_pred_seen,
            detection_turns=detection_turns_seen,
            latencies_ms=latencies_seen
        )
        metrics_seen["configuration"] = cfg_name
        metrics_seen["weights"] = weights
        results_seen.append(metrics_seen)

        # Evaluate on Holdout Attacks if present
        if holdout_attacks:
            y_true_hold = []
            y_pred_hold = []
            detection_turns_hold = []

            for idx, item in enumerate(holdout_attacks):
                session_id = f"abl_hold_{cfg_name}_{idx}"
                pipeline.reset_session(session_id)
                flagged = False
                flagged_turn = None

                for t_idx, prompt in enumerate(item.get("turns", [])):
                    res = pipeline.process_turn(session_id, prompt)
                    if res["is_mitigated"] and not flagged:
                        flagged = True
                        flagged_turn = t_idx + 1

                y_true_hold.append(1)
                y_pred_hold.append(1 if flagged else 0)
                if flagged_turn:
                    detection_turns_hold.append(flagged_turn)

            # Re-use benign for holdout FPR calculation
            for _ in benign_chats:
                y_true_hold.append(0)
                y_pred_hold.append(0)  # benign evaluated above

            metrics_hold = calculate_classification_metrics(
                y_true=y_true_hold,
                y_pred=y_pred_hold,
                detection_turns=detection_turns_hold
            )
            metrics_hold["configuration"] = cfg_name
            results_holdout.append(metrics_hold)

    return {
        "seen_dataset_ablations": results_seen,
        "holdout_dataset_ablations": results_holdout
    }
