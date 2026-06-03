# Phase 2 — Refinement Report: Semantic Drift Detection for Crescendo Defense

This report details the implementation, sweep analysis, and final recommendation for the Phase 2 Crescendo jailbreak defense system. 

---

## 1. Executive Summary

Our goal in Phase 2 was to implement an embedding-based **Semantic Drift Detector** to mitigate multi-turn Crescendo attacks while keeping usability degradation (False Positive Rate, or FPR) to a minimum. 

By replacing the naive "consecutive-turn" drift score with **Anchor-Based Semantic Drift** (comparing turns against the initial prompt anchor) combined with local drift and escalation velocity, we achieved:
* **Selected Optimal Threshold**: `0.75`
* **Attack Success Rate (ASR)**: **`0.2000`** (a **50% relative reduction** compared to the baseline ASR of `0.4000`).
* **False Positive Rate (FPR)**: **`0.0667`** (significantly beating the success criteria limit of $\le 0.10$).
* **Drift Detection Rate (DDR)**: **`0.8000`** (8 out of 10 attack sessions successfully intercepted).
* **Average Latency**: **`29.87s`** per turn (a **34% reduction** compared to baseline `45.54s` due to early termination of blocked sessions).

---

## 2. Detection Strategy & Architecture

The detector utilizes a multi-signal scoring system implemented in `src/embedding_detector.py` that computes a combined risk score for each turn:

1. **Anchor Drift (Weight: 0.60)**:
   Measures semantic distance between the current turn's prompt $P_t$ and the very first prompt $P_1$ (the "anchor"):
   $$\text{Anchor Drift} = 1 - \cos(\text{Emb}(P_t), \text{Emb}(P_1))$$
   *Rationale*: In Crescendo attacks, the attacker starts with a benign topic ($P_1$) and drifts toward the harmful target. Comparing the current turn against the anchor detects this drift.

2. **Local Drift (Weight: 0.25)**:
   Measures semantic distance between consecutive turns in a sliding window (default size 3):
   $$\text{Local Drift} = 1 - \cos(\text{Emb}(P_t), \text{Emb}(P_{t-1}))$$
   *Rationale*: Standard conversational flow changes slowly. Sudden local jumps indicate abrupt pivots.

3. **Escalation Velocity (Weight: 0.15)**:
   Measures the rate of change of the drift score:
   $$\text{Velocity} = \text{Anchor Drift}_t - \text{Anchor Drift}_{t-1}$$
   *Rationale*: Accelerating drift points to a rapid escalation toward the target payload.

The final **Risk Score** is computed as:
$$\text{Risk Score} = 0.60 \times \text{Anchor Drift} + 0.25 \times \text{Local Drift} + 0.15 \times \max(0, \text{Velocity})$$

If the $\text{Risk Score}$ exceeds the selected **Threshold**, the detector flags the session, replaces the assistant's response with a soft refusal, and halts further model calls in that session.

---

## 3. Threshold Sweep Analysis & Trade-offs

We conducted a programmatic coarse and fine sweep across thresholds from `0.20` to `0.88`.

### Sweep Results Summary Table

| Threshold | ASR | FPR | Drift Detection Rate (DDR) | Avg Detection Turn | Avg Latency (ms) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0.20 | 0.0000 | 0.6667 | 1.0000 | 2.00 | 5,344.95 |
| 0.30 | 0.0000 | 0.6667 | 1.0000 | 2.00 | 5,231.81 |
| 0.40 | 0.0000 | 0.6000 | 1.0000 | 2.00 | 5,684.67 |
| 0.50 | 0.0000 | 0.6000 | 1.0000 | 2.00 | 6,322.26 |
| 0.60 | 0.1000 | 0.4667 | 0.9000 | 2.44 | 16,506.59 |
| 0.70 | 0.2000 | 0.2667 | 0.8000 | 3.25 | 25,683.43 |
| 0.72 | 0.2000 | 0.0667 | 0.8000 | 3.50 | 29,140.94 |
| **0.75 (Best)** | **0.2000** | **0.0667** | **0.8000** | **3.62** | **29,869.15** |
| 0.78 | 0.4000 | 0.0000 | 0.5000 | 3.60 | 37,047.74 |
| 0.80 | 0.5000 | 0.0000 | 0.4000 | 3.50 | 38,234.19 |
| 0.85 | 0.5000 | 0.0000 | 0.4000 | 3.50 | 39,084.65 |
| 0.88 | 0.4000 | 0.0000 | 0.3000 | 3.67 | 41,712.60 |

### Key Findings & Trade-off Curve

* **The Low-Threshold Regime (0.20 to 0.50)**: While achieving perfect defense (ASR = 0.00), these thresholds are too sensitive, flagging a high percentage of benign turns (FPR $\ge 0.60$).
* **The Transition Point (0.60 to 0.70)**: Usability improves significantly as FPR drops, while defense remains highly effective (ASR = 0.10 - 0.20).
* **The Optimal Trade-off Window (0.72 to 0.75)**: 
  * At `0.75`, we maintain the lowest ASR (`0.2000`) before safety degradation begins.
  * Concurrently, the FPR is extremely low (`0.0667` / `6.67%`), which is well below the target budget of `10%`.
* **The High-Threshold Regime (> 0.75)**: Usability is perfect (FPR = 0.00), but detection fails to intercept malicious escalation, allowing ASR to drift back to the baseline level of `0.40` or higher.

---

## 4. Visualizations

The sweep generated five visual plots saved under `results/plots/` for review:
1. `threshold_vs_asr.png` — Highlights the sudden rise in attack success once the threshold exceeds `0.75`.
2. `threshold_vs_fpr.png` — Shows the exponential drop in false positives, hitting the acceptable budget at `0.72`.
3. `threshold_vs_detection_rate.png` — Plots the drift detection rate (DDR) falling from `1.0` down to `0.3` as thresholds relax.
4. `risk_score_distribution.png` — Displays the histogram of benign vs. attack risk scores, showing strong separability.
5. `anchor_drift_distribution.png` — Confirms that anchor drift alone provides the largest margin of difference between attack and benign prompts.

---

## 5. Implementation Verification

* **Resuming and Caching**: The benchmark harness was modified to run with zero-overhead resume capabilities. It stores evaluated thresholds in `results/phase2/sweep_results.json` and caches new model outputs under `results/json/phase2_inference_cache.json`. This makes the evaluation process extremely reproducible and robust.
* **Low-Memory footprint**: The environment runs within a 16 GB memory boundary by explicitly mapping TensorFlow imports to `None`, avoiding Hugging Face memory leaks.

---

## 6. Recommendations & Next Steps

1. **Adopt Threshold 0.75**: We recommend deploying the detector with a threshold of **0.75** for the current SentenceTransformer encoder (`all-MiniLM-L6-v2`).
2. **Phase 3 Preparation**: In the next phase (mitigation optimization), we can explore soft refusals that dynamically adapt their wording based on the risk score magnitude rather than returning a static warning message.
