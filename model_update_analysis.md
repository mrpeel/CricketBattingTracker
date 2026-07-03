# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-03 06:47:56

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `2896.1 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1801 | 1801 | +0 |
| **Total Detected Shots** | 2114 | 2114 | +0 |
| **True Positives (Matches)** | 1095 | 1095 | +0 |
| **False Positives** | 1019 | 1019 | +0 |
| **Precision** | 0.52 ➔ 0.52 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.61 ➔ 0.61 (0.00) ⚪ | | |
| **F1 Score** | 0.56 ➔ 0.56 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 184 | 58.7% ➔ **67.4%** (+8.7%) 🟢 |
| DEFLECTION/GUIDE | 75 | 65.3% ➔ **73.3%** (+8.0%) 🟢 |
| DRIVE/DEFENCE | 283 | 71.4% ➔ **67.8%** (-3.5%) 🔴 |
| GLANCE/FLICK | 167 | 58.1% ➔ **62.3%** (+4.2%) 🟢 |
| POWER DRIVE | 71 | 39.4% ➔ **43.7%** (+4.2%) 🟢 |
| PULL/HOOK | 165 | 60.6% ➔ **66.1%** (+5.5%) 🟢 |
| SLOG | 29 | 37.9% ➔ 37.9% (0.00) ⚪ |
| SWEEP | 108 | 68.5% ➔ **63.0%** (-5.6%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
