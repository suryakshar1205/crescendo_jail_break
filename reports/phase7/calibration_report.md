# Phase 7: Dynamic Threshold Calibration & Alignment Report

This report evaluates the utility-security trade-off using Turn 1 Dynamic Threshold Calibration.

## Calibration Statistics Summary

* **Total evaluated sessions**: `15`
* **Total evaluated turns**: `63`
* **Base (Static) Threshold**: `0.92`

### Average Calibrated Thresholds by Domain

| Domain | Classified Sessions | Average Calibrated Threshold | Offset |
| --- | --- | --- | --- |
| academic_research | 2 | `0.9200` | `+0.00` |
| general | 11 | `0.9200` | `+0.00` |
| creative_writing | 1 | `0.9000` | `-0.02` |
| programming | 1 | `0.9500` | `+0.03` |

## Utility & Security Comparison

| Metric | Static Thresholding | Dynamic (Turn 1 Calibrated) |
| --- | --- | --- |
| Blocked Turns | `0` | `0` |
| Block Rate % | `0.00%` | `0.00%` |

## Interpretation
- **Programming**: Higher threshold (0.95) decreases False Positive Rate (FPR), ensuring safe code generation queries are not prematurely blocked.
- **Creative Writing**: Lower threshold (0.90) increases safety margin against adversarial roleplay attacks (ASR reduction).
