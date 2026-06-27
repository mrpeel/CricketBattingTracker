# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-26 16:25:42

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `{'n_estimators': 100, 'max_depth': 7}`
- **Kotlin File Size**: `914.6 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Facing Up / Shot Detection Performance
Below are the overall shot detection metrics aggregated across all active watch sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1384 | 1384 | +0 |
| **Total Detected Shots** | 1772 | 1772 | +0 |
| **True Positives (Matches)** | 1302 | 1302 | +0 |
| **False Positives** | 470 | 470 | +0 |
| **Precision** | 0.73 ➔ 0.73 (0.00) ⚪ | | |
| **Recall (Accuracy)** | 0.94 ➔ 0.94 (0.00) ⚪ | | |
| **F1 Score** | 0.83 ➔ 0.83 (0.00) ⚪ | | |

## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 194 | 79.4% ➔ 79.4% (0.00) ⚪ |
| DEFLECTION/GUIDE | 64 | 84.4% ➔ **85.9%** (+1.6%) 🟢 |
| DRIVE/DEFENCE | 358 | 81.8% ➔ **84.6%** (+2.8%) 🟢 |
| GLANCE/FLICK | 315 | 73.0% ➔ **74.6%** (+1.6%) 🟢 |
| POWER SHOT | 117 | 29.9% ➔ **28.2%** (-1.7%) 🔴 |
| PULL/HOOK | 241 | 79.3% ➔ **80.5%** (+1.2%) 🟢 |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
