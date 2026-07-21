# Phone Pipeline Performance Scorecard
**Generated:** 2026-07-21 17:37:09  
**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  
**Sessions evaluated:** 1408  
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
| **Ground Truth Swing Shots** | 1305 |
| **Shots Identified by Pipeline** | 1305 |
| **Shots Missed (False Negatives)** | 0 |
| **Recall (Coverage)** | 100.0% |
| **Precision** | *Not measurable from offline files — requires raw detection log* |

## 2. Overall Shot Classification

**Overall accuracy (training-set diagnostic): 80.4%**

| Shot Class | Ground Truth Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 422 | 87% |
| DEFLECTION/GUIDE | 428 | 77% |
| DRIVE/DEFENCE | 470 | 74% |
| GLANCE/FLICK | 399 | 79% |
| POWER DRIVE | 140 | 85% |
| PULL/HOOK | 393 | 67% |
| SLOG | 330 | 95% |
| SWEEP | 95 | 99% |

## 3. Breakdown by Data Profile

This shows how well the model performs on each data combination,
demonstrating that heterogeneous training generalises across all profiles.

### Watch 100Hz + Polar (`100hz_watch_polar`)  — 69 shots

**Overall accuracy: 91.3%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 14 | 100% |
| DEFLECTION/GUIDE | 11 | 100% |
| DRIVE/DEFENCE | 22 | 91% |
| GLANCE/FLICK | 8 | 62% |
| POWER DRIVE | 1 | 100% |
| PULL/HOOK | 10 | 90% |
| SLOG | 2 | 100% |
| SWEEP | 1 | 100% |

### Watch-only 50Hz (`50hz_watch`)  — 1089 shots

**Overall accuracy: 74.4%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 120 | 88% |
| DEFLECTION/GUIDE | 131 | 63% |
| DRIVE/DEFENCE | 412 | 72% |
| GLANCE/FLICK | 127 | 69% |
| POWER DRIVE | 37 | 73% |
| PULL/HOOK | 155 | 70% |
| SLOG | 87 | 93% |
| SWEEP | 20 | 100% |

### Watch 50Hz + Polar (`50hz_watch_polar`)  — 147 shots

**Overall accuracy: 74.8%**

| Shot Class | Count | Accuracy |
|---|---|---|
| DRIVE/DEFENCE | 36 | 86% |
| GLANCE/FLICK | 20 | 60% |
| PULL/HOOK | 70 | 69% |
| SLOG | 21 | 90% |

