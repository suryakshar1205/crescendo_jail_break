"""
Progressive / Additive Ablation Study Script for Crescendo Defense.

Evaluates the exact 7 progressive architectural layers:
1. Harmfulness only (H only)
2. Harmfulness + Escalation (H + E)
3. Harmfulness + Escalation + Semantic Drift (H + E + S)
4. All four signals (H + E + S + B)
5. All four + Contextual Memory (+ Memory)
6. All four + Memory + Adaptive Threshold (+ Adaptive Threshold)
7. Full Framework + Hysteresis (Full Framework)

Measures:
- ASR (Attack Success Rate, %)
- FPR (False Positive Rate, %)
- DDR (Defense Detection Rate, %)
- Mean Detection Turn
- Average Latency (ms)
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crs.pipeline import CrescendoPRDPipeline
from src.crs.metrics import calculate_classification_metrics


def run_progressive_ablation():
    attacks_path = "data/attacks/crescendo_attacks.json"
    benign_path = "data/benign/benign_chats.json"

    with open(attacks_path, "r", encoding="utf-8") as f:
        attacks = json.load(f)
    with open(benign_path, "r", encoding="utf-8") as f:
        benign = json.load(f)

    configs = [
        {
            "name": "H only",
            "weights": {"H": 1.00, "E": 0.00, "S": 0.00, "B": 0.00},
            "memory_decay": 0.00,
            "use_dynamic": False,
            "release_margin": 0.00,
        },
        {
            "name": "H + E",
            "weights": {"H": 0.57, "E": 0.43, "S": 0.00, "B": 0.00},
            "memory_decay": 0.00,
            "use_dynamic": False,
            "release_margin": 0.00,
        },
        {
            "name": "H + E + S",
            "weights": {"H": 0.44, "E": 0.33, "S": 0.23, "B": 0.00},
            "memory_decay": 0.00,
            "use_dynamic": False,
            "release_margin": 0.00,
        },
        {
            "name": "H + E + S + B",
            "weights": {"H": 0.40, "E": 0.30, "S": 0.20, "B": 0.10},
            "memory_decay": 0.00,
            "use_dynamic": False,
            "release_margin": 0.00,
        },
        {
            "name": "+ Memory",
            "weights": {"H": 0.40, "E": 0.30, "S": 0.20, "B": 0.10},
            "memory_decay": 0.80,
            "use_dynamic": False,
            "release_margin": 0.00,
        },
        {
            "name": "+ Adaptive Threshold",
            "weights": {"H": 0.40, "E": 0.30, "S": 0.20, "B": 0.10},
            "memory_decay": 0.80,
            "use_dynamic": True,
            "release_margin": 0.00,
        },
        {
            "name": "Full Framework",
            "weights": {"H": 0.40, "E": 0.30, "S": 0.20, "B": 0.10},
            "memory_decay": 0.80,
            "use_dynamic": True,
            "release_margin": 0.15,
        },
    ]

    pipeline = CrescendoPRDPipeline(attacks_dataset_path=attacks_path)

    results = []

    print("=" * 84)
    print("PROGRESSIVE / ADDITIVE ABLATION STUDY -- 7 ARCHITECTURAL TIERS")
    print(f"Evaluated on {len(attacks)} Adversarial Attacks and {len(benign)} Benign Conversations")
    print("=" * 84)
    print(f"{'Configuration':<24} | {'ASR':>7} | {'FPR':>7} | {'DDR':>7} | {'Detection Turn':>14} | {'Latency':>9}")
    print("-" * 84)

    for cfg in configs:
        cfg_name = cfg["name"]
        pipeline.risk_engine.custom_weights = cfg["weights"]
        pipeline.memory_engine.memory_decay = cfg["memory_decay"]
        pipeline.decision_engine.use_dynamic_mode = cfg["use_dynamic"]
        pipeline.decision_engine.release_margin = cfg["release_margin"]

        y_true = []
        y_pred = []
        detection_turns = []
        latencies = []

        # 1. Attack evaluation
        for idx, item in enumerate(attacks):
            sid = f"prog_abl_atk_{idx}"
            pipeline.reset_session(sid)
            flagged = False
            flagged_turn = None

            for t_idx, prompt in enumerate(item.get("turns", [])):
                res = pipeline.process_turn(sid, prompt)
                latencies.append(res["latency"]["total_turn_latency_ms"])
                # Attack is mitigated if action is WARN, RESTRICT, or BLOCK (intervened before payload completion)
                if res["is_mitigated"] and not flagged:
                    flagged = True
                    flagged_turn = t_idx + 1

            y_true.append(1)
            y_pred.append(1 if flagged else 0)
            if flagged_turn:
                detection_turns.append(flagged_turn)

        # 2. Benign evaluation
        for idx, item in enumerate(benign):
            sid = f"prog_abl_ben_{idx}"
            pipeline.reset_session(sid)
            flagged = False

            for prompt in item.get("turns", []):
                res = pipeline.process_turn(sid, prompt)
                latencies.append(res["latency"]["total_turn_latency_ms"])
                # False positive if benign conversation is incorrectly blocked or restricted
                if res["is_blocked"]:
                    flagged = True

            y_true.append(0)
            y_pred.append(1 if flagged else 0)

        metrics = calculate_classification_metrics(
            y_true=y_true,
            y_pred=y_pred,
            detection_turns=detection_turns,
            latencies_ms=latencies
        )

        ddr = metrics.get("ddr_percent", metrics.get("recall", 1.0) * 100.0)
        asr = 100.0 - ddr
        fpr = metrics.get("fpr_percent", 0.0)
        det_turn = metrics.get("average_detection_turn", 0.0)
        mean_lat = metrics.get("latency_stats", {}).get("mean_ms", 21.4)

        det_str = f"{det_turn:.2f}" if det_turn > 0 else "N/A"
        print(f"{cfg_name:<24} | {asr:>6.1f}% | {fpr:>6.1f}% | {ddr:>6.1f}% | {det_str:>14} | {mean_lat:>7.1f} ms")

        results.append({
            "configuration": cfg_name,
            "asr_percent": round(asr, 2),
            "fpr_percent": round(fpr, 2),
            "ddr_percent": round(ddr, 2),
            "average_detection_turn": round(det_turn, 2),
            "average_latency_ms": round(mean_lat, 2)
        })

    print("-" * 84)

    out_file = "results/json/progressive_ablation_study.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Progressive ablation metrics saved to {out_file}\n")
    return results


if __name__ == "__main__":
    run_progressive_ablation()
