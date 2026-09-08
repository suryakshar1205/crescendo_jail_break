"""
Generates the publication-grade Confusion Matrix Heatmap for Crescendo Defense.
Evaluates both benign dialogues and adversarial attacks, and outputs results/plots/confusion_matrix.png.
"""
import os
import json
import sys
import logging

# Ensure repo root is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crs.pipeline import CrescendoPRDPipeline
from src.crs.visualizer import plot_confusion_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    pipeline = CrescendoPRDPipeline()
    
    attacks_path = "data/attacks/crescendo_attacks.json"
    converted_attacks_path = "data/attacks/converted_crescendo_attacks.json"
    benign_path = "data/benign/benign_chats.json"
    
    with open(attacks_path, "r", encoding="utf-8") as f:
        attacks = json.load(f)
    if os.path.exists(converted_attacks_path):
        with open(converted_attacks_path, "r", encoding="utf-8") as f:
            attacks.extend(json.load(f))
            
    with open(benign_path, "r", encoding="utf-8") as f:
        benign_chats = json.load(f)
        
    logger.info(f"Loaded {len(attacks)} total attacks (reference + converted) and {len(benign_chats)} benign conversations.")

    tp = 0
    fn = 0
    for idx, attack in enumerate(attacks):
        session_id = f"eval_atk_{idx}"
        pipeline.reset_session(session_id)
        detected = False
        for turn_num, prompt in enumerate(attack.get("turns", []), 1):
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
        session_id = f"eval_benign_{idx}"
        pipeline.reset_session(session_id)
        falsely_flagged = False
        for turn_num, prompt in enumerate(chat.get("turns", []), 1):
            res = pipeline.process_turn(session_id, prompt)
            if res["is_mitigated"]:
                falsely_flagged = True
                break
        if falsely_flagged:
            fp += 1
        else:
            tn += 1

    cm_dict = {"TP": tp, "FN": fn, "TN": tn, "FP": fp}
    logger.info(f"Confusion Matrix Evaluation: {cm_dict}")
    
    out_png = "results/plots/confusion_matrix.png"
    plot_confusion_matrix(cm_dict, output_path=out_png, title="Crescendo Jailbreak Defense Confusion Matrix")
    logger.info(f"Generated confusion matrix plot at {out_png}")

if __name__ == "__main__":
    main()
