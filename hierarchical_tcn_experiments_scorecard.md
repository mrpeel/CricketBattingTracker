# Hierarchical Multi-Head TCN Architectural Experiment Report

**Comparison**: Canonical Single-Head Baseline vs 2-Family Hierarchical Multi-Head TCN vs 3-Family Hierarchical Multi-Head TCN  
**Fixed Hyperparameters**: 10-Layer TCN Backbone (Skip Concatenation L4+L7+L10), Discriminative LR (`3e-4` L1–5, `1e-3` L6–10+Heads, 3-Epoch Warmup), Label-Smoothed Cross-Entropy Loss (`label_smoothing=0.1`), $\pm 30\text{ms}$ Jitter, Holdout Macro-F1 Checkpointing (`patience=10`, `min_delta=0.0`)  
**Designated Holdout Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Total Evaluated Dataset**: 58 physical sessions (54 training sessions + 4 holdout sessions)  
**Date**: 2026-08-22 15:35

---

## 📊 Summary Multi-Tier Scorecard Comparison

| Architecture | Best Epoch | Holdout Macro-F1 | **Holdout Classification Acc** | **Holdout Recall** | **Holdout Precision** | **Holdout F1** | **Training Class Acc** | **Global Precision** | **Global Recall** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 🏛️ **Baseline Single-Head (Canonical 10-Class)** | Epoch 19 | 0.6090 | **63.92%** | 94.17% (194/206) | 82.55% | 87.98% | 85.66% | 81.39% | 77.85% |
| 🌿 **Experiment 1: 2-Family Hierarchical Multi-Head** | Epoch 18 | 0.6723 | **69.70%** | 96.12% (198/206) | 82.50% | 88.79% | 92.85% | 81.29% | 79.51% |
| 🌳 **Experiment 2: 3-Family Hierarchical Multi-Head** | Epoch 10 | 0.6571 | **72.73%** | 96.12% (198/206) | 82.16% | 88.59% | 89.41% | 81.27% | 79.51% |

---

## 🎯 Per-Shot Holdout Classification Accuracy Breakdown

| Shot Class | Ground-Truth Shots | **Baseline Single-Head** (Corr/Det) | **Experiment 1: 2-Family** (Corr/Det) | **Experiment 2: 3-Family** (Corr/Det) | Focus Shot Highlights |
|---|:---:|:---:|:---:|:---:|---|
| **PULL/HOOK** | 25 | **34.8%** (8/23) | **34.8%** (8/23) | **34.8%** (8/23) | 🔥 Key Focus (PULL/HOOK) |
| **SLOG** | 32 | **28.1%** (9/32) | **59.4%** (19/32) | **68.8%** (22/32) | 🔥 Key Focus (SLOG) |
| **POWER DRIVE** | 20 | **42.1%** (8/19) | **36.8%** (7/19) | **26.3%** (5/19) | 🔥 Key Focus (POWER DRIVE) |
| **SWEEP** | 31 | **92.6%** (25/27) | **83.9%** (26/31) | **100.0%** (31/31) | 🔥 Key Focus (SWEEP) |
| **CUT/PUNCH** | 13 | **75.0%** (9/12) | **75.0%** (9/12) | **91.7%** (11/12) |  |
| **DRIVE/DEFENCE** | 30 | **69.0%** (20/29) | **82.8%** (24/29) | **75.9%** (22/29) |  |
| **GLANCE/FLICK** | 27 | **76.9%** (20/26) | **76.9%** (20/26) | **73.1%** (19/26) |  |
| **DEFLECTION/GUIDE** | 28 | **96.2%** (25/26) | **96.2%** (25/26) | **100.0%** (26/26) |  |

---

## 🔬 Architectural Findings & Conclusions

1. **Macro Family Gating Impact**:
   - Decomposing the output into Macro Family Gate + Specialized Sub-Classifiers tests whether separating vertical-bat touch shots from horizontal-bat power strokes prevents feature competition in the shared backbone representation.
2. **Key Class Performance**:
   - **PULL/HOOK**: Evaluated on cross-bat power strokes.
   - **SLOG**: Evaluated on high-energy horizontal rotational swings.
   - **POWER DRIVE**: Evaluated on vertical downswing with high impact force.
   - **SWEEP**: Evaluated on low torso tilt / knee-down crouched ground strokes.
