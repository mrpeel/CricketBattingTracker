# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-27 15:04:09

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 100, 'max_depth': 7}`
- **Kotlin File Size**: `924.0 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1441 | 1441 | +0 |
| **Total Detected Shots** | 1850 | 1850 | +0 |
| **True Positives (Matches)** | 1324 | 1324 | +0 |
| **False Positives** | 526 | 526 | +0 |
| **Precision** | 0.72 ➔ 0.72 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.92 ➔ 0.92 (0.00) ⚪ | | |
| **F1 Score** | 0.80 ➔ 0.80 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 187 | 76.5% ➔ 76.5% (0.00) ⚪ |
| DEFLECTION/GUIDE | 64 | 85.9% ➔ **71.9%** (-14.1%) 🔴 |
| DRIVE/DEFENCE | 340 | 82.4% ➔ **83.2%** (+0.9%) 🟢 |
| GLANCE/FLICK/SWEEP | 362 | 1.7% ➔ **75.1%** (+73.5%) 🟢 |
| POWER SHOT | 117 | 28.2% ➔ **30.8%** (+2.6%) 🟢 |
| PULL/HOOK | 241 | 80.5% ➔ **78.4%** (-2.1%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
