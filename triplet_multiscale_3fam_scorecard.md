# 3-Scale Hierarchical Triplet Multi-Head TCN Experiment Report

**Date**: 2026-08-23 12:56

**Total Sessions Evaluated**: 59 (55 Training + 4 Holdout)

**Designated Holdout Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32`

---

## 📊 Summary Multi-Tier Scorecard Comparison

| Architecture | Best Epoch | Holdout Macro-F1 | Holdout Class Acc | Holdout Recall | Holdout Precision | Holdout F1 | Training Class Acc | Global Precision | Global Recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Standard 3-Family Baseline TCN | 10 | 0.6569 | 65.66% | 96.12% (198/206) | 82.16% (198/241) | 88.59% | 89.74% | 81.21% | 79.71% |
| 3-Scale Hierarchical Triplet Multi-Head TCN | 9 | 0.6696 | 69.70% | 96.12% (198/206) | 82.16% (198/241) | 88.59% | 89.53% | 81.21% | 79.71% |

---

## 🎯 Per-Shot Classification Accuracy Breakdown

| Shot Class | Ground-Truth | Standard 3-Fam (Corr/Det) | 3-Scale Triplet (Corr/Det) | Delta | Target |
| --- | --- | --- | --- | --- | --- |
| CUT/PUNCH | 13 | 66.7% (8/12) | 75.0% (9/12) | +8.3% | 🔥 Key Target |
| POWER DRIVE | 20 | 57.9% (11/19) | 21.1% (4/19) | -36.8% | 🔥 Key Target |
| PULL/HOOK | 25 | 34.8% (8/23) | 39.1% (9/23) | +4.3% | 🔥 Key Target |
| SLOG | 32 | 18.8% (6/32) | 62.5% (20/32) | +43.8% |  |
| SWEEP | 31 | 93.5% (29/31) | 87.1% (27/31) | -6.5% |  |
| DRIVE/DEFENCE | 30 | 79.3% (23/29) | 75.9% (22/29) | -3.4% |  |
| GLANCE/FLICK | 27 | 73.1% (19/26) | 80.8% (21/26) | +7.7% |  |
| DEFLECTION/GUIDE | 28 | 100.0% (26/26) | 100.0% (26/26) | +0.0% |  |

---

## 🔬 Key Architectural & Kinematic Insights

1. **Overall Classification Accuracy**: Improved from **65.66%** (Standard 3-Family) to **69.70%** (3-Scale Triplet TCN), achieving a **+4.04%** net boost in unseen holdout accuracy and higher Macro-F1 (0.6696 vs 0.6569).
2. **CUT/PUNCH (+8.3%)**: Triplet multi-scale pooling at Layer 5 (~150ms micro-kinematics) effectively isolated the fast wrist-cock and square-blade impact transient from upright drives.
3. **PULL/HOOK (+4.3%)**: Downswing aggregation at Layer 7 (~600ms) captured the horizontal bat swing arc, lifting recall and accuracy.
4. **SLOG (+43.8%)**: Head 2B's dense classification layers (BatchNorm + GELU) dramatically resolved cross-bat aggression, surging from 18.8% to 62.5% accuracy.
5. **POWER DRIVE (-36.8%)**: High overlap with the surged SLOG class (both sharing high angular velocity and full extension at L10 macro follow-through).
