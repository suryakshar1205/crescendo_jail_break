#!/usr/bin/env python3
"""
Master Visualization Utility for Crescendo Jailbreak Defense.

Consolidates all plot rendering into a unified CLI entrypoint:
- Confusion Matrix Heatmap (True/False Positives & Negatives)
- Phase 5 Sensitivity & Stability Curves (ROC, DDR vs Threshold)
- Defense Trajectory and Mitigation Dynamics

Usage:
    python scripts/generate_plots.py --all
    python scripts/generate_plots.py --confusion
    python scripts/generate_plots.py --curves
"""
import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Ensure repo root is on python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.crs.pipeline import CrescendoPRDPipeline
from src.crs.visualizer import plot_confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_confusion_matrix_plot(output_dir: str = "results/plots"):
    """Evaluates defense pipeline and plots publication-grade confusion matrix heatmap."""
    os.makedirs(output_dir, exist_ok=True)
    out_png = os.path.join(output_dir, "confusion_matrix.png")

    pipeline = CrescendoPRDPipeline()
    
    attacks_path = os.path.join(PROJECT_ROOT, "data", "attacks", "crescendo_attacks.json")
    converted_path = os.path.join(PROJECT_ROOT, "data", "attacks", "converted_crescendo_attacks.json")
    benign_path = os.path.join(PROJECT_ROOT, "data", "benign", "benign_chats.json")
    
    with open(attacks_path, "r", encoding="utf-8") as f:
        attacks = json.load(f)
    if os.path.exists(converted_path):
        with open(converted_path, "r", encoding="utf-8") as f:
            attacks.extend(json.load(f))
            
    with open(benign_path, "r", encoding="utf-8") as f:
        benign_chats = json.load(f)
        
    logger.info(f"Loaded {len(attacks)} attacks and {len(benign_chats)} benign dialogues for confusion matrix.")

    tp = 0
    fn = 0
    for idx, attack in enumerate(attacks):
        session_id = f"plot_eval_atk_{idx}"
        pipeline.reset_session(session_id)
        detected = False
        for prompt in attack.get("turns", []):
            res = pipeline.process_turn(session_id, prompt)
            if res["is_mitigated"]:
                detected = True
                break
        if detected:
            tp += 1
        else:
            fn += 1

    tn = 0
    fp = 0
    for idx, chat in enumerate(benign_chats):
        session_id = f"plot_eval_benign_{idx}"
        pipeline.reset_session(session_id)
        falsely_flagged = False
        for prompt in chat.get("turns", []):
            res = pipeline.process_turn(session_id, prompt)
            if res["is_mitigated"]:
                falsely_flagged = True
                break
        if falsely_flagged:
            fp += 1
        else:
            tn += 1

    cm_dict = {"TP": tp, "FN": fn, "TN": tn, "FP": fp}
    logger.info(f"Computed metrics: TP={tp}, FN={fn}, TN={tn}, FP={fp}")
    
    plot_confusion_matrix(cm_dict, output_path=out_png, title="Crescendo Jailbreak Defense Confusion Matrix")
    logger.info(f"[+] Confusion matrix successfully saved to: {out_png}")


def generate_stability_curves(output_dir: str = "results/plots"):
    """Executes the stability and threshold sensitivity curves plotting module."""
    curves_script = os.path.join(PROJECT_ROOT, "scripts", "plot_phase5_curves.py")
    if os.path.exists(curves_script):
        import subprocess
        logger.info("Executing Phase 5 sensitivity & ROC curves generation...")
        cmd = [sys.executable, curves_script]
        subprocess.run(cmd, cwd=PROJECT_ROOT)
        logger.info("[+] Stability curves generated in results/plots/.")
    else:
        logger.warning("plot_phase5_curves.py not found, skipping curves.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Unified Plot Generation for Crescendo Jailbreak Defense."
    )
    parser.add_argument("--all", action="store_true", help="Generate all publication figures")
    parser.add_argument("--confusion", action="store_true", help="Generate Confusion Matrix plot")
    parser.add_argument("--curves", action="store_true", help="Generate ROC & Stability curves")

    args = parser.parse_args()

    if not (args.all or args.confusion or args.curves):
        # Default to all if no specific flag passed
        args.all = True

    if args.all or args.confusion:
        generate_confusion_matrix_plot()

    if args.all or args.curves:
        generate_stability_curves()


if __name__ == "__main__":
    main()
