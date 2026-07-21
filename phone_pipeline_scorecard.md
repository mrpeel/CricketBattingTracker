# Phone Pipeline Performance Scorecard
**Generated:** 2026-07-21 18:03:45  
**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  
**Sessions evaluated:** 1410  
**Architecture:** Dual-Model Routing Architecture (`GeneratedTopForest` 14f / `GeneratedDualForest` 26f)

> [!IMPORTANT]
> This scorecard reflects the **phone-side batch pipeline** (`PhoneSwingDetector.kt`)
> dynamically routing between Top-Hand (14 features) and Dual-Hand (26 features) models.

## 1. Shot Identification (Detection)

| Metric | Value |
|---|---|
| **Ground Truth Swing Shots** | 1385 |
| **Shots Identified by Pipeline** | 1385 |
| **Shots Missed (False Negatives)** | 0 |
| **Recall (Coverage)** | 100.0% |
| **Precision** | *Not measurable from offline files — requires raw detection log* |

## 2. Overall Shot Classification

**Overall accuracy (Dual-Model Routing diagnostic): 81.9%**

| Shot Class | Ground Truth Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 423 | 88% |
| DEFLECTION/GUIDE | 428 | 79% |
| DRIVE/DEFENCE | 488 | 77% |
| GLANCE/FLICK | 433 | 79% |
| POWER DRIVE | 140 | 89% |
| PULL/HOOK | 401 | 69% |
| SLOG | 330 | 96% |
| SWEEP | 114 | 100% |

## 3. Breakdown by Data Profile

This shows how well the dual-model routing performs on each data profile.

### Watch 100Hz + Polar (`100hz_watch_polar`)  — 148 shots

**Overall accuracy: 93.9%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 14 | 100% |
| DEFLECTION/GUIDE | 11 | 91% |
| DRIVE/DEFENCE | 40 | 90% |
| GLANCE/FLICK | 42 | 93% |
| POWER DRIVE | 1 | 100% |
| PULL/HOOK | 18 | 94% |
| SLOG | 2 | 100% |
| SWEEP | 20 | 100% |

### Watch-only 50Hz (`50hz_watch`)  — 1090 shots

**Overall accuracy: 75.8%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 121 | 88% |
| DEFLECTION/GUIDE | 131 | 69% |
| DRIVE/DEFENCE | 412 | 75% |
| GLANCE/FLICK | 127 | 67% |
| POWER DRIVE | 37 | 81% |
| PULL/HOOK | 155 | 68% |
| SLOG | 87 | 94% |
| SWEEP | 20 | 100% |

### Watch 50Hz + Polar (`50hz_watch_polar`)  — 147 shots

**Overall accuracy: 77.6%**

| Shot Class | Count | Accuracy |
|---|---|---|
| DRIVE/DEFENCE | 36 | 89% |
| GLANCE/FLICK | 20 | 65% |
| PULL/HOOK | 70 | 70% |
| SLOG | 21 | 95% |

