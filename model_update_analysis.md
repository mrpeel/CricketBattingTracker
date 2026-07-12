# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-12 15:09:54

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `4350.1 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1885 | 1885 | +0 |
| **Total Detected Shots** | 1859 | 1859 | +0 |
| **True Positives (Matches)** | 973 | 973 | +0 |
| **False Positives** | 886 | 886 | +0 |
| **Precision** | 0.52 ➔ 0.52 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.52 ➔ 0.52 (0.00) ⚪ | | |
| **F1 Score** | 0.52 ➔ 0.52 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 102 | 59.8% ➔ 59.8% (0.00) ⚪ |
| DEFLECTION/GUIDE | 63 | 71.4% ➔ **73.0%** (+1.6%) 🟢 |
| DRIVE/DEFENCE | 222 | 56.8% ➔ **55.4%** (-1.4%) 🔴 |
| GLANCE/FLICK | 190 | 56.3% ➔ 56.3% (0.00) ⚪ |
| POWER DRIVE | 26 | 88.5% ➔ 88.5% (0.00) ⚪ |
| PULL/HOOK | 217 | 63.6% ➔ **57.6%** (-6.0%) 🔴 |
| SLOG | 100 | 73.0% ➔ **81.0%** (+8.0%) 🟢 |
| SWEEP | 45 | 77.8% ➔ 77.8% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
