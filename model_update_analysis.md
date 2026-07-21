# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-21 17:37:09

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `Flat Data Arrays (Compressed)`
- **Kotlin File Size**: `0.2 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Shot Identification (Detection Coverage)
How many ground-truth swing shots were covered by the phone pipeline across all sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1305 | 1305 | +0 |
| **Shots Identified (TP)** | 1305 | 1305 | +0 |
| **Missed (FN)** | 0 | 0 | +0 |
| **Detection Recall** | 100.0% | 100.0% | +0.0% |
| **Overall Classification Accuracy** | 80.2% | 80.2% | +0.0% |

> [!CAUTION]
> Classification accuracy is **training-set fit** (diagnostic only). Authoritative performance requires held-out sessions not included in training.


## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 422 | 87.4% ➔ 87.4% (0.00) ⚪ |
| DEFLECTION/GUIDE | 428 | 76.2% ➔ 76.2% (0.00) ⚪ |
| DRIVE/DEFENCE | 470 | 73.4% ➔ 73.4% (0.00) ⚪ |
| GLANCE/FLICK | 399 | 79.4% ➔ 79.4% (0.00) ⚪ |
| POWER DRIVE | 140 | 85.0% ➔ 85.0% (0.00) ⚪ |
| PULL/HOOK | 393 | 67.9% ➔ 67.9% (0.00) ⚪ |
| SLOG | 330 | 94.2% ➔ 94.2% (0.00) ⚪ |
| SWEEP | 95 | 98.9% ➔ 98.9% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## 3. Offline Classifier Performance (All 1,803 Physical Swings)
Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):

| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |
|---|---|---|---|
| CUT/PUNCH | 422 | 68.7% | 82.0% |
| DEFLECTION/GUIDE | 428 | 57.0% | 68.9% |
| DRIVE/DEFENCE | 470 | 60.4% | 70.0% |
| GLANCE/FLICK | 399 | 56.9% | 71.9% |
| POWER DRIVE | 140 | 30.7% | 78.6% |
| PULL/HOOK | 393 | 52.9% | 63.6% |
| SLOG | 330 | 76.4% | 91.8% |
| SWEEP | 95 | 44.2% | 97.9% |
| **OVERALL** | **2677** | **59.4%** | **75.2%** |

## 4. Classification Accuracy by Data Profile
The RF model was trained on all data profiles simultaneously. Polar features are imputed to 0.0 for watch-only sessions, so the model learns to classify confidently with or without Polar data.

| Data Profile | Shots | Overall Acc | DRIVE | PULL | CUT | GLANCE | POWER | SLOG | SWEEP | GUIDE |
|---|---|---|---|---|---|---|---|---|---|---|
*Could not generate data-profile breakdown: '<' not supported between instances of 'float' and 'str'*

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
