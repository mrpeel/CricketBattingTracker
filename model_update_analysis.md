# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-13 12:10:11

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 731 | 731 | +0 |
| **Total Detected Shots** | 876 | 876 | +0 |
| **True Positives (Matches)** | 691 | 691 | +0 |
| **False Positives** | 185 | 185 | +0 |
| **Precision** | 0.79 ➔ 0.79 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.95 ➔ 0.95 (0.00) ⚪ | | |
| **F1 Score** | 0.86 ➔ 0.86 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 69 | 75.4% ➔ **76.8%** (+1.4%) 🟢 |
| DEFLECTION/GUIDE | 5 | 0.0% ➔ 0.0% (0.00) ⚪ |
| DRIVE/DEFENCE | 241 | 87.1% ➔ 87.6% (0.00) ⚪ |
| GLANCE/FLICK | 176 | 72.7% ➔ **73.9%** (+1.1%) 🟢 |
| POWER SHOT | 19 | 36.8% ➔ **26.3%** (-10.5%) 🔴 |
| PULL/HOOK | 168 | 77.4% ➔ **83.9%** (+6.5%) 🟢 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
