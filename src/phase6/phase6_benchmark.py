#!/usr/bin/env python3
import os
import json
import argparse
import logging
from typing import List, Dict, Any
from src.core.evaluator import RuleBasedEvaluator
from src.phase6.judge_evaluator import LLMJudgeEvaluator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def calculate_raw_cohen_kappa(y1, y2):
    n = len(y1)
    if n == 0:
        return 0.0
    agreement = sum(1 for a, b in zip(y1, y2) if a == b)
    p_o = agreement / n
    y1_true = sum(y1) / n
    y1_false = 1.0 - y1_true
    y2_true = sum(y2) / n
    y2_false = 1.0 - y2_true
    p_e = (y1_true * y2_true) + (y1_false * y2_false)
    if p_e == 1.0:
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)

def run_phase6_benchmark(results_json: str, config_path: str, output_dir: str, report_path: str, mock: bool):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(config_path, "r") as f:
        config = json.load(f)

    if not os.path.exists(results_json):
        # If baseline results do not exist, check phase4 persistent cache or fallback
        logger.warning(f"Results file {results_json} not found. Searching alternative cache.")
        results_json = "results/json/phase4_inference_cache.json"
        if not os.path.exists(results_json):
            logger.error("No valid input results found to evaluate.")
            return

    logger.info(f"Loading turns from: {results_json}")
    with open(results_json, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Re-map cached dictionaries if needed
    details = []
    if isinstance(raw_data, list):
        # phase4 persistent cache list style
        for entry in raw_data:
            history = entry.get("history", [])
            response = entry.get("response", "")
            if history:
                prompt = history[-1]
                details.append({"prompt": prompt, "response": response})
    else:
        details = raw_data.get("details", [])

    if not details:
        logger.warning("No conversation records found to evaluate.")
        return

    rule_evaluator = RuleBasedEvaluator()
    judge_evaluator = LLMJudgeEvaluator(model_id=config.get("judge_model_id"), mock=mock)

    y_rules = []
    y_judge = []

    for item in details:
        prompt = item.get("prompt", "")
        response = item.get("response", "")
        y_rules.append(int(rule_evaluator.evaluate(prompt, response)))
        y_judge.append(int(judge_evaluator.evaluate(prompt, response)))

    total = len(details)
    agreement = sum(1 for a, b in zip(y_rules, y_judge) if a == b)
    pct_agreement = (agreement / total) * 100.0 if total > 0 else 0.0
    kappa = calculate_raw_cohen_kappa(y_rules, y_judge)

    # Save JSON metrics
    metrics_out = {
        "total_evaluated_turns": total,
        "observed_agreement_pct": round(pct_agreement, 4),
        "cohen_kappa_score": round(kappa, 4)
    }
    with open(os.path.join(output_dir, "agreement_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, indent=2)

    # Save Markdown report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Phase 6: LLM-as-a-Judge Evaluation & Consensus Report\n\n")
        f.write(f"This report documents the statistical agreement between the Rule-Based safety heuristic and the Causal LLM-as-a-Judge model (`{config.get('judge_model_id')}`).\n\n")
        f.write(f"## Consensus Metrics Summary\n\n")
        f.write(f"* **Total Evaluated turns**: `{total}`\n")
        f.write(f"* **Observed agreement**: `{pct_agreement:.2f}%`\n")
        f.write(f"* **Cohen's Kappa ($\kappa$) score**: `{kappa:.4f}`\n\n")
        f.write(f"## Interpretation\n\n")
        if kappa >= 0.81:
            f.write(f"The agreement level is **Almost Perfect Agreement ($\kappa \ge 0.81$)**.\n")
        elif kappa >= 0.61:
            f.write(f"The agreement level is **Substantial Agreement ($0.61 \le \kappa < 0.81$)**.\n")
        else:
            f.write(f"The agreement level is **Moderate or Fair Agreement ($\kappa < 0.61$)**.\n")
            
    logger.info(f"Phase 6 Benchmark completed. Metrics saved to {output_dir}, report saved to {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Phase 6 LLM-as-a-Judge Validation Benchmark")
    parser.add_argument("--results_json", type=str, default="results/json/baseline_results.json", help="Path to json results")
    parser.add_argument("--config_path", type=str, default="configs/phase6_config.json", help="Config file path")
    parser.add_argument("--output_dir", type=str, default="results/phase6", help="Results folder")
    parser.add_argument("--report_path", type=str, default="reports/phase6/agreement_report.md", help="Markdown output path")
    parser.add_argument("--mock_inference", action="store_true", help="Force mock evaluator mode")
    args = parser.parse_args()

    run_phase6_benchmark(
        results_json=args.results_json,
        config_path=args.config_path,
        output_dir=args.output_dir,
        report_path=args.report_path,
        mock=args.mock_inference
    )

if __name__ == "__main__":
    main()
