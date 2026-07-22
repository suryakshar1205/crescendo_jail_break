#!/usr/bin/env python3
import os
import json
import argparse
import logging
from src.core.evaluator import RuleBasedEvaluator
from src.core.judge_evaluator import LLMJudgeEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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
    parser.add_argument("--mock", action="store_true", default=True, help="Force mock evaluator mode (highly recommended for offline/local CPU)")
    parser.add_argument("--no_mock", dest="mock", action="store_false", help="Run real inference using model weights")
    args = parser.parse_args()

    if not os.path.exists(args.results_json):
        logger.error(f"Results file {args.results_json} not found.")
        return

    logger.info(f"Loading results from {args.results_json}")
    with open(args.results_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Details are in "details" array
    details = data.get("details", [])
    if not details:
        logger.warning("No detail records found in the results file.")
        return

    logger.info(f"Evaluating {len(details)} conversation turns...")
    
    rule_evaluator = RuleBasedEvaluator()
    judge_evaluator = LLMJudgeEvaluator(model_id=args.model_id, mock=args.mock)

    y_rules = []
    y_judge = []

    for idx, record in enumerate(details):
        prompt = record.get("prompt", "")
        response = record.get("response", "")
        
        # Evaluate using both rule and judge
        eval_rules = rule_evaluator.evaluate(prompt, response)
        eval_judge = judge_evaluator.evaluate(prompt, response)

        y_rules.append(int(eval_rules))
        y_judge.append(int(eval_judge))

    # Calculate metrics
    agreement = sum(1 for a, b in zip(y_rules, y_judge) if a == b)
    pct_agreement = (agreement / len(details)) * 100.0
    
    try:
        from sklearn.metrics import cohen_kappa_score
        sklearn_kappa = cohen_kappa_score(y_rules, y_judge)
    except ImportError:
        sklearn_kappa = None

    raw_kappa = calculate_raw_cohen_kappa(y_rules, y_judge)
    
    logger.info("=" * 60)
    logger.info("EVALUATION COMPARISON SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Evaluated Turns:   {len(details)}")
    logger.info(f"Observed Agreement:      {pct_agreement:.2f}% ({agreement}/{len(details)})")
    if sklearn_kappa is not None:
        logger.info(f"Cohen's Kappa (Sklearn): {sklearn_kappa:.4f}")
    logger.info(f"Cohen's Kappa (Calculated): {raw_kappa:.4f}")
    
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
        
    logger.info(f"Agreement Level:         {interpretation}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
