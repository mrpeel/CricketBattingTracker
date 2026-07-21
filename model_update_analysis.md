# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-21 18:03:46

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `Flat Data Arrays (Compressed)`
- **Kotlin File Size**: `0.2 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Shot Identification (Detection Coverage)
How many ground-truth swing shots were covered by the phone pipeline across all sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1385 | 1385 | +0 |
| **Shots Identified (TP)** | 1385 | 1385 | +0 |
| **Missed (FN)** | 0 | 0 | +0 |
| **Detection Recall** | 100.0% | 100.0% | +0.0% |
| **Overall Classification Accuracy** | 80.2% | 80.2% | +0.0% |

> [!CAUTION]
> Classification accuracy is **training-set fit** (diagnostic only). Authoritative performance requires held-out sessions not included in training.


## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 423 | 87.0% ➔ 87.0% (0.00) ⚪ |
| DEFLECTION/GUIDE | 428 | 76.2% ➔ 76.2% (0.00) ⚪ |
| DRIVE/DEFENCE | 488 | 75.4% ➔ 75.4% (0.00) ⚪ |
| GLANCE/FLICK | 433 | 77.6% ➔ 77.6% (0.00) ⚪ |
| POWER DRIVE | 140 | 85.7% ➔ 85.7% (0.00) ⚪ |
| PULL/HOOK | 401 | 67.1% ➔ 67.1% (0.00) ⚪ |
| SLOG | 330 | 94.2% ➔ 94.2% (0.00) ⚪ |
| SWEEP | 114 | 98.2% ➔ 98.2% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## 3. Offline Classifier Performance (All 1,803 Physical Swings)
Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):

| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |
|---|---|---|---|
| CUT/PUNCH | 423 | 68.6% | 83.0% |
| DEFLECTION/GUIDE | 428 | 57.9% | 69.9% |
| DRIVE/DEFENCE | 488 | 61.9% | 69.1% |
| GLANCE/FLICK | 433 | 57.3% | 70.9% |
| POWER DRIVE | 140 | 28.6% | 75.0% |
| PULL/HOOK | 401 | 53.4% | 62.8% |
| SLOG | 330 | 75.2% | 89.4% |
| SWEEP | 114 | 58.8% | 96.5% |
| **OVERALL** | **2757** | **60.1%** | **74.6%** |

## 4. Classification Accuracy by Data Profile
The system employs a **Dual-Model Routing Architecture**: Watch-only sessions (Match Day) route to `GeneratedTopForest` (14 features), while dual-sensor sessions (Net Practice) route to `GeneratedDualForest` (26 features).

| Data Profile | Shots | Overall Acc | DRIVE | PULL | CUT | GLANCE | POWER | SLOG | SWEEP | GUIDE |
|---|---|---|---|---|---|---|---|---|---|---|
| 100hz_watch_polar | 148 | 94% | 90% | 94% | 100% | 93% | 100% | 100% | 100% | 91% |
| 50hz_watch | 1090 | 76% | 75% | 68% | 88% | 67% | 81% | 94% | 100% | 69% |
| 50hz_watch_polar | 147 | 78% | 89% | 70% | n/a | 65% | n/a | 95% | n/a | n/a |

> [!NOTE]
> These accuracy figures are **training-set fit** (diagnostic only).

## 5. Alignment Health Summary
**Sessions Processed:** 38  |  **With Polar:** 4  |  **Total Swing Shots:** 2238  |  **Polar Timestamp Refinements:** 145
**Recommended threshold: `4.00 rad/s`** (selected to maximise good/excellent recall while minimising false positives)
**Total shots missed at standard threshold (1.5 rad/s):** 66
**Recommended algorithm: `scipy peak prominence`**
## 5. Polar Timestamp Refinement Summary

*Full alignment report: [alignment_pipeline_report.md](alignment_pipeline_report.md)*

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
