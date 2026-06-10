# Model Update & Retraining Performance Analysis

**Generated:** 2026-06-10 18:56:23

## Executive Summary
This report presents the side-by-side performance comparison of the Wear OS `SwingDetector` Random Forest shot classifier **before** and **after** retraining on the updated aligned dataset.

### Comparison Table

| Session / Shot Category | GT | Precision (Before ➔ After) | Recall (Before ➔ After) | F1 Score (Before ➔ After) | Class Accuracy (Before ➔ After) | Hit/Miss Agr (Before ➔ After) |
|---|---|---|---|---|---|---|
| Pull shots | 24 | 0.79 ➔ 0.79 (0.00) ⚪ | 0.92 ➔ 0.92 (0.00) ⚪ | 0.85 ➔ 0.85 (0.00) ⚪ | 0.05 ➔ 0.05 (0.00) ⚪ | 0.95 ➔ 0.95 (0.00) ⚪ |
| Cover drives | 14 | 1.00 ➔ 1.00 (0.00) ⚪ | 0.57 ➔ 0.57 (0.00) ⚪ | 0.73 ➔ 0.73 (0.00) ⚪ | 0.43 ➔ 0.43 (0.00) ⚪ | 0.75 ➔ 0.75 (0.00) ⚪ |
| On drives and flick shots | 26 | 0.93 ➔ 0.93 (0.00) ⚪ | 0.96 ➔ 0.96 (0.00) ⚪ | 0.94 ➔ 0.94 (0.00) ⚪ | 0.52 ➔ 0.52 (0.00) ⚪ | 0.92 ➔ 0.92 (0.00) ⚪ |
| Short off side | 25 | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ |
| full_toss | 27 | 0.82 ➔ 0.82 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 0.90 ➔ 0.90 (0.00) ⚪ | 0.56 ➔ 0.56 (0.00) ⚪ | 0.96 ➔ 0.96 (0.00) ⚪ |
| full_length | 23 | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ | 0.00 ➔ 0.00 (0.00) ⚪ |
| live_session_20260530 | 91 | 0.57 ➔ 0.57 (0.00) ⚪ | 0.81 ➔ 0.81 (0.00) ⚪ | 0.67 ➔ 0.67 (0.00) ⚪ | 0.76 ➔ 0.76 (0.00) ⚪ | 0.96 ➔ 0.96 (0.00) ⚪ |
| live_session_20260531_10 | 5 | 1.00 ➔ 1.00 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 0.60 ➔ 0.60 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ |
| live_session_20260531_14 | 68 | 0.89 ➔ 0.89 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 0.94 ➔ 0.94 (0.00) ⚪ | 0.78 ➔ 0.78 (0.00) ⚪ | 0.96 ➔ 0.96 (0.00) ⚪ |
| live_session_20260601 | 68 | 0.83 ➔ 0.83 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 0.91 ➔ 0.91 (0.00) ⚪ | 0.91 ➔ 0.91 (0.00) ⚪ | 0.85 ➔ 0.85 (0.00) ⚪ |
| live_session_20260605 | 30 | 0.88 ➔ 0.88 (0.00) ⚪ | 0.97 ➔ 0.97 (0.00) ⚪ | 0.92 ➔ 0.92 (0.00) ⚪ | 0.90 ➔ 0.90 (0.00) ⚪ | 0.86 ➔ 0.86 (0.00) ⚪ |
| live_session_20260607 | 58 | 0.85 ➔ 0.85 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 0.92 ➔ 0.92 (0.00) ⚪ | 0.79 ➔ 0.79 (0.00) ⚪ | 0.91 ➔ 0.91 (0.00) ⚪ |
| live_session_20260608 | 60 | 0.79 ➔ 0.79 (0.00) ⚪ | 0.87 ➔ 0.87 (0.00) ⚪ | 0.83 ➔ 0.83 (0.00) ⚪ | 0.94 ➔ 0.94 (0.00) ⚪ | 0.71 ➔ 0.71 (0.00) ⚪ |
| live_session_20260609 | 63 | 0.91 ➔ 0.91 (0.00) ⚪ | 1.00 ➔ 1.00 (0.00) ⚪ | 0.95 ➔ 0.95 (0.00) ⚪ | 0.94 ➔ 0.94 (0.00) ⚪ | 0.89 ➔ 0.89 (0.00) ⚪ |

## Legend
- 🟢: Significant performance improvement (> +0.005)
- 🔴: Significant performance regression (< -0.005)
- ⚪: Unchanged performance

## Detailed Verification Log
- Model successfully retrained on `combined_features.csv`.
- Transpiled Kotlin trees written successfully to `GeneratedForest.kt`.
- Run all 12 Wear OS unit tests: **BUILD SUCCESSFUL**.
- Alignment test `SwingDetectorRandomForestAlignmentTest.kt` completed with **0 mismatches** against Python predictions.
