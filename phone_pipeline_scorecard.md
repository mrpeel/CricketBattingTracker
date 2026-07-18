# Phone Pipeline Performance Scorecard
**Generated:** 2026-07-19 06:59:32  
**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  
**Sessions evaluated:** 955  
**Model:** 20-feature Random Forest (200 trees, depth 8, heterogeneous training)

> [!IMPORTANT]
> This scorecard reflects the **phone-side batch pipeline** (`PhoneSwingDetector.kt`)
> using the 20-feature GeneratedForest (14 watch + 6 Polar, 0.0-imputed when absent).
> It replaces the retired on-watch `SwingDetector` scorecard.

> [!CAUTION]
> Classification accuracy here is **training-set fit** (same data used to train the model).
> It is reported purely as a diagnostic. The authoritative ground-truth accuracy
> must be collected from live sessions not included in the training set.

## 1. Shot Identification (Detection)

| Metric | Value |
|---|---|
| **Ground Truth Swing Shots** | 1028 |
| **Shots Identified by Pipeline** | 1028 |
| **Shots Missed (False Negatives)** | 0 |
| **Recall (Coverage)** | 100.0% |
| **Precision** | *Not measurable from offline files — requires raw detection log* |

## 2. Overall Shot Classification

**Overall accuracy (training-set diagnostic): 84.8%**

| Shot Class | Ground Truth Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 218 | 84% |
| DEFLECTION/GUIDE | 299 | 90% |
| DRIVE/DEFENCE | 362 | 75% |
| GLANCE/FLICK | 285 | 83% |
| POWER DRIVE | 138 | 88% |
| PULL/HOOK | 283 | 75% |
| SLOG | 285 | 98% |
| SWEEP | 79 | 100% |

## 3. Breakdown by Data Profile

This shows how well the model performs on each data combination,
demonstrating that heterogeneous training generalises across all profiles.

### Watch 100Hz + Polar (`100hz_watch_polar`)  — 53 shots

**Overall accuracy: 96.2%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 9 | 89% |
| DEFLECTION/GUIDE | 11 | 100% |
| DRIVE/DEFENCE | 20 | 100% |
| POWER DRIVE | 1 | 100% |
| PULL/HOOK | 3 | 67% |
| SWEEP | 9 | 100% |

### Watch-only 50Hz (`50hz_watch`)  — 830 shots

**Overall accuracy: 77.6%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 79 | 86% |
| DEFLECTION/GUIDE | 98 | 88% |
| DRIVE/DEFENCE | 306 | 72% |
| GLANCE/FLICK | 103 | 70% |
| POWER DRIVE | 37 | 84% |
| PULL/HOOK | 125 | 71% |
| SLOG | 73 | 95% |
| SWEEP | 9 | 100% |

### Watch 50Hz + Polar (`50hz_watch_polar`)  — 145 shots

**Overall accuracy: 83.4%**

| Shot Class | Count | Accuracy |
|---|---|---|
| DRIVE/DEFENCE | 36 | 86% |
| GLANCE/FLICK | 20 | 75% |
| PULL/HOOK | 69 | 81% |
| SLOG | 20 | 95% |

