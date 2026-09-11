# Phase 9: Unified Research-Grade Harness & Benchmarking Report

This report compiles all advanced research-level safety evaluations, optimization passes, and stress tests.

## 1. Cross-Model Safety & Robustness Metrics

| Model ID | Attack Success Rate (ASR) | False Positive Rate (FPR) | Drift Detection Rate (DDR) | Avg Detection Turn | Avg Latency (ms) |
| --- | --- | --- | --- | --- | --- |
| meta-llama/Llama-3.2-3B-Instruct | 0.00% | 100.00% | 100.00% | 3.50 | 154735.4 |
| meta-llama/Llama-3.1-8B-Instruct | 0.00% | 100.00% | 100.00% | 3.50 | 154725.7 |
| mistralai/Mistral-7B-Instruct-v0.3 | 0.00% | 100.00% | 100.00% | 3.50 | 154725.6 |

## 2. LLM-as-a-Judge Prompt Optimization Results

| Prompt Template | Observed Consensus Agreement | Cohen's Kappa score ($\kappa$) |
| --- | --- | --- |
| Standard | 90.00% | `0.0000` |
| Chain of thought | 95.00% | `0.0000` |
| Few shot | 98.33% | `0.0000` |

## 3. Adaptive Adversary Evasion Spacing Solver

Calculates safety boundaries against attackers attempting to evade risk accumulation through filler turn intervals.

| Memory Decay constant ($\gamma$) | Defense Threshold ($T$) | Min Spacing interval to bypass block |
| --- | --- | --- |
| 0.50 | 0.92 | `0` turns |
| 0.70 | 0.92 | `0` turns |
| 0.80 | 0.92 | `0` turns |
| 0.90 | 0.92 | `0` turns |

## 4. Human-in-the-Loop FPR Auditing

* **Total Audited flagged cases**: `27`
* **Human Safety Team Consensus blocks**: `27`
* **Human Safety Team Overruled blocks (FPs)**: `0`
