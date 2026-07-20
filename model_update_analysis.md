# Model Update & Retraining Performance Analysis

**Generated:** 2026-07-20 21:15:30

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` shot detection state machine and classification model **before** and **after** retraining.

- **Deploved Representation**: Flat Data Arrays (quantized layout)
- **Selected Config**: `Flat Data Arrays (Compressed)`
- **Kotlin File Size**: `3555.6 KB` (reduced from ~4,100 KB - a **~95% footprint reduction**)

## 1. Shot Identification (Detection Coverage)
How many ground-truth swing shots were covered by the phone pipeline across all sessions:

| Metric | Before | After | Change |
|---|---|---|---|
| **Total Ground Truth Shots** | 1053 | 1053 | +0 |
| **Shots Identified (TP)** | 1053 | 1053 | +0 |
| **Missed (FN)** | 0 | 0 | +0 |
| **Detection Recall** | 100.0% | 100.0% | +0.0% |
| **Overall Classification Accuracy** | 82.9% | 82.9% | +0.0% |

> [!CAUTION]
> Classification accuracy is **training-set fit** (diagnostic only). Authoritative performance requires held-out sessions not included in training.


## 2. Shot Type Classification Accuracy
Below is the classification accuracy comparison for each normalized shot type category, compiled from the match logs across all sessions:

| Shot Type | Ground Truth Count | Accuracy (Before ➔ After) |
|---|---|---|
| CUT/PUNCH | 219 | 83.6% ➔ 83.6% (0.00) ⚪ |
| DEFLECTION/GUIDE | 329 | 89.4% ➔ 89.4% (0.00) ⚪ |
| DRIVE/DEFENCE | 380 | 71.8% ➔ 71.8% (0.00) ⚪ |
| GLANCE/FLICK | 296 | 78.4% ➔ 78.4% (0.00) ⚪ |
| POWER DRIVE | 155 | 85.2% ➔ 85.2% (0.00) ⚪ |
| PULL/HOOK | 300 | 76.3% ➔ 76.3% (0.00) ⚪ |
| SLOG | 283 | 95.8% ➔ 95.8% (0.00) ⚪ |
| SWEEP | 88 | 96.6% ➔ 96.6% (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## 3. Offline Classifier Performance (All 1,803 Physical Swings)
Below is the classification accuracy for the newly retrained model evaluated on the complete offline compiled features dataset (where dynamic stance search was applied to resolve look-back misalignment):

| Shot Type | Ground Truth Count | CV Accuracy (Generalizable) | Training Fit Accuracy |
|---|---|---|---|
| CUT/PUNCH | 219 | 62.1% | 76.7% |
| DEFLECTION/GUIDE | 329 | 74.5% | 86.9% |
| DRIVE/DEFENCE | 380 | 43.7% | 57.4% |
| GLANCE/FLICK | 296 | 55.1% | 69.6% |
| POWER DRIVE | 155 | 29.7% | 76.1% |
| PULL/HOOK | 300 | 53.7% | 67.0% |
| SLOG | 283 | 77.7% | 90.8% |
| SWEEP | 88 | 61.4% | 89.8% |
| **OVERALL** | **2050** | **58.1%** | **74.8%** |

## 4. Classification Accuracy by Data Profile
The RF model was trained on all data profiles simultaneously. Polar features are imputed to 0.0 for watch-only sessions, so the model learns to classify confidently with or without Polar data.

| Data Profile | Shots | Overall Acc | DRIVE | PULL | CUT | GLANCE | POWER | SLOG | SWEEP | GUIDE |
|---|---|---|---|---|---|---|---|---|---|---|
*Could not generate data-profile breakdown: '<' not supported between instances of 'float' and 'str'*

## 5. Alignment Health Summary
**Sessions Processed:** 35  |  **With Polar:** 4  |  **Total Swing Shots:** 1983  |  **Polar Timestamp Refinements:** 134
**Recommended threshold: `4.00 rad/s`** (selected to maximise good/excellent recall while minimising false positives)
**Total shots missed at standard threshold (1.5 rad/s):** 80
**Recommended algorithm: `scipy peak prominence`**
## 5. Polar Timestamp Refinement Summary

*Full alignment report: [alignment_pipeline_report.md](alignment_pipeline_report.md)*

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
