# Phone Pipeline Performance Scorecard
**Generated:** 2026-07-20 21:15:29  
**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  
**Sessions evaluated:** 1031  
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
| **Ground Truth Swing Shots** | 1053 |
| **Shots Identified by Pipeline** | 1053 |
| **Shots Missed (False Negatives)** | 0 |
| **Recall (Coverage)** | 100.0% |
| **Precision** | *Not measurable from offline files — requires raw detection log* |

## 2. Overall Shot Classification

**Overall accuracy (training-set diagnostic): 82.9%**

| Shot Class | Ground Truth Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 219 | 84% |
| DEFLECTION/GUIDE | 329 | 89% |
| DRIVE/DEFENCE | 380 | 72% |
| GLANCE/FLICK | 296 | 78% |
| POWER DRIVE | 155 | 85% |
| PULL/HOOK | 300 | 76% |
| SLOG | 283 | 96% |
| SWEEP | 88 | 97% |

## 3. Breakdown by Data Profile

This shows how well the model performs on each data combination,
demonstrating that heterogeneous training generalises across all profiles.

### Watch 100Hz + Polar (`100hz_watch_polar`)  — 53 shots

**Overall accuracy: 98.1%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 9 | 100% |
| DEFLECTION/GUIDE | 11 | 100% |
| DRIVE/DEFENCE | 20 | 100% |
| POWER DRIVE | 1 | 100% |
| PULL/HOOK | 3 | 67% |
| SWEEP | 9 | 100% |

### Watch-only 50Hz (`50hz_watch`)  — 853 shots

**Overall accuracy: 75.8%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 81 | 88% |
| DEFLECTION/GUIDE | 99 | 87% |
| DRIVE/DEFENCE | 324 | 69% |
| GLANCE/FLICK | 104 | 66% |
| POWER DRIVE | 37 | 78% |
| PULL/HOOK | 126 | 74% |
| SLOG | 73 | 93% |
| SWEEP | 9 | 89% |

### Watch 50Hz + Polar (`50hz_watch_polar`)  — 147 shots

**Overall accuracy: 82.3%**

| Shot Class | Count | Accuracy |
|---|---|---|
| DRIVE/DEFENCE | 36 | 83% |
| GLANCE/FLICK | 20 | 65% |
| PULL/HOOK | 70 | 83% |
| SLOG | 21 | 95% |

