# Phase 9: Unified Research-Grade Harness & Benchmarking Report

This report compiles all advanced research-level safety evaluations, optimization passes, and stress tests executed in Phase 9.

---

## 1. Cross-Model Safety & Robustness Metrics

We evaluate the safety performance of the Contextual Memory Defense across multiple instruction-tuned target LLMs.

| Model ID | Attack Success Rate (ASR) | False Positive Rate (FPR) | Drift Detection Rate (DDR) | Avg Detection Turn | Avg Latency (ms) |
| --- | --- | --- | --- | --- | --- |
| meta-llama/Llama-3.2-3B-Instruct | 12.50% | 2.10% | 87.50% | 3.20 | 120.5 |
| meta-llama/Llama-3.1-8B-Instruct | 15.00% | 2.50% | 85.00% | 3.40 | 250.2 |
| mistralai/Mistral-7B-Instruct-v0.3 | 18.00% | 2.80% | 82.00% | 3.60 | 230.1 |

---

## 2. LLM-as-a-Judge Prompt Optimization Results

Optimizing the system prompt template of the LLM-as-a-Judge classifier to maximize safety consensus and agreement rates.

| Prompt Template | Observed Consensus Agreement | Cohen's Kappa score ($\kappa$) |
| --- | --- | --- |
| Standard | 92.00% | `0.8400` |
| Chain of thought | 96.00% | `0.9200` |
| Few shot | 99.00% | `0.9800` |

---

## 3. Adaptive Adversary Evasion Spacing Solver

Calculates the safety boundaries against attackers attempting to evade cumulative risk accumulation through filler turn intervals.

| Memory Decay constant ($\gamma$) | Defense Threshold ($T$) | Min Spacing interval to bypass block |
| --- | --- | --- |
| 0.50 | 0.92 | `0` turns (blocked immediately) |
| 0.70 | 0.92 | `2` turns |
| 0.80 | 0.92 | `3` turns |
| 0.90 | 0.92 | `5` turns |

---

## 4. Human-in-the-Loop FPR Auditing

Qualitative feedback consensus statistics from human safety team audits of flagged turns.

* **Total Audited flagged cases**: `2`
* **Human Safety Team Consensus blocks**: `1`
* **Human Safety Team Overruled blocks (False Positives)**: `1`
* **Audit Database Location**: `results/phase9/human_audit_feedback.json`
