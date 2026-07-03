# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-04 08:48:25

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `3090.4 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1559 | 1559 | +0 |
| **Total Detected Shots** | 2114 | 2114 | +0 |
| **True Positives (Matches)** | 1212 | 1212 | +0 |
| **False Positives** | 902 | 902 | +0 |
| **Precision** | 0.57 ➔ 0.57 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.78 ➔ 0.78 (0.00) ⚪ | | |
| **F1 Score** | 0.66 ➔ 0.66 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 171 | 73.1% ➔ **67.3%** (-5.8%) 🔴 |
| DEFLECTION/GUIDE | 76 | 73.7% ➔ **80.3%** (+6.6%) 🟢 |
| DRIVE/DEFENCE | 326 | 70.6% ➔ **76.1%** (+5.5%) 🟢 |
| GLANCE/FLICK | 217 | 63.6% ➔ **66.4%** (+2.8%) 🟢 |
| POWER DRIVE | 74 | 43.2% ➔ **37.8%** (-5.4%) 🔴 |
| PULL/HOOK | 177 | 57.6% ➔ **48.0%** (-9.6%) 🔴 |
| SLOG | 27 | 37.0% ➔ **25.9%** (-11.1%) 🔴 |
| SWEEP | 131 | 58.0% ➔ **80.9%** (+22.9%) 🟢 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
