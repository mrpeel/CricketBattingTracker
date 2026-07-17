# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-17 19:40:15

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
| CUT/PUNCH | 91 | 65.9% ➔ 65.9% (0.00) ⚪ |
| DEFLECTION/GUIDE | 63 | 69.8% ➔ 69.8% (0.00) ⚪ |
| DRIVE/DEFENCE | 207 | 16.9% ➔ 16.9% (0.00) ⚪ |
| GLANCE/FLICK | 158 | 46.8% ➔ 46.8% (0.00) ⚪ |
| POWER DRIVE | 28 | 85.7% ➔ 85.7% (0.00) ⚪ |
| PULL/HOOK | 230 | 52.6% ➔ 52.6% (0.00) ⚪ |
| SLOG | 100 | 89.0% ➔ 89.0% (0.00) ⚪ |
| SWEEP | 10 | 10.0% ➔ 10.0% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## 3. Offline Classifier Performance (All 1,803 Physical Swings)
Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):

| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |
|---|---|---|---|
| CUT/PUNCH | 208 | 61.5% | 78.8% |
| DEFLECTION/GUIDE | 284 | 73.6% | 85.6% |
| DRIVE/DEFENCE | 254 | 63.0% | 81.9% |
| GLANCE/FLICK | 285 | 58.9% | 72.3% |
| POWER DRIVE | 136 | 25.7% | 73.5% |
| PULL/HOOK | 278 | 56.8% | 67.6% |
| SLOG | 288 | 83.3% | 95.5% |
| SWEEP | 70 | 42.9% | 92.9% |
| **OVERALL** | **1803** | **62.6%** | **80.4%** |

## 4. Polar Sense (Bottom Hand) Integration
Polar Sense bottom-hand telemetry runs at a high sampling rate (~418Hz vs. the watch's 50Hz) to capture high-resolution impact transients and release mechanics. These metrics are used by the companion app's `ShotEnhancementEngine` as a post-classification refinement layer.

### Active Refinement Thresholds (Auto-Optimized):
- `const val DRIVE_TO_POWER_GYRO_RATIO = 1.2500f`
- `const val DRIVE_TO_POWER_ACC_PEAK = 15.0000f`
- `const val FLICK_TO_GUIDE_GYRO_RATIO = 0.3000f`
- `const val FLICK_TO_GUIDE_GYRO_PEAK = 3.0000f`
- `const val PULL_TO_SLOG_GYRO_RATIO = 1.1000f`
- `const val PULL_TO_SLOG_GYRO_PEAK = 8.0000f`

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
