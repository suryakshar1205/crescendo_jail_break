# Phase 6: LLM-as-a-Judge Evaluation & Consensus Report

This report documents the statistical agreement between the Rule-Based safety heuristic and the Causal LLM-as-a-Judge model (`meta-llama/Llama-Guard-3-1B`).

## Consensus Metrics Summary

* **Total Evaluated turns**: `56`
* **Observed agreement**: `94.64%`
* **Cohen's Kappa ($\kappa$) score**: `0.8842`

## Interpretation

The agreement level is **Almost Perfect Agreement ($\kappa \ge 0.81$)**.
- Both the Rule-Based Safety Evaluator and the Causal LLM Judge show strong consistency in labeling jailbreak complies.
- Fallback activation successfully routes traffic under network or offline limits, preserving evaluation pipeline integrity.
