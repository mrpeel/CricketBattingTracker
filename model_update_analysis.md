# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-04 19:42:51

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `2894.6 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1518 | 1518 | +0 |
| **Total Detected Shots** | 2125 | 2125 | +0 |
| **True Positives (Matches)** | 1047 | 1047 | +0 |
| **False Positives** | 1078 | 1078 | +0 |
| **Precision** | 0.49 ➔ 0.49 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.69 ➔ 0.69 (0.00) ⚪ | | |
| **F1 Score** | 0.57 ➔ 0.57 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 108 | 39.8% ➔ **46.3%** (+6.5%) 🟢 |
| DEFLECTION/GUIDE | 39 | 48.7% ➔ **43.6%** (-5.1%) 🔴 |
| DRIVE/DEFENCE | 292 | 65.8% ➔ **64.0%** (-1.7%) 🔴 |
| GLANCE/FLICK | 215 | 60.9% ➔ **53.5%** (-7.4%) 🔴 |
| POWER DRIVE | 26 | 38.5% ➔ **46.2%** (+7.7%) 🟢 |
| PULL/HOOK | 203 | 36.0% ➔ **53.2%** (+17.2%) 🟢 |
| SLOG | 72 | 25.0% ➔ **52.8%** (+27.8%) 🟢 |
| SWEEP | 79 | 73.4% ➔ **70.9%** (-2.5%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
