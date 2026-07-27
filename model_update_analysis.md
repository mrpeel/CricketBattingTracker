# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-26 16:14:31

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `Flat Data Arrays (Compressed)`
- **Kotlin File Size**: `0.2 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Shot Identification (Detection Coverage)
How many ground-truth swing shots were covered by the phone pipeline across all sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 2050 | 2050 | +0 |
| **Shots Identified (TP)** | 2050 | 2050 | +0 |
| **Missed (FN)** | 0 | 0 | +0 |
| **Detection Recall** | 100.0% | 100.0% | +0.0% |
| **Overall Classification Accuracy** | 80.7% | 80.7% | +0.0% |

> [!CAUTION]
> Classification accuracy is **training-set fit** (diagnostic only). Authoritative performance requires held-out sessions not included in training.


## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 399 | 88.0% ➔ 88.0% (0.00) ⚪ |
| DEFLECTION/GUIDE | 469 | 81.9% ➔ 81.9% (0.00) ⚪ |
| DRIVE/DEFENCE | 489 | 72.6% ➔ 72.6% (0.00) ⚪ |
| GLANCE/FLICK | 379 | 72.0% ➔ 72.0% (0.00) ⚪ |
| POWER DRIVE | 160 | 91.9% ➔ 91.9% (0.00) ⚪ |
| PULL/HOOK | 427 | 70.7% ➔ 70.7% (0.00) ⚪ |
| SLOG | 421 | 91.7% ➔ 91.7% (0.00) ⚪ |
| SWEEP | 404 | 84.9% ➔ 84.9% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## 3. Offline Classifier Performance (All 1,803 Physical Swings)
Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):

| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |
|---|---|---|---|
| CUT/PUNCH | 399 | 69.7% | 81.2% |
| DEFLECTION/GUIDE | 469 | 66.5% | 73.6% |
| DRIVE/DEFENCE | 489 | 56.2% | 65.6% |
| GLANCE/FLICK | 379 | 51.7% | 63.9% |
| POWER DRIVE | 160 | 36.2% | 87.5% |
| PULL/HOOK | 427 | 50.4% | 64.2% |
| SLOG | 421 | 69.1% | 85.5% |
| SWEEP | 404 | 68.1% | 80.9% |
| **OVERALL** | **3148** | **60.4%** | **74.1%** |

## 4. Classification Accuracy by Data Profile
The system employs a **Dual-Model Routing Architecture**: Watch-only sessions (Match Day) route to `GeneratedTopForest` (16 features), while dual-sensor sessions (Net Practice) route to `GeneratedDualForest` (30 features).

| Data Profile | Shots | Overall Acc | DRIVE | PULL | CUT | GLANCE | POWER | SLOG | SWEEP | GUIDE |
|---|---|---|---|---|---|---|---|---|---|---|
| 100hz_watch_polar | 330 | 95% | 92% | 92% | 97% | 87% | 100% | 90% | 100% | 96% |
| 50hz_watch | 1505 | 76% | 72% | 70% | 86% | 64% | 85% | 91% | 86% | 69% |
| 50hz_watch_polar | 215 | 87% | 97% | 75% | n/a | 79% | n/a | 100% | 0% | 100% |

> [!NOTE]
> These accuracy figures are **training-set fit** (diagnostic only).

## 5. Alignment Health Summary
**Sessions Processed:** 42  |  **With Polar:** 10  |  **Total Swing Shots:** 2592  |  **Polar Timestamp Refinements:** 400
**Recommended threshold: `4.00 rad/s`** (selected to maximise good/excellent recall while minimising false positives)
**Total shots missed at standard threshold (1.5 rad/s):** 15
**Recommended algorithm: `scipy peak prominence`**
## 5. Polar Timestamp Refinement Summary

*Full alignment report: [alignment_pipeline_report.md](alignment_pipeline_report.md)*

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
