import os
import sys
import json
import argparse
import logging

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.evaluator import RuleBasedEvaluator
from src.core.judge_evaluator import LLMJudgeEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger("src.core.evaluator").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def calculate_raw_cohen_kappa(y1, y2):
    """
    Computes Cohen's Kappa agreement score between two binary lists in raw Python.
    """
    n = len(y1)
    if n == 0:
        return 0.0
    
    # Concordance matrix
    # y1 is Rule-based, y2 is LLM Judge
    agreement = sum(1 for a, b in zip(y1, y2) if a == b)
    p_o = agreement / n  # Observed agreement
    
    # Marginal probabilities
    y1_true = sum(y1) / n
    y1_false = 1.0 - y1_true
    y2_true = sum(y2) / n
    y2_false = 1.0 - y2_true
    
    p_e = (y1_true * y2_true) + (y1_false * y2_false)  # Expected agreement by chance
    
    if p_e == 1.0:
        return 1.0
        
    kappa = (p_o - p_e) / (1.0 - p_e)
    return kappa

def main():
    parser = argparse.ArgumentParser(description="Evaluate agreement between RuleBasedEvaluator and LLMJudgeEvaluator")
    parser.add_argument("--results_json", type=str, default="results/json/baseline_results.json", help="Path to json results file")
    parser.add_argument("--model_id", type=str, default="meta-llama/Llama-Guard-3-1B", help="Model ID for LLM Judge")
    parser.add_argument("--judge", type=str, choices=["llama_guard", "rule", "mock"], default="mock",
                        help="Explicit evaluation mode: llama_guard (real), rule (heuristic), or mock (simulated)")
    parser.add_argument("--allow_fallback", action="store_true", default=False, help="Allow silent fallback if model fails to load")
    parser.add_argument("--out_json", type=str, default="results/json/judge_agreement_results.json", help="Output path for agreement metrics")
    args = parser.parse_args()

    if not os.path.exists(args.results_json):
        logger.error(f"Results file {args.results_json} not found.")
        return

    logger.info(f"Loading results from {args.results_json}")
    with open(args.results_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle either list format or dict with "details"
    if isinstance(data, list):
        details = data
    else:
        details = data.get("details", [])

    if not details:
        logger.warning("No detail records found in the results file.")
        return

    logger.info(f"Evaluating {len(details)} conversation turns using Judge Mode: [{args.judge.upper()}]...")
    
    from src.phase6.judge_evaluator import LLMJudgeEvaluator
    rule_evaluator = RuleBasedEvaluator()
    judge_evaluator = LLMJudgeEvaluator(
        model_id=args.model_id,
        mode=args.judge,
        allow_fallback=args.allow_fallback,
        mock=(args.judge == "mock")
    )

    y_rules = []
    y_judge = []

    for idx, record in enumerate(details):
        prompt = record.get("prompt", "")
        if not prompt and "history" in record and record["history"]:
            prompt = record["history"][-1]
        response = record.get("response", "")
        
        # Evaluate using both rule and judge
        eval_rules = rule_evaluator.evaluate(prompt, response)
        eval_judge = judge_evaluator.evaluate(prompt, response)

        y_rules.append(int(eval_rules))
        y_judge.append(int(eval_judge))

    # Confusion matrix:
    # y_rules (Reference Ground Truth), y_judge (Judge Prediction)
    # [ [TN, FP], [FN, TP] ]
    tn = sum(1 for r, j in zip(y_rules, y_judge) if r == 0 and j == 0)
    fp = sum(1 for r, j in zip(y_rules, y_judge) if r == 0 and j == 1)
    fn = sum(1 for r, j in zip(y_rules, y_judge) if r == 1 and j == 0)
    tp = sum(1 for r, j in zip(y_rules, y_judge) if r == 1 and j == 1)

    # Calculate metrics
    agreement = sum(1 for a, b in zip(y_rules, y_judge) if a == b)
    pct_agreement = (agreement / len(details)) * 100.0
    
    try:
        from sklearn.metrics import cohen_kappa_score
        sklearn_kappa = cohen_kappa_score(y_rules, y_judge)
    except ImportError:
        sklearn_kappa = None

    raw_kappa = calculate_raw_cohen_kappa(y_rules, y_judge)
    
    # Interpretation
    if raw_kappa >= 0.81:
        interpretation = "Almost Perfect Agreement"
    elif raw_kappa >= 0.61:
        interpretation = "Substantial Agreement"
    elif raw_kappa >= 0.41:
        interpretation = "Moderate Agreement"
    elif raw_kappa >= 0.21:
        interpretation = "Fair Agreement"
    elif raw_kappa >= 0.0:
        interpretation = "Slight Agreement"
    else:
        interpretation = "Poor/No Agreement"

    eval_meta = judge_evaluator.get_metadata()
    exec_mode = eval_meta.get("mode", eval_meta.get("execution_mode", "UNKNOWN"))
    fallback_flag = eval_meta.get("fallback", eval_meta.get("fallback_occurred", False))

    print("\n" + "=" * 65)
    print("LLM JUDGE AGREEMENT EVALUATION SUMMARY")
    print("=" * 65)
    print(f"  • Model ID            : {args.model_id}")
    print(f"  • Requested Mode      : {args.judge}")
    print(f"  • Execution Mode      : {exec_mode}")
    print(f"  • Fallback Occurred   : {fallback_flag}")
    print(f"  • Samples Evaluated   : {len(details)}")
    print(f"  • Observed Agreement  : {pct_agreement:.2f}% ({agreement}/{len(details)})")
    if sklearn_kappa is not None:
        print(f"  • Cohen's Kappa (SK)  : {sklearn_kappa:.4f}")
    print(f"  • Cohen's Kappa (Raw) : {raw_kappa:.4f}")
    print(f"  • Agreement Level     : {interpretation}")
    print("  • Confusion Matrix    :")
    print(f"      [[TN={tn:3d}, FP={fp:3d}],")
    print(f"       [FN={fn:3d}, TP={tp:3d}]]")
    print("=" * 65)

    res_data = {
        "model_id": args.model_id,
        "requested_mode": args.judge,
        "execution_mode": exec_mode,
        "fallback_occurred": fallback_flag,
        "total_samples": len(details),
        "observed_agreement_pct": round(pct_agreement, 2),
        "cohen_kappa": round(raw_kappa, 4),
        "cohen_kappa_sklearn": round(float(sklearn_kappa), 4) if sklearn_kappa is not None and not np.isnan(sklearn_kappa) else None,
        "agreement_level": interpretation,
        "confusion_matrix": {
            "tn": tn,
            "fp": fp,
            "fn": fn,
            "tp": tp
        }
    }

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(res_data, f, indent=2)
    print(f"[+] Agreement results saved to {args.out_json}\n")


if __name__ == "__main__":
    main()
