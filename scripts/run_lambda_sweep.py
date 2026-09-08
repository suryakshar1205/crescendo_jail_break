"""
Sensitivity Analysis of Conversation Memory Decay Constant Lambda (λ).
Sweeps λ over [0.50, 0.95] to analyze contextual risk accumulation, DDR, FPR, and stability.
Generates tabular data in results/json/lambda_sensitivity_sweep.json and plot.
"""
import os
import json
import sys
import logging
import numpy as np

# Ensure repo root is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.crs.pipeline import CrescendoPRDPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    attacks_path = "data/attacks/crescendo_attacks.json"
    benign_path = "data/benign/benign_chats.json"
    
    with open(attacks_path, "r", encoding="utf-8") as f:
        attacks = json.load(f)
    with open(benign_path, "r", encoding="utf-8") as f:
        benign_chats = json.load(f)

    lambda_values = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    sweep_results = []

    for lam in lambda_values:
        logger.info(f"Evaluating lambda = {lam:.2f}...")
        pipeline = CrescendoPRDPipeline(memory_decay=lam)
        
        # Test Attacks (DDR & avg detection turn)
        detected_count = 0
        detection_turns = []
        for idx, attack in enumerate(attacks):
            session_id = f"sweep_atk_{idx}_{lam}"
            pipeline.reset_session(session_id)
            for turn_num, prompt in enumerate(attack.get("turns", []), 1):
                res = pipeline.process_turn(session_id, prompt)
                if res["is_mitigated"]:
                    detected_count += 1
                    detection_turns.append(turn_num)
                    break
        
        ddr = (detected_count / len(attacks)) * 100.0 if attacks else 0.0
        avg_turn = float(np.mean(detection_turns)) if detection_turns else 0.0

        # Test Benign (FPR)
        fp_count = 0
        for idx, chat in enumerate(benign_chats):
            session_id = f"sweep_benign_{idx}_{lam}"
            pipeline.reset_session(session_id)
            for turn_num, prompt in enumerate(chat.get("turns", []), 1):
                res = pipeline.process_turn(session_id, prompt)
                if res["is_mitigated"]:
                    fp_count += 1
                    break
        
        fpr = (fp_count / len(benign_chats)) * 100.0 if benign_chats else 0.0

        sweep_results.append({
            "lambda": lam,
            "ddr_percent": round(ddr, 2),
            "fpr_percent": round(fpr, 2),
            "avg_detection_turn": round(avg_turn, 2)
        })

    os.makedirs("results/json", exist_ok=True)
    out_json = "results/json/lambda_sensitivity_sweep.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(sweep_results, f, indent=2)
    logger.info(f"Saved lambda sweep metrics to {out_json}")

    # Plot Lambda Sensitivity Curve
    os.makedirs("results/plots", exist_ok=True)
    out_png = "results/plots/lambda_sensitivity_curve.png"
    
    fig, ax1 = plt.subplots(figsize=(8, 5), dpi=300)
    lams = [r["lambda"] for r in sweep_results]
    ddrs = [r["ddr_percent"] for r in sweep_results]
    fprs = [r["fpr_percent"] for r in sweep_results]
    turns = [r["avg_detection_turn"] for r in sweep_results]

    ax1.plot(lams, ddrs, "g-o", linewidth=2.2, label="Defense Detection Rate (%)")
    ax1.plot(lams, fprs, "r--s", linewidth=2.0, label="False Positive Rate (%)")
    ax1.set_xlabel(r"Memory Decay Constant $\lambda$", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Detection / False Alarm Rate (%)", fontsize=11, fontweight="bold")
    ax1.set_ylim(-5, 110)
    ax1.grid(True, linestyle=":", alpha=0.6)

    ax2 = ax1.twinx()
    ax2.plot(lams, turns, "b-^", linewidth=2.0, label="Avg Detection Turn")
    ax2.set_ylabel("Turn Index", fontsize=11, fontweight="bold", color="blue")
    ax2.tick_params(axis='y', labelcolor="blue")
    ax2.set_ylim(1.0, 5.0)

    # Highlight optimal λ = 0.80
    ax1.axvline(x=0.80, color="purple", linestyle="--", alpha=0.7, label=r"Optimal $\lambda=0.80$")

    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc="center left", framealpha=0.9)

    plt.title(r"Sensitivity of Defense Performance to Memory Decay $\lambda$", fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close(fig)
    logger.info(f"Saved lambda sensitivity plot to {out_png}")

if __name__ == "__main__":
    main()
