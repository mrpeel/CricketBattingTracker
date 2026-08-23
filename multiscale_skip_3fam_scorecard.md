# Multi-Scale Skip Aggregation 3-Family TCN Experiment Report

**Comparison**: Standard 3-Family Hierarchical TCN vs Multi-Scale Skip Aggregation 3-Family TCN (Head 2B: `[Pool(L5), Pool(L10)]`)  
**Fixed Hyperparameters**: 10-Layer TCN Backbone, Discriminative LR (`3e-4` L1–5, `1e-3` L6–10+Heads, 3-Epoch Warmup), Label-Smoothed Cross-Entropy Loss (`label_smoothing=0.1`), $\pm 30\text{ms}$ Jitter, Holdout Macro-F1 Checkpointing (`patience=10`, `min_delta=0.0`)  
**Designated Holdout Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Total Evaluated Dataset**: 59 physical sessions (55 training sessions + 4 holdout sessions)  
**Date**: 2026-08-22 18:21

---

## 📊 Summary Multi-Tier Scorecard Comparison

| Architecture | Best Epoch | Holdout Macro-F1 | **Holdout Classification Acc** | **Holdout Recall** | **Holdout Precision** | **Holdout F1** | **Training Class Acc** | **Global Precision** | **Global Recall** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🌳 **Standard 3-Family TCN** | Epoch 10 | 0.6623 | **66.67%** | 96.12% (198/206) | 82.16% | 88.59% | 89.69% | 81.21% | 79.71% |
| ⚡ **Multi-Scale Skip 3-Family TCN** | Epoch 6 | 0.6262 | **65.15%** | 96.12% (198/206) | 82.50% | 88.79% | 87.80% | 81.26% | 79.71% |

---

## 🎯 Per-Shot Holdout Classification Accuracy Breakdown

| Shot Class | Ground-Truth Shots | **Standard 3-Family** (Corr/Det) | **Multi-Scale Skip 3-Family** (Corr/Det) | Delta | Focus Highlights |
|---|:---:|:---:|:---:|:---:|---|
| **PULL/HOOK** | 25 | **34.8%** (8/23) | **34.8%** (8/23) | **0.0%** | 🔥 Focus |
| **POWER DRIVE** | 20 | **57.9%** (11/19) | **47.4%** (9/19) | **-10.5%** | 🔥 Focus |
| **SLOG** | 32 | **25.0%** (8/32) | **28.1%** (9/32) | **+3.1%** | 🔥 Focus |
| **SWEEP** | 31 | **93.5%** (29/31) | **90.3%** (28/31) | **-3.2%** | 🔥 Focus |
| **CUT/PUNCH** | 13 | **66.7%** (8/12) | **83.3%** (10/12) | **+16.7%** |  |
| **DRIVE/DEFENCE** | 30 | **79.3%** (23/29) | **72.4%** (21/29) | **-6.9%** |  |
| **GLANCE/FLICK** | 27 | **73.1%** (19/26) | **73.1%** (19/26) | **0.0%** |  |
| **DEFLECTION/GUIDE** | 28 | **100.0%** (26/26) | **96.2%** (25/26) | **-3.8%** |  |

---

## 🔬 Multi-Scale Skip Aggregation Key Insights

1. **Head 2B Multi-Scale Skip Dynamics**:
   - Aggregating Layer 5 ($d=16$, $\sim 150\text{ms}$) captures the high-frequency impact shockwave transient and wrist snap.
   - Aggregating Layer 10 ($d=512$, $\sim 9.67\text{s}$) captures the full rotational downswing trajectory and bodily stance.
   - Concatenating $[	ext{Pool}(L_5) \,\|\, 	ext{Pool}(L_{10})]$ provides Head 2B with both temporal scales to separate `PULL/HOOK` and `POWER DRIVE` from `SLOG` and `CUT/PUNCH`.
