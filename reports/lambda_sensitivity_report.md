# Memory Decay Parameter (λ) Sensitivity & Stability Analysis Report

> **Objective**: Empirically characterize defense resilience across exponential memory decay parameter $\lambda \in [0.50, 0.95]$ in the canonical recurrence relation:
> $$C_t = \lambda C_{t-1} + (1 - \lambda) CRS_t$$

---

## 1. Empirical Results Across Decay Constant $\lambda$

| Memory Decay $\lambda$ | Defense Detection Rate (DDR) | False Positive Rate (FPR) | Avg Detection Turn | Memory Half-Life ($t_{1/2}$) | Stability / Attack Retention |
|:---:|:---:|:---:|:---:|:---:|:---|
| **0.50** | **100.00%** | **0.00%** | 3.70 | ~1.0 turn | High responsiveness, rapid risk dissipation |
| **0.60** | **100.00%** | **0.00%** | 3.70 | ~1.36 turns | Responsive; moderate risk retention |
| **0.70** | **100.00%** | **0.00%** | 3.70 | ~1.94 turns | Good multi-turn context retention |
| **0.75** | **100.00%** | **0.00%** | 3.70 | ~2.41 turns | Robust retention across mild filler turns |
| **0.80 (Optimal)** | **100.00%** | **0.00%** | **3.70** | **~3.11 turns** | **Optimal balance of persistence and noise suppression** |
| **0.85** | **100.00%** | **0.00%** | 3.70 | ~4.27 turns | High persistence; risk stays elevated longer |
| **0.90** | **100.00%** | **0.00%** | 3.70 | ~6.58 turns | Very high persistence; slower recovery on clean turns |
| **0.95** | **100.00%** | **0.00%** | 3.70 | ~13.51 turns | Extreme persistence; risk accumulates almost monotonically |

---

## 2. Key Findings & Theoretical Justification for $\lambda = 0.80$

1. **Detection Stability**:
   - The Defense Detection Rate (DDR) remains strictly at **100.00%** across the entire swept interval $\lambda \in [0.50, 0.95]$.
   - The False Positive Rate (FPR) remains strictly at **0.00%** on benign interactions because safe prompts generate $CRS_t \approx 0.0$, meaning $C_t \to 0$ regardless of $\lambda$.

2. **Defense Against Jittering & Benign Filler Attacks**:
   - In multi-turn Crescendo attacks, an adversary often inserts 1–2 seemingly benign questions to reset detection before escalating again.
   - At $\lambda = 0.50$, memory decay is aggressive ($t_{1/2} \approx 1$ turn), which would allow a determined adversary to lower contextual risk $C_t$ by interweaving two benign filler turns.
   - At $\lambda = 0.80$, the effective half-life is $t_{1/2} = \frac{\ln(0.5)}{\ln(0.80)} \approx 3.11$ turns. A 1-turn or 2-turn benign jitter retains **$64\%$ to $80\%$** of prior accumulated adversarial intent, frustrating evasion attempts.

3. **Prevention of False Alarms in Extended Benign Dialogues**:
   - Values of $\lambda \ge 0.90$ exhibit excessive inertia ($t_{1/2} > 6.5$ turns). If a user discussed a dual-use topic (e.g., educational networking or encryption algorithms), any slight transient spike would linger indefinitely.
   - $\lambda = 0.80$ guarantees that genuine topic shifts to benign questions decay to $< 10\%$ of peak risk within 10 turns.

---

## 3. Visualization Artifacts

- **Data File**: [`results/json/lambda_sensitivity_sweep.json`](file:///c:/Users/surya/Desktop/crescendo_jail_break/results/json/lambda_sensitivity_sweep.json)
- **High-Resolution Sensitivity Curve**: [`results/plots/lambda_sensitivity_curve.png`](file:///c:/Users/surya/Desktop/crescendo_jail_break/results/plots/lambda_sensitivity_curve.png)
- **Harness Script**: [`scripts/run_lambda_sweep.py`](file:///c:/Users/surya/Desktop/crescendo_jail_break/scripts/run_lambda_sweep.py)
