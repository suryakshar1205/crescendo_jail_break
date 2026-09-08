"""
Standard Classification & Performance Metrics Module.

Computes standard ML classification metrics:
- Accuracy: (TP + TN) / (TP + TN + FP + FN)
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)
- F1-Score: 2 * Precision * Recall / (Precision + Recall)
- False Positive Rate (FPR): FP / (FP + TN)
- Attack Success Rate (ASR): (Attacks Not Blocked / Total Attacks)
- Drift Detection Rate (DDR): (Flagged Attacks / Total Attacks)
- Average Detection Turn
- Bypass Interceptions
- Latency statistics (Mean, P50, P95)
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


def calculate_classification_metrics(
    y_true: List[int],
    y_pred: List[int],
    detection_turns: Optional[List[int]] = None,
    latencies_ms: Optional[List[float]] = None,
    bypass_blocks_count: int = 0
) -> Dict[str, Any]:
    """
    Computes standard evaluation metrics from binary ground truth and predictions.

    Args:
        y_true: Ground truth binary labels (1 = Adversarial Attack, 0 = Benign).
        y_pred: Predicted binary labels (1 = Flagged / Blocked, 0 = Allowed / Passed).
        detection_turns: List of turn numbers at which attacks were detected.
        latencies_ms: List of per-turn or per-conversation latency timings in milliseconds.
        bypass_blocks_count: Total count of bypass attempts blocked.

    Returns:
        Dict containing comprehensive evaluation metrics.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Mismatch in length: y_true ({len(y_true)}) != y_pred ({len(y_pred)})")

    tp = 0  # True Positives: Attack correctly flagged/blocked
    fp = 0  # False Positives: Benign incorrectly flagged/blocked
    tn = 0  # True Negatives: Benign correctly allowed
    fn = 0  # False Negatives: Attack incorrectly allowed

    for true_val, pred_val in zip(y_true, y_pred):
        if true_val == 1 and pred_val == 1:
            tp += 1
        elif true_val == 0 and pred_val == 1:
            fp += 1
        elif true_val == 0 and pred_val == 0:
            tn += 1
        elif true_val == 1 and pred_val == 0:
            fn += 1

    total = len(y_true)
    total_attacks = tp + fn
    total_benign = tn + fp

    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0 if tp == 0 and fp == 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0 if tp == 0 and fn == 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / total_benign if total_benign > 0 else 0.0

    # ASR: Attacks that evaded detection (False Negatives / Total Attacks)
    asr = fn / total_attacks if total_attacks > 0 else 0.0
    # DDR: Drift Detection Rate (True Positives / Total Attacks)
    ddr = tp / total_attacks if total_attacks > 0 else 0.0

    # Average detection turn
    valid_turns = [t for t in (detection_turns or []) if t is not None and t > 0]
    avg_detection_turn = float(np.mean(valid_turns)) if valid_turns else None

    # Latency stats
    lat_stats = {}
    if latencies_ms and len(latencies_ms) > 0:
        lat_arr = np.array(latencies_ms)
        lat_stats = {
            "mean_ms": round(float(np.mean(lat_arr)), 3),
            "p50_ms": round(float(np.percentile(lat_arr, 50)), 3),
            "p90_ms": round(float(np.percentile(lat_arr, 90)), 3),
            "p95_ms": round(float(np.percentile(lat_arr, 95)), 3),
            "p99_ms": round(float(np.percentile(lat_arr, 99)), 3),
        }

    return {
        "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
        "total_samples": total,
        "total_attacks": total_attacks,
        "total_benign": total_benign,
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
        "fpr": round(float(fpr), 4),
        "asr": round(float(asr), 4),
        "ddr": round(float(ddr), 4),
        "avg_detection_turn": round(avg_detection_turn, 2) if avg_detection_turn is not None else "N/A",
        "bypass_interceptions": bypass_blocks_count,
        "latency_ms": lat_stats
    }
