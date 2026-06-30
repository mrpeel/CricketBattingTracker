# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-30 18:51:12

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `3192.7 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1521 | 1521 | +0 |
| **Total Detected Shots** | 2029 | 2029 | +0 |
| **True Positives (Matches)** | 1221 | 1221 | +0 |
| **False Positives** | 808 | 808 | +0 |
| **Precision** | 0.60 ➔ 0.60 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.80 ➔ 0.80 (0.00) ⚪ | | |
| **F1 Score** | 0.69 ➔ 0.69 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 134 | 81.3% ➔ **78.4%** (-3.0%) 🔴 |
| DEFLECTION/GUIDE | 62 | 85.5% ➔ **74.2%** (-11.3%) 🔴 |
| DRIVE/DEFENCE | 339 | 81.7% ➔ 81.4% (0.00) ⚪ |
| GLANCE/FLICK | 194 | 68.0% ➔ **70.6%** (+2.6%) 🟢 |
| POWER DRIVE | 99 | 46.5% ➔ **48.5%** (+2.0%) 🟢 |
| PULL/HOOK | 188 | 79.3% ➔ **78.7%** (-0.5%) 🔴 |
| SLOG | 54 | 46.3% ➔ **40.7%** (-5.6%) 🔴 |
| SWEEP | 138 | 82.6% ➔ **81.2%** (-1.4%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
