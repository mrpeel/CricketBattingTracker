# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-12 07:57:46

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 591 | 591 | +0 |
| **Total Detected Shots** | 712 | 712 | +0 |
| **True Positives (Matches)** | 555 | 555 | +0 |
| **False Positives** | 157 | 157 | +0 |
| **Precision** | 0.78 ➔ 0.78 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.94 ➔ 0.94 (0.00) ⚪ | | |
| **F1 Score** | 0.85 ➔ 0.85 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 68 | 55.9% ➔ **77.9%** (+22.1%) 🟢 |
| DEFLECTION/GUIDE | 5 | 0.0% ➔ 0.0% (0.00) ⚪ |
| DRIVE/DEFENCE | 223 | 87.0% ➔ 86.5% (0.00) ⚪ |
| GLANCE/FLICK | 155 | 80.6% ➔ **74.2%** (-6.5%) 🔴 |
| POWER SHOT | 19 | 57.9% ➔ **47.4%** (-10.5%) 🔴 |
| PULL/HOOK | 72 | 59.7% ➔ **62.5%** (+2.8%) 🟢 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
