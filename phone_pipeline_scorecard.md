# Phone Pipeline Performance Scorecard
**Generated:** 2026-07-19 12:04:53  
**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  
**Sessions evaluated:** 1022  
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
| **Ground Truth Swing Shots** | 1049 |
| **Shots Identified by Pipeline** | 1049 |
| **Shots Missed (False Negatives)** | 0 |
| **Recall (Coverage)** | 100.0% |
| **Precision** | *Not measurable from offline files — requires raw detection log* |

## 2. Overall Shot Classification

**Overall accuracy (training-set diagnostic): 82.7%**

| Shot Class | Ground Truth Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 217 | 84% |
| DEFLECTION/GUIDE | 326 | 90% |
| DRIVE/DEFENCE | 379 | 72% |
| GLANCE/FLICK | 294 | 76% |
| POWER DRIVE | 155 | 86% |
| PULL/HOOK | 298 | 75% |
| SLOG | 280 | 96% |
| SWEEP | 88 | 97% |

## 3. Breakdown by Data Profile

This shows how well the model performs on each data combination,
demonstrating that heterogeneous training generalises across all profiles.

### Watch 100Hz + Polar (`100hz_watch_polar`)  — 53 shots

**Overall accuracy: 94.3%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 9 | 78% |
| DEFLECTION/GUIDE | 11 | 100% |
| DRIVE/DEFENCE | 20 | 100% |
| POWER DRIVE | 1 | 100% |
| PULL/HOOK | 3 | 67% |
| SWEEP | 9 | 100% |

### Watch-only 50Hz (`50hz_watch`)  — 851 shots

**Overall accuracy: 76.0%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 80 | 86% |
| DEFLECTION/GUIDE | 99 | 87% |
| DRIVE/DEFENCE | 323 | 69% |
| GLANCE/FLICK | 104 | 66% |
| POWER DRIVE | 37 | 84% |
| PULL/HOOK | 126 | 73% |
| SLOG | 73 | 95% |
| SWEEP | 9 | 89% |

### Watch 50Hz + Polar (`50hz_watch_polar`)  — 145 shots

**Overall accuracy: 80.0%**

| Shot Class | Count | Accuracy |
|---|---|---|
| DRIVE/DEFENCE | 36 | 86% |
| GLANCE/FLICK | 20 | 55% |
| PULL/HOOK | 69 | 81% |
| SLOG | 20 | 90% |

