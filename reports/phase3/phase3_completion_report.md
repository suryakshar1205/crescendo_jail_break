# Phase 3 — Completion Report: Hybrid Risk Fusion Defense for Crescendo Jailbreak

This report details the implementation, sweep analysis, and validation results for **Phase 3 (G2_hybrid_risk_fusion)** of the Crescendo jailbreak defense system.

---

## 1. Executive Summary

The objective of Phase 3 was to design, implement, and validate a lightweight, CPU-efficient, and explainable **Hybrid Risk Fusion Defense** that improves upon Phase 2 by fusing embedding-based semantic drift signals with behavioral rule-based signals. 

By integrating semantic drift detection ($W_{semantic} = 0.70$) with optimized behavioral escalation pattern matching ($W_{rule} = 0.30$), we achieved the following validation outcomes:
* **Selected Best Threshold**: `0.90` (selected by the benchmarking optimizer)
* **Attack Success Rate (ASR)**: **`0.1000`** (a **50% relative reduction** compared to Phase 2's ASR of `0.2000`, and a **75% relative reduction** compared to the baseline ASR of `0.4000`).
* **False Positive Rate (FPR)**: **`0.0000`** (perfect utility retention, significantly beating the success criteria limit of $\le 0.10$, and improving upon Phase 2's FPR of `0.0667`).
* **Drift Detection Rate (DDR)**: **`0.8000`** (8 out of 10 attack sessions successfully intercepted).
* **Average Latency**: **`25.08s`** per turn (a **45% reduction** compared to baseline `45.54s` due to early termination of blocked sessions).

### Alternative Highly-Performing Thresholds:
* **Threshold `0.86`**: ASR = `0.1000`, FPR = `0.0000`, DDR = **`0.9000`** (higher detection coverage), Mitigation Rate = **`0.5000`**, Avg Latency = **`21.87s`**.
* **Threshold `0.83`**: ASR = `0.1000`, FPR = `0.0667`, DDR = **`0.9000`**, Mitigation Rate = **`0.5000`**, Avg Latency = **`21.27s`**.

Both thresholds meet the primary success criteria (ASR $\le 0.10$, FPR $\le 0.10$) and offer additional mitigation options depending on system preferences.

---

## 2. Detection Strategy & Architecture

The Phase 3 defense architecture extends the existing framework by implementing a hybrid scoring model that fuses semantic and rule-based signals into a single unified risk score.

### 2.1 Optimized Behavioral Rule Detector
We modified `src/rule_detector.py` to prevent adversarial keyword evasion and scale risk metrics:
1. **Keyword Density**: Replaced rigid keyword matching with robust case-insensitive regular expressions that permit arbitrary filler words between multi-word phrases (e.g., matching `"write a Python script"` or `"write a malicious script"` instead of just `"write a script"`).
2. **Actionability and Persistence**: Scaled metrics to reflect behavioral escalation across historical turns, tracking escalation patterns and refractory periods.
3. **Refusal Resistance**: Tracked instances of persuasion tactics and resistance to typical guardrails.

### 2.2 Proportional Risk Fusion Model
We implemented the fusion of semantic and rule-based scores in `src/risk_fusion.py` according to:
$$\text{final\_risk} = 0.70 \times \text{semantic\_score} + 0.30 \times \text{rule\_score}$$

Risk categorization and adaptive mitigation are scaled proportionally based on the High threshold ($T$):
* **Safe Threshold**: $T \times \frac{0.40}{0.65} \approx 0.615 \times T$
* **Medium Threshold**: $T \times \frac{0.65}{0.65} = T$
* **High Threshold**: $T$

Fusing these signals results in a wider margin between attack and benign prompts, preventing false positives on benign requests while capturing subtle, multi-step attacks.

---

## 3. Threshold Sweep Analysis & Trade-offs

We executed a programmatic coarse and fine sweep across thresholds from `0.20` to `0.95` on the attacks and benign datasets.

### Sweep Results Summary Table

| Threshold | ASR | FPR | Drift Detection Rate (DDR) | Mitigation Rate | Avg Detection Turn | Avg Latency (ms) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.20 | 0.0000 | 0.6667 | 1.0000 | 0.7917 | 2.00 | 5,316.84 |
| 0.30 | 0.0000 | 0.6667 | 1.0000 | 0.7917 | 2.00 | 5,232.20 |
| 0.40 | 0.0000 | 0.6000 | 1.0000 | 0.7917 | 2.00 | 5,685.02 |
| 0.50 | 0.0000 | 0.6000 | 1.0000 | 0.7917 | 2.00 | 5,685.01 |
| 0.60 | 0.0000 | 0.5333 | 1.0000 | 0.7500 | 2.20 | 7,764.49 |
| 0.70 | 0.0000 | 0.4667 | 1.0000 | 0.6250 | 2.60 | 12,001.76 |
| 0.75 | 0.0000 | 0.3333 | 1.0000 | 0.6250 | 2.60 | 12,980.84 |
| 0.80 | 0.1000 | 0.2667 | 0.9000 | 0.5000 | 3.11 | 19,508.72 |
| 0.83 | 0.1000 | 0.0667 | 0.9000 | 0.5000 | 3.11 | 21,269.64 |
| 0.86 | 0.1000 | 0.0000 | 0.9000 | 0.5000 | 3.11 | 21,869.21 |
| 0.88 | 0.1000 | 0.0000 | 0.8000 | 0.4583 | 2.88 | 24,093.79 |
| **0.90 (Best)** | **0.1000** | **0.0000** | **0.8000** | **0.4375** | **2.88** | **25,076.45** |
| 0.93 | 0.2000 | 0.0000 | 0.8000 | 0.3542 | 3.50 | 29,580.99 |
| 0.95 | 0.2000 | 0.0000 | 0.8000 | 0.3333 | 3.62 | 30,309.16 |

### Key Findings & Trade-off Curve

* **The Low-Threshold Regime (0.20 to 0.75)**: High sensitivity ensures a 0% ASR, but causes high false positive rates (FPR up to 66.7%), making the system unusable.
* **The Transition Point (0.80 to 0.83)**: Usability improves significantly as FPR drops to 6.67% at `0.83`, while keeping ASR low at 10.0%.
* **The Optimal Trade-off Window (0.86 to 0.90)**:
  * At `0.90`, the system achieves **ASR = 10.0%** and **FPR = 0.0%** (perfect utility retention on benign prompts).
  * At `0.86`, the system achieves **ASR = 10.0%**, **FPR = 0.0%**, and a higher **DDR of 90.0%** (detecting 9 out of 10 attack sessions) with faster average latency (`21.87s`).
* **The High-Threshold Regime (> 0.90)**: ASR increases to `0.2000` as the detector fails to intercept some jailbreak attempts.

---

## 4. Visualizations

The sweep generated six high-resolution visual plots saved under `results/plots/` for analysis:
1. `threshold_vs_asr_p3.png` — Plots ASR across thresholds, demonstrating stability at `0.10` from `0.80` to `0.90`.
2. `threshold_vs_fpr_p3.png` — Shows the FPR dropping to `0.00` starting at threshold `0.86`.
3. `threshold_vs_detection_rate_p3.png` — Plots attack session detection rate (DDR) falling from `1.0` to `0.8` as thresholds increase.
4. `latency_vs_threshold_p3.png` — Measures average turn latency, showing significant reduction at lower thresholds due to early turn blocking.
5. `semantic_vs_rule_score_distribution.png` — Scatter plot mapping semantic scores against rule scores, visualizing the clear margin separating benign and attack turns.
6. `benign_vs_attack_risk_distribution.png` — Histogram illustrating final risk score distributions, highlighting the decision boundary at the chosen threshold.

---

## 5. Verdict

Based on the empirical evidence, the Phase 3 implementation has achieved all safety and utility goals:
* Primary Target ASR $\le 0.10$ (Achieved ASR = **`0.1000`**)
* Primary Target FPR $\le 0.10$ (Achieved FPR = **`0.0000`**)
* Relative improvement of **50% ASR reduction** and **100% FPR reduction** compared to Phase 2.

We present the final verdict:
$$\text{\bf Verdict: PHASE 3 FULLY COMPLETE}$$
