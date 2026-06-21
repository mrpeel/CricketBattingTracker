# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-21 16:45:18

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 100, 'max_depth': 7}`
- **Kotlin File Size**: `862.9 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1124 | 1124 | +0 |
| **Total Detected Shots** | 1398 | 1398 | +0 |
| **True Positives (Matches)** | 1056 | 1056 | +0 |
| **False Positives** | 342 | 342 | +0 |
| **Precision** | 0.76 ➔ 0.76 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.94 ➔ 0.94 (0.00) ⚪ | | |
| **F1 Score** | 0.84 ➔ 0.84 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 144 | 81.9% ➔ 81.9% (0.00) ⚪ |
| DEFLECTION/GUIDE | 52 | 75.0% ➔ **80.8%** (+5.8%) 🟢 |
| DRIVE/DEFENCE | 261 | 85.4% ➔ 85.1% (0.00) ⚪ |
| GLANCE/FLICK | 245 | 73.1% ➔ **74.7%** (+1.6%) 🟢 |
| POWER SHOT | 117 | 29.9% ➔ **26.5%** (-3.4%) 🔴 |
| PULL/HOOK | 224 | 81.7% ➔ **79.5%** (-2.2%) 🔴 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
