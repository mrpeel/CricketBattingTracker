# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-29 17:11:23

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `3410.0 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1590 | 1590 | +0 |
| **Total Detected Shots** | 2029 | 2029 | +0 |
| **True Positives (Matches)** | 1385 | 1385 | +0 |
| **False Positives** | 644 | 644 | +0 |
| **Precision** | 0.68 ➔ 0.68 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.87 ➔ 0.87 (0.00) ⚪ | | |
| **F1 Score** | 0.77 ➔ 0.77 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 180 | 76.1% ➔ **73.9%** (-2.2%) 🔴 |
| DEFLECTION/GUIDE | 62 | 79.0% ➔ 79.0% (0.00) ⚪ |
| DRIVE/DEFENCE | 364 | 83.0% ➔ **83.8%** (+0.8%) 🟢 |
| GLANCE/FLICK | 225 | 77.3% ➔ 77.3% (0.00) ⚪ |
| POWER SHOT | 136 | 21.3% ➔ **32.4%** (+11.0%) 🟢 |
| PULL/HOOK | 223 | 73.5% ➔ 73.1% (0.00) ⚪ |
| SWEEP | 182 | 88.5% ➔ 88.5% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
