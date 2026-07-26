# Phone Pipeline Performance Scorecard
**Generated:** 2026-07-26 16:14:31  
**Source of truth:** `combined_features.csv` + `combined_ground_truth_aligned.csv`  
**Sessions evaluated:** 1140  
**Architecture:** Dual-Model Routing Architecture (`GeneratedTopForest` 14f / `GeneratedDualForest` 26f)

> [!IMPORTANT]
> This scorecard reflects the **phone-side batch pipeline** (`PhoneSwingDetector.kt`)
> dynamically routing between Top-Hand (14 features) and Dual-Hand (26 features) models.

## 1. Shot Identification (Detection)

| Metric | Value |
|---|---|
| **Ground Truth Swing Shots** | 2050 |
| **Shots Identified by Pipeline** | 2050 |
| **Shots Missed (False Negatives)** | 0 |
| **Recall (Coverage)** | 100.0% |
| **Precision** | *Not measurable from offline files — requires raw detection log* |

## 2. Overall Shot Classification

**Overall accuracy (Dual-Model Routing diagnostic): 82.7%**

| Shot Class | Ground Truth Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 399 | 88% |
| DEFLECTION/GUIDE | 469 | 83% |
| DRIVE/DEFENCE | 489 | 78% |
| GLANCE/FLICK | 379 | 73% |
| POWER DRIVE | 160 | 93% |
| PULL/HOOK | 427 | 73% |
| SLOG | 421 | 93% |
| SWEEP | 404 | 88% |

## 3. Breakdown by Data Profile

This shows how well the dual-model routing performs on each data profile.

### Watch 100Hz + Polar (`100hz_watch_polar`)  — 330 shots

**Overall accuracy: 94.8%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 76 | 97% |
| DEFLECTION/GUIDE | 53 | 96% |
| DRIVE/DEFENCE | 53 | 92% |
| GLANCE/FLICK | 15 | 87% |
| POWER DRIVE | 16 | 100% |
| PULL/HOOK | 48 | 92% |
| SLOG | 31 | 90% |
| SWEEP | 38 | 100% |

### Watch-only 50Hz (`50hz_watch`)  — 1505 shots

**Overall accuracy: 75.5%**

| Shot Class | Count | Accuracy |
|---|---|---|
| CUT/PUNCH | 187 | 86% |
| DEFLECTION/GUIDE | 165 | 69% |
| DRIVE/DEFENCE | 363 | 72% |
| GLANCE/FLICK | 205 | 64% |
| POWER DRIVE | 48 | 85% |
| PULL/HOOK | 257 | 70% |
| SLOG | 171 | 91% |
| SWEEP | 109 | 86% |

### Watch 50Hz + Polar (`50hz_watch_polar`)  — 215 shots

**Overall accuracy: 87.0%**

| Shot Class | Count | Accuracy |
|---|---|---|
| DEFLECTION/GUIDE | 3 | 100% |
| DRIVE/DEFENCE | 73 | 97% |
| GLANCE/FLICK | 52 | 79% |
| PULL/HOOK | 51 | 75% |
| SLOG | 34 | 100% |
| SWEEP | 2 | 0% |

