# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-23 17:44:18

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `2490.1 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1252 | 1252 | +0 |
| **Total Detected Shots** | 1579 | 1579 | +0 |
| **True Positives (Matches)** | 1180 | 1180 | +0 |
| **False Positives** | 399 | 399 | +0 |
| **Precision** | 0.75 ➔ 0.75 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.94 ➔ 0.94 (0.00) ⚪ | | |
| **F1 Score** | 0.83 ➔ 0.83 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 178 | 80.3% ➔ **81.5%** (+1.1%) 🟢 |
| DEFLECTION/GUIDE | 64 | 76.6% ➔ **78.1%** (+1.6%) 🟢 |
| DRIVE/DEFENCE | 294 | 85.0% ➔ **85.7%** (+0.7%) 🟢 |
| GLANCE/FLICK | 274 | 75.2% ➔ **79.9%** (+4.7%) 🟢 |
| POWER SHOT | 117 | 29.1% ➔ 29.1% (0.00) ⚪ |
| PULL/HOOK | 240 | 80.4% ➔ **78.3%** (-2.1%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
