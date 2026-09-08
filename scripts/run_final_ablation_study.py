"""
Final Component Ablation Study Script.

Evaluates:
1. Full System (H + E + S + B + Memory + Dynamic Threshold)
2. Without Harmfulness (w_H = 0.0)
3. Without Intent Escalation (w_E = 0.0)
4. Without Jailbreak Similarity (w_S = 0.0)
5. Without Refusal Bypass (w_B = 0.0)
6. Without Conversation Memory (lambda = 0.0)
7. Without Dynamic Threshold (Fixed tau = 0.80)
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crs.ablation import run_prd_ablation_study

def main():
    print("=" * 75)
    print("FINAL ABLATION STUDY — SYSTEM COMPONENT CONTRIBUTION")
    print("=" * 75)

    res = run_prd_ablation_study(
        attacks_dataset_path="data/attacks/crescendo_attacks.json",
        benign_dataset_path="data/benign/benign_chats.json"
    )

    seen_metrics = res.get("seen_dataset_ablations", [])

    print("\n" + "-" * 75)
    print(f"{'Configuration':<36} | {'DDR':>7} | {'ASR':>7} | {'FPR':>7} | {'Mean Turn':>9}")
    print("-" * 75)

    table_rows = []
    for m in seen_metrics:
        name = m.get("configuration", "Unknown")
        ddr = m.get("ddr_percent", m.get("recall", 1.0) * 100.0)
        asr = 100.0 - ddr
        fpr = m.get("fpr_percent", 0.0)
        det_turn = m.get("average_detection_turn", 0.0)
        print(f"{name:<36} | {ddr:>6.1f}% | {asr:>6.1f}% | {fpr:>6.1f}% | {det_turn:>9.2f}")
        table_rows.append({
            "configuration": name,
            "ddr_percent": round(ddr, 2),
            "asr_percent": round(asr, 2),
            "fpr_percent": round(fpr, 2),
            "average_detection_turn": round(det_turn, 2)
        })
    print("-" * 75)

    out_file = "results/json/final_ablation_study.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(table_rows, f, indent=2)
    print(f"\n[+] Ablation study metrics successfully saved to {out_file}\n")


if __name__ == "__main__":
    main()
