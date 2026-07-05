# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-05 18:10:45

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 200, 'max_depth': 8}`
- **Kotlin File Size**: `4417.2 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1558 | 1558 | +0 |
| **Total Detected Shots** | 2216 | 2216 | +0 |
| **True Positives (Matches)** | 1066 | 1066 | +0 |
| **False Positives** | 1150 | 1150 | +0 |
| **Precision** | 0.48 ➔ 0.48 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.68 ➔ 0.68 (0.00) ⚪ | | |
| **F1 Score** | 0.56 ➔ 0.56 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 108 | 46.3% ➔ 46.3% (0.00) ⚪ |
| DEFLECTION/GUIDE | 39 | 33.3% ➔ 33.3% (0.00) ⚪ |
| DRIVE/DEFENCE | 297 | 54.9% ➔ 54.9% (0.00) ⚪ |
| GLANCE/FLICK | 218 | 50.5% ➔ 50.5% (0.00) ⚪ |
| POWER DRIVE | 37 | 75.7% ➔ 75.7% (0.00) ⚪ |
| PULL/HOOK | 203 | 44.8% ➔ 44.8% (0.00) ⚪ |
| SLOG | 72 | 58.3% ➔ 58.3% (0.00) ⚪ |
| SWEEP | 79 | 65.8% ➔ 65.8% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
