# Dual-Sensor Expert Training & Holdout Scorecard Report

**Dataset Filter**: Strictly complete dual-sensor sessions (`has_polar == 1` and `p_acc_mag > 1.0`)  
**Training Sessions Count**: 30 physical sessions (34 evaluated)  
**Holdout Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions, 100% active Polar)  
**Best Model Checkpoint**: Epoch 20 (Reloaded Dual Checkpoint) (Macro-F1: 0.6242, Candidate Acc: 62.62%)  
**Execution Log**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/dual_sensor_training_2026-09-04_07-13-04.log`  
**Date**: 2026-09-04 07:13

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (4 Sessions)** | **206** | **241** | **87.38%** (180/206) | **74.69%** (180/241) | **80.54%** |
| 🏋️ **Dual Training Set (30 Sessions)** | **1757** | **1714** | **76.15%** (1338/1757) | **78.06%** (1338/1714) | **77.10%** |
| 🌐 **Total Dual Dataset (34 Sessions)** | **1963** | **1955** | **77.33%** (1518/1963) | **77.65%** (1518/1955) | **77.49%** |

---

## 🎯 Peak-Aligned Holdout Classification Accuracy per Shot Type

| Shot Type | GT Count | Detected TPs | Class Correct | Classification Acc (%) | Shot Recall (%) |
|---|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 57 | 49 | 26 | **53.06%** | 45.61% |
| **DRIVE/DEFENCE** | 30 | 27 | 15 | **55.56%** | 50.00% |
| **GLANCE/FLICK** | 27 | 22 | 14 | **63.64%** | 51.85% |
| **CUT/PUNCH** | 13 | 11 | 9 | **81.82%** | 69.23% |
| **DEFLECTION/GUIDE** | 28 | 21 | 19 | **90.48%** | 67.86% |
| **POWER DRIVE** | 20 | 20 | 8 | **40.00%** | 40.00% |
| **SWEEP** | 31 | 30 | 23 | **76.67%** | 74.19% |

🏆 **Overall Holdout Classification Accuracy**: **63.33%** (114/180 correct across detected shots)
