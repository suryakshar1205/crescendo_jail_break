# Phase 7: Dynamic Threshold Calibration & Alignment Report

This report evaluates the utility-security trade-off using Turn 1 Dynamic Threshold Calibration.

## Calibration Statistics Summary

* **Total evaluated sessions**: `4`
* **Total evaluated turns**: `6`
* **Base (Static) Threshold**: `0.92`

### Average Calibrated Thresholds by Domain

| Domain | Classified Sessions | Average Calibrated Threshold | Offset |
| --- | --- | --- | --- |
| programming | 1 | `0.9500` | `+0.03` |
| creative_writing | 1 | `0.9000` | `-0.02` |
| academic_research | 1 | `0.9200` | `+0.00` |
| general | 1 | `0.9200` | `+0.00` |

## Utility & Security Comparison

| Metric | Static Thresholding | Dynamic (Turn 1 Calibrated) |
| --- | --- | --- |
| Blocked Turns | `3` | `3` |
| Block Rate % | `50.00%` | `50.00%` |

## Interpretation
- **Programming**: Higher threshold (0.95) decreases False Positive Rate (FPR), ensuring safe code generation queries are not prematurely blocked.
- **Creative Writing**: Lower threshold (0.90) increases safety margin against adversarial roleplay attacks (ASR reduction).
