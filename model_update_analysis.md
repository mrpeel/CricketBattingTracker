# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-17 19:25:59

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 100, 'max_depth': 7}`
- **Kotlin File Size**: `1266.9 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1925 | 1925 | +0 |
| **Total Detected Shots** | 1991 | 1991 | +0 |
| **True Positives (Matches)** | 895 | 895 | +0 |
| **False Positives** | 1096 | 1096 | +0 |
| **Precision** | 0.45 ➔ 0.45 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.46 ➔ 0.46 (0.00) ⚪ | | |
| **F1 Score** | 0.46 ➔ 0.46 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 91 | 64.8% ➔ **65.9%** (+1.1%) 🟢 |
| DEFLECTION/GUIDE | 63 | 73.0% ➔ **69.8%** (-3.2%) 🔴 |
| DRIVE/DEFENCE | 207 | 21.7% ➔ **16.9%** (-4.8%) 🔴 |
| GLANCE/FLICK | 158 | 46.8% ➔ 46.8% (0.00) ⚪ |
| POWER DRIVE | 28 | 85.7% ➔ 85.7% (0.00) ⚪ |
| PULL/HOOK | 230 | 53.9% ➔ **52.6%** (-1.3%) 🔴 |
| SLOG | 100 | 92.0% ➔ **89.0%** (-3.0%) 🔴 |
| SWEEP | 10 | 30.0% ➔ **10.0%** (-20.0%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
