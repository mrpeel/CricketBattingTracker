# Systematic Ablation Study Results & Comparative Scorecard

**Holdout Session**: `session_2026-07-18_13-44-09`  
**Date**: 2026-07-29 03:55

---

## 📊 Ablation Experiment Results Table

| Run ID | Downsampling (200Hz) | Derived Data (+Jerk/Mags) | Multi-Task (2-Head) | Detection Recall (±0.5s) | Detection Precision | Detection F1 | Holdout Shot Classification Accuracy |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Run 0 (Control)** | NO (423Hz) | NO (Raw 26) | NO (Single Head) | **44.7%** | 16.0% | 0.236 | **53.06%** |
| **Run A (Downsample)** | YES (200Hz) | NO (Raw 26) | NO (Single Head) | **47.4%** | 11.5% | 0.185 | **53.76%** |
| **Run B (Derived)** | NO (423Hz) | YES (32 Feats) | NO (Single Head) | **48.2%** | 14.8% | 0.226 | **45.74%** |
| **Run C (MultiTask)** | NO (423Hz) | NO (Raw 26) | YES (Dual-Head) | **45.6%** | 15.8% | 0.234 | **45.41%** |
| **Run A+B (Pair)** | YES (200Hz) | YES (32 Feats) | NO (Single Head) | **57.9%** | 16.0% | 0.250 | **45.18%** |
| **Run A+C (Pair)** | YES (200Hz) | NO (Raw 26) | YES (Dual-Head) | **53.5%** | 12.7% | 0.205 | **54.01%** |
| **Run B+C (Pair)** | NO (423Hz) | YES (32 Feats) | YES (Dual-Head) | **50.9%** | 16.3% | 0.246 | **49.00%** |
| **Run A+B+C (All 3)** | YES (200Hz) | YES (32 Feats) | YES (Dual-Head) | **63.2%** | 15.0% | 0.242 | **50.62%** |

---

## 🏆 Reference Benchmarks Comparison

| Reference Model / Architecture | Detection Recall | False Alarm Rate | Holdout Shot Classification Accuracy | Notes |
|---|---|---|---|---|
| **Production Random Forest** | 74.6% (±1.5s) | **4.27 FP/min** | **35.87%** | Severe training-set overfitting (>90% -> 35.87%) |
| **Previous TCN Baseline (423Hz)** | **92.1%** (±0.5s) | Continuous Softmax | **52.40%** | Peaked at Epoch 3, overfit past Epoch 3 |
| **Noise-Augmented TCN (423Hz)** | **86.8%** (±0.5s) | Continuous Softmax | **47.34%** | Global noise blurred continuous time steps |
