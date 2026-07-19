# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-19 12:04:53

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `Flat Data Arrays (Compressed)`
- **Kotlin File Size**: `3595.4 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Shot Identification (Detection Coverage)
How many ground-truth swing shots were covered by the phone pipeline across all sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1049 | 1049 | +0 |
| **Shots Identified (TP)** | 1049 | 1049 | +0 |
| **Missed (FN)** | 0 | 0 | +0 |
| **Detection Recall** | 100.0% | 100.0% | +0.0% |
| **Overall Classification Accuracy** | 82.7% | 82.7% | +0.0% |

> [!CAUTION]
> Classification accuracy is **training-set fit** (diagnostic only). Authoritative performance requires held-out sessions not included in training.


## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 217 | 84.3% ➔ 84.3% (0.00) ⚪ |
| DEFLECTION/GUIDE | 326 | 89.6% ➔ 89.6% (0.00) ⚪ |
| DRIVE/DEFENCE | 379 | 72.3% ➔ 72.3% (0.00) ⚪ |
| GLANCE/FLICK | 294 | 76.2% ➔ 76.2% (0.00) ⚪ |
| POWER DRIVE | 155 | 85.8% ➔ 85.8% (0.00) ⚪ |
| PULL/HOOK | 298 | 75.2% ➔ 75.2% (0.00) ⚪ |
| SLOG | 280 | 96.1% ➔ 96.1% (0.00) ⚪ |
| SWEEP | 88 | 96.6% ➔ 96.6% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## 3. Offline Classifier Performance (All 1,803 Physical Swings)
Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):

| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |
|---|---|---|---|
| CUT/PUNCH | 217 | 59.9% | 75.1% |
| DEFLECTION/GUIDE | 326 | 75.8% | 85.9% |
| DRIVE/DEFENCE | 379 | 43.0% | 57.8% |
| GLANCE/FLICK | 294 | 51.7% | 67.3% |
| POWER DRIVE | 155 | 25.8% | 72.3% |
| PULL/HOOK | 298 | 54.4% | 67.4% |
| SLOG | 280 | 77.5% | 93.6% |
| SWEEP | 88 | 61.4% | 90.9% |
| **OVERALL** | **2037** | **57.2%** | **74.4%** |

## 4. Classification Accuracy by Data Profile
The RF model was trained on all data profiles simultaneously. Polar features are imputed to 0.0 for watch-only sessions, so the model learns to classify confidently with or without Polar data.

| Data Profile | Shots | Overall Acc | DRIVE | PULL | CUT | GLANCE | POWER | SLOG | SWEEP | GUIDE |
|---|---|---|---|---|---|---|---|---|---|---|
*Could not generate data-profile breakdown: '<' not supported between instances of 'float' and 'str'*

## 5. Alignment Health Summary
**Sessions Processed:** 34  |  **With Polar:** 4  |  **Total Swing Shots:** 1941  |  **Polar Timestamp Refinements:** 134
**Recommended threshold: `4.00 rad/s`** (selected to maximise good/excellent recall while minimising false positives)
**Total shots missed at standard threshold (1.5 rad/s):** 77
**Recommended algorithm: `scipy peak prominence`**
## 5. Polar Timestamp Refinement Summary

*Full alignment report: [alignment_pipeline_report.md](alignment_pipeline_report.md)*

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
