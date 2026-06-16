# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-16 18:42:51

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 100, 'max_depth': 7}`
- **Kotlin File Size**: `721.6 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 924 | 924 | +0 |
| **Total Detected Shots** | 1137 | 1137 | +0 |
| **True Positives (Matches)** | 866 | 866 | +0 |
| **False Positives** | 271 | 271 | +0 |
| **Precision** | 0.76 ➔ 0.76 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.94 ➔ 0.94 (0.00) ⚪ | | |
| **F1 Score** | 0.84 ➔ 0.84 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 69 | 75.4% ➔ 75.4% (0.00) ⚪ |
| DEFLECTION/GUIDE | 5 | 20.0% ➔ 20.0% (0.00) ⚪ |
| DRIVE/DEFENCE | 257 | 85.6% ➔ 85.6% (0.00) ⚪ |
| GLANCE/FLICK | 230 | 71.7% ➔ 71.7% (0.00) ⚪ |
| POWER SHOT | 117 | 29.9% ➔ 29.9% (0.00) ⚪ |
| PULL/HOOK | 175 | 80.6% ➔ 80.6% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
