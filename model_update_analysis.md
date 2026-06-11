# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-12 05:53:26

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 534 | 534 | +0 |
| **Total Detected Shots** | 625 | 625 | +0 |
| **True Positives (Matches)** | 499 | 499 | +0 |
| **False Positives** | 126 | 126 | +0 |
| **Precision** | 0.80 ➔ 0.80 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.93 ➔ 0.93 (0.00) ⚪ | | |
| **F1 Score** | 0.86 ➔ 0.86 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 30 | 76.7% ➔ **73.3%** (-3.3%) 🔴 |
| DEFLECTION/GUIDE | 5 | 0.0% ➔ 0.0% (0.00) ⚪ |
| DRIVE/DEFENCE | 208 | 87.5% ➔ **86.5%** (-1.0%) 🔴 |
| GLANCE/FLICK | 155 | 79.4% ➔ **80.6%** (+1.3%) 🟢 |
| POWER SHOT | 19 | 47.4% ➔ **57.9%** (+10.5%) 🟢 |
| PULL/HOOK | 69 | 62.3% ➔ **60.9%** (-1.4%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
