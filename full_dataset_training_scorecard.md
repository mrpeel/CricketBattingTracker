# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.0, 1.0, 1.0], Rejection Threshold $\theta_{no\_shot} = 0.35$)  
**Holdout Test Sessions**: `session_2026-06-12_12-24-37, session_2026-06-16_15-39-33, session_2026-06-19_12-25-55, session_2026-07-05_16-27-16, session_2026-07-20_12-42-16, session_2026-07-25_15-16-32, session_2026-08-11_12-49-31, session_2026-08-21_12-50-53, session_2026-09-08_12-52-30, session_2026-09-17_12-48-47, session_2026-10-05_12-53-51, session_2026-10-09_12-41-17` (12 sessions)  
**Validation Sessions**: `session_2026-06-27_14-12-40, session_2026-07-02_12-38-53, session_2026-08-01_10-18-20, session_2026-08-17_12-51-22, session_2026-08-30_11-05-11, session_2026-09-10_12-55-41, session_2026-10-04_15-30-15` (7 sessions)  
**Quarantined Faulted Sessions**: `session_2026-05-30_15-04-41, session_2026-05-31_14-12-10, session_2026-07-11_12-51-39, session_2026-07-17_12-30-41, session_2026-07-18_13-44-09, session_2026-09-05_16-26-41, session_2026-09-06_12-14-46, session_2026-09-11_12-44-50` (8 sessions)  
**Training Sessions Count**: 64 physical sessions  
**Clean Benchmark Sessions Count**: 83 physical sessions  
**Total Dataset Duration**: 1477.1 minutes (24.6 hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch 5 (Best Val Macro-F1: 0.7953, Shot Acc: 84.93%, Val Loss: 1.4685, Stopped at Epoch 21)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-10-22_13-23-31.log`  
**Date**: 2026-10-22 13:47

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set (12 Sessions)** | **701** | **722** | **93.15%** (653/701) | **90.44%** (653/722) | **91.78%** |
| **Training Set Micro Average (64 Sessions)** | **4031** | **4034** | **90.08%** (3631/4031) | **90.01%** (3631/4034) | **90.04%** |
| 🏆 **Clean Benchmark Micro Average (83 Sessions)** | **4732** | **4756** | 🏆 **90.53%** (4284/4732) | 🏆 **90.08%** (4284/4756) | 🏆 **90.30%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (12 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 111 | 107 | 96.4% | 83 | **77.6%** | **74.8%** |
| **DRIVE/DEFENCE** | 198 | 183 | 92.4% | 145 | **79.2%** | **73.2%** |
| **GLANCE/FLICK** | 59 | 56 | 94.9% | 29 | **51.8%** | **49.2%** |
| **CUT/PUNCH** | 102 | 96 | 94.1% | 86 | **89.6%** | **84.3%** |
| **DEFLECTION/GUIDE** | 112 | 94 | 83.9% | 83 | **88.3%** | **74.1%** |
| **POWER DRIVE** | 57 | 57 | 100.0% | 20 | **35.1%** | **35.1%** |
| **SWEEP** | 62 | 60 | 96.8% | 45 | **75.0%** | **72.6%** |
| **OVERALL TOTAL** | **701** | **653** | **93.2%** | **491** | 🏆 **75.2%** | 🏆 **70.0%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (71 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1165 | 1059 | 90.9% | 977 | **92.3%** | **83.9%** |
| **DRIVE/DEFENCE** | 976 | 897 | 91.9% | 775 | **86.4%** | **79.4%** |
| **GLANCE/FLICK** | 777 | 712 | 91.6% | 633 | **88.9%** | **81.5%** |
| **CUT/PUNCH** | 417 | 382 | 91.6% | 357 | **93.5%** | **85.6%** |
| **DEFLECTION/GUIDE** | 203 | 137 | 67.5% | 124 | **90.5%** | **61.1%** |
| **POWER DRIVE** | 285 | 255 | 89.5% | 248 | **97.3%** | **87.0%** |
| **SWEEP** | 208 | 189 | 90.9% | 170 | **89.9%** | **81.7%** |
| **OVERALL TOTAL** | **4031** | **3631** | **90.1%** | **3284** | 🏆 **90.4%** | 🏆 **81.5%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 83 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1276 | 1166 | 91.4% | 1060 | **90.9%** | **83.1%** |
| **DRIVE/DEFENCE** | 1174 | 1080 | 92.0% | 920 | **85.2%** | **78.4%** |
| **GLANCE/FLICK** | 836 | 768 | 91.9% | 662 | **86.2%** | **79.2%** |
| **CUT/PUNCH** | 519 | 478 | 92.1% | 443 | **92.7%** | **85.4%** |
| **DEFLECTION/GUIDE** | 315 | 231 | 73.3% | 207 | **89.6%** | **65.7%** |
| **POWER DRIVE** | 342 | 312 | 91.2% | 268 | **85.9%** | **78.4%** |
| **SWEEP** | 270 | 249 | 92.2% | 215 | **86.3%** | **79.6%** |
| **OVERALL TOTAL** | **4732** | **4284** | **90.5%** | **3775** | 🏆 **88.1%** | 🏆 **79.8%** |

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 4 | 75.0% | 75.0% | 75.0%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 60 | 93.4% | 95.0% | 94.2%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 96.4% | 96.4% | 96.4%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 41 | 70.6% | 87.8% | 78.3%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 40 | 66.7% | 75.0% | 70.6%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 94.8% | 93.2% | 94.0%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 96.1% | 92.5% | 94.2%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 65 | 89.9% | 95.4% | 92.5%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 60 | 100.0% | 91.7% | 95.7%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 55 | 96.5% | 100.0% | 98.2%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 56 | 93.0% | 94.6% | 93.8%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 65 | 95.4% | 95.4% | 95.4%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 60 | 96.6% | 95.0% | 95.8%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 55 | 98.1% | 92.7% | 95.3%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 62 | 100.0% | 93.5% | 96.7%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 53 | 98.0% | 90.6% | 94.1%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 55 | 93.1% | 98.2% | 95.6%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 45 | 76.9% | 88.9% | 82.5%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 62 | 100.0% | 93.5% | 96.7%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 52 | 92.2% | 90.4% | 91.3%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 19 | 30.4% | 89.5% | 45.3%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 61 | 67 | 90.2% | 82.1% | 85.9%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 58 | 62 | 72.4% | 67.7% | 70.0%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 61 | 98.2% | 91.8% | 94.9%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 52 | 51 | 78.8% | 80.4% | 79.6%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 59 | 98.2% | 91.5% | 94.7%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 56 | 94.3% | 89.3% | 91.7%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 44 | 56 | 90.9% | 71.4% | 80.0%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 63 | 89.1% | 77.8% | 83.1%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 51 | 93.9% | 90.2% | 92.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 64 | 83.6% | 79.7% | 81.6%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 58 | 59 | 84.5% | 83.1% | 83.8%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 58 | 91.9% | 98.3% | 95.0%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 74 | 85.7% | 89.2% | 87.4%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 64 | 93.4% | 89.1% | 91.2%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 70 | 87.7% | 91.4% | 89.5%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 51 | 100.0% | 98.0% | 99.0%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 69 | 97.0% | 92.8% | 94.8%
| `session_2026-08-22_14-25-31` | Training | 12.0 | 51 | 48 | 86.3% | 91.7% | 88.9%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 65 | 94.0% | 96.9% | 95.5%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 92.3% | 89.6% | 90.9%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 68 | 98.3% | 83.8% | 90.5%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 63 | 89.3% | 79.4% | 84.0%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 64 | 92.4% | 95.3% | 93.8%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 50 | 77.8% | 84.0% | 80.8%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 65 | 63 | 89.2% | 92.1% | 90.6%
| `session_2026-09-06_11-41-57` | Training | 1.8 | 7 | 6 | 85.7% | 100.0% | 92.3%
| `session_2026-09-06_12-35-47` | Training | 5.3 | 27 | 25 | 92.6% | 100.0% | 96.2%
| `session_2026-09-07_12-29-10` | Training | 20.3 | 60 | 56 | 73.3% | 78.6% | 75.9%
| `session_2026-09-14_12-56-40` | Training | 21.2 | 53 | 60 | 96.2% | 85.0% | 90.3%
| `session_2026-09-18_12-48-53` | Training | 20.5 | 68 | 65 | 92.6% | 96.9% | 94.7%
| `session_2026-09-30_12-52-29` | Training | 20.2 | 63 | 63 | 93.7% | 93.7% | 93.7%
| `session_2026-10-06_12-49-35` | Training | 24.2 | 73 | 71 | 89.0% | 91.5% | 90.3%
| `session_2026-10-08_12-55-02` | Training | 20.6 | 69 | 69 | 81.2% | 81.2% | 81.2%
| `session_2026-10-15_12-49-52` | Training | 20.0 | 58 | 60 | 93.1% | 90.0% | 91.5%
| `session_2026-10-16_12-59-39` | Training | 19.6 | 69 | 70 | 87.0% | 85.7% | 86.3%
| `session_2026-10-17_11-47-47` | Training | 18.9 | 70 | 67 | 87.1% | 91.0% | 89.1%
| `session_2026-10-18_14-46-16` | Training | 19.2 | 64 | 66 | 87.5% | 84.8% | 86.2%
| `session_2026-10-19_12-47-59` | Training | 19.4 | 67 | 72 | 94.0% | 87.5% | 90.6%
| `session_2026-10-20_12-39-32` | Training | 18.9 | 70 | 69 | 90.0% | 91.3% | 90.6%
| `session_2026-10-22_12-57-41` | Training | 19.7 | 73 | 70 | 90.4% | 94.3% | 92.3%
| `session_2026-06-27_14-12-40` | 🔹 VALIDATION | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-07-02_12-38-53` | 🔹 VALIDATION | 20.9 | 59 | 59 | 98.3% | 98.3% | 98.3%
| `session_2026-08-01_10-18-20` | 🔹 VALIDATION | 8.9 | 27 | 27 | 88.9% | 88.9% | 88.9%
| `session_2026-08-17_12-51-22` | 🔹 VALIDATION | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
| `session_2026-08-30_11-05-11` | 🔹 VALIDATION | 21.1 | 64 | 63 | 90.6% | 92.1% | 91.3%
| `session_2026-09-10_12-55-41` | 🔹 VALIDATION | 19.4 | 60 | 57 | 88.3% | 93.0% | 90.6%
| `session_2026-10-04_15-30-15` | 🔹 VALIDATION | 15.0 | 67 | 65 | 92.5% | 95.4% | 93.9%
| `session_2026-06-12_12-24-37` | 🌟 HOLDOUT TEST | 20.9 | 70 | 70 | 97.1% | 97.1% | 97.1%
| `session_2026-06-16_15-39-33` | 🌟 HOLDOUT TEST | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-19_12-25-55` | 🌟 HOLDOUT TEST | 16.7 | 56 | 59 | 98.2% | 93.2% | 95.7%
| `session_2026-07-05_16-27-16` | 🌟 HOLDOUT TEST | 18.5 | 57 | 58 | 96.5% | 94.8% | 95.7%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT TEST | 15.3 | 37 | 49 | 91.9% | 69.4% | 79.1%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT TEST | 20.6 | 61 | 65 | 98.4% | 92.3% | 95.2%
| `session_2026-08-11_12-49-31` | 🌟 HOLDOUT TEST | 19.8 | 62 | 64 | 91.9% | 89.1% | 90.5%
| `session_2026-08-21_12-50-53` | 🌟 HOLDOUT TEST | 21.0 | 69 | 66 | 89.9% | 93.9% | 91.9%
| `session_2026-09-08_12-52-30` | 🌟 HOLDOUT TEST | 22.7 | 57 | 56 | 82.5% | 83.9% | 83.2%
| `session_2026-09-17_12-48-47` | 🌟 HOLDOUT TEST | 20.3 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-10-05_12-53-51` | 🌟 HOLDOUT TEST | 20.6 | 67 | 64 | 86.6% | 90.6% | 88.5%
| `session_2026-10-09_12-41-17` | 🌟 HOLDOUT TEST | 20.1 | 51 | 57 | 96.1% | 86.0% | 90.7%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **NOT_DETECTED (MISSING_CANDIDATE)** | **43** | DRIVE/DEFENCE (15), DEFLECTION/GUIDE (14), PULL/HOOK/SLOG (5) |
| **CROSS_BAT_CONFUSION** | **40** | DRIVE/DEFENCE (22), GLANCE/FLICK (15), DEFLECTION/GUIDE (3) |
| **VERTICAL_BAT_CONFUSION** | **34** | PULL/HOOK/SLOG (24), CUT/PUNCH (10) |
| **CROSS_BAT_CONFUSION (Macro Gate)** | **33** | POWER DRIVE (33) |
| **SUBCLASS_CONFUSION** | **31** | DRIVE/DEFENCE (15), DEFLECTION/GUIDE (9), GLANCE/FLICK (4) |
| **SWEEP_CONFUSION** | **24** | SWEEP (15), GLANCE/FLICK (7), DRIVE/DEFENCE (2) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-06-12_12-24-37` | 138.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 132.22 | -6.13 | *pull shot four facing up* |
| `session_2026-06-12_12-24-37` | 197.07 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 195.39 | -1.68 | *flick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 632.67 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 627.36 | -5.31 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 654.71 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.41 | 654.65 | -0.06 | *good shot okay facing up* |
| `session_2026-06-12_12-24-37` | 753.15 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.45 | 752.84 | -0.31 | *pull shot good* |
| `session_2026-06-16_15-39-33` | 6.79 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 64.51 | +57.72 | *alright* |
| `session_2026-06-16_15-39-33` | 64.26 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.46 | 64.51 | +0.25 | *straight shot with miss* |
| `session_2026-06-16_15-39-33` | 89.19 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.29 | 89.28 | +0.09 | *quick shot missed* |
| `session_2026-06-16_15-39-33` | 99.53 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.57 | 99.87 | +0.34 | *slip shot four* |
| `session_2026-06-16_15-39-33` | 113.70 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.72 | 113.96 | +0.26 | *quick shot miss* |
| `session_2026-06-16_15-39-33` | 129.64 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.54 | 129.62 | -0.02 | *slip shot miss* |
| `session_2026-06-16_15-39-33` | 139.62 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.71 | 139.63 | +0.01 | *sweep shot okay* |
| `session_2026-06-16_15-39-33` | 150.35 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.75 | 150.59 | +0.24 | *three shot four* |
| `session_2026-06-16_15-39-33` | 169.68 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.63 | 170.00 | +0.32 | *free shot okay* |
| `session_2026-06-16_15-39-33` | 178.56 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.61 | 178.73 | +0.17 | *slip shot okay* |
| `session_2026-06-16_15-39-33` | 187.76 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.56 | 188.17 | +0.41 | *slip shot four* |
| `session_2026-06-16_15-39-33` | 199.11 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.62 | 199.32 | +0.21 | *sling shot okay* |
| `session_2026-06-16_15-39-33` | 209.36 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.64 | 209.56 | +0.20 | *sweep shot good* |
| `session_2026-06-16_15-39-33` | 218.87 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.40 | 219.30 | +0.43 | *sweep shot good* |
| `session_2026-06-16_15-39-33` | 448.21 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.38 | 448.56 | +0.35 | *slip shot four* |
| `session_2026-06-16_15-39-33` | 472.40 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.41 | 472.62 | +0.22 | *slip shot okay* |
| `session_2026-06-16_15-39-33` | 497.58 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.45 | 497.65 | +0.07 | *flick shot core* |
| `session_2026-06-16_15-39-33` | 505.82 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.41 | 506.17 | +0.35 | *flick shot okay* |
| `session_2026-06-16_15-39-33` | 514.79 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.47 | 515.15 | +0.36 | *sweep shot good* |
| `session_2026-06-16_15-39-33` | 534.01 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.49 | 534.39 | +0.38 | *sweet shot okay* |
| `session_2026-06-16_15-39-33` | 555.77 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.67 | 555.79 | +0.02 | *flip shot miss* |
| `session_2026-06-16_15-39-33` | 576.60 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.40 | 576.70 | +0.10 | *foot shot four* |
| `session_2026-06-16_15-39-33` | 791.41 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.75 | 790.77 | -0.64 | *on drive miss* |
| `session_2026-06-16_15-39-33` | 804.61 | **DRIVE/DEFENCE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.42 | 804.42 | -0.19 | *let's try miss* |
| `session_2026-06-16_15-39-33` | 832.41 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.68 | 832.48 | +0.07 | *flip shot miss* |
| `session_2026-06-16_15-39-33` | 844.81 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.69 | 844.50 | -0.31 | *sweep shot four* |
| `session_2026-06-16_15-39-33` | 864.30 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.64 | 864.43 | +0.13 | *flip shot okay* |
| `session_2026-06-16_15-39-33` | 882.72 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.59 | 882.61 | -0.11 | *sweep shot okay* |
| `session_2026-06-16_15-39-33` | 910.66 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.70 | 910.79 | +0.13 | *sleep shot good* |
| `session_2026-06-16_15-39-33` | 920.42 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.70 | 920.86 | +0.44 | *sleep shot good* |
| `session_2026-06-16_15-39-33` | 968.92 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.76 | 969.00 | +0.08 | *flick shot poor* |
| `session_2026-06-16_15-39-33` | 978.36 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.76 | 978.45 | +0.09 | *flick shot good end of round in the session* |
| `session_2026-06-19_12-25-55` | 45.30 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.74 | 44.29 | -1.01 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 82.28 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.49 | 82.14 | -0.14 | *touch shot four* |
| `session_2026-06-19_12-25-55` | 173.51 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.41 | 173.05 | -0.46 | *cut shot four* |
| `session_2026-06-19_12-25-55` | 810.97 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 805.91 | -5.06 | *back foot drive good facing up* |
| `session_2026-06-19_12-25-55` | 832.73 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.74 | 831.89 | -0.84 | *back foot punch okay facing up back foot drive okay facing up* |
| `session_2026-06-19_12-25-55` | 860.39 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.66 | 859.04 | -1.35 | *cut shot four facing up* |
| `session_2026-06-19_12-25-55` | 877.00 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.49 | 875.93 | -1.07 | *back foot punch or facing up back foot punch good* |
| `session_2026-06-19_12-25-55` | 988.68 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.67 | 987.71 | -0.97 | *back foot punch okay facing up* |
| `session_2026-07-05_16-27-16` | 4.33 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 51.30 | +46.97 | *alright* |
| `session_2026-07-05_16-27-16` | 53.80 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 51.30 | -2.50 | *power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 89.89 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 97.37 | +7.48 | *fence edge facing up* |
| `session_2026-07-05_16-27-16` | 115.02 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.54 | 114.21 | -0.81 | *slog good* |
| `session_2026-07-05_16-27-16` | 160.88 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.47 | 161.02 | +0.14 | *power drive missed* |
| `session_2026-07-05_16-27-16` | 170.57 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.34 | 170.57 | +0.00 | *power drive edge* |
| `session_2026-07-05_16-27-16` | 212.30 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.71 | 211.64 | -0.66 | *power drive edge* |
| `session_2026-07-05_16-27-16` | 470.56 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 468.74 | -1.82 | *straight drive good good facing up* |
| `session_2026-07-05_16-27-16` | 498.94 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.50 | 499.19 | +0.25 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 517.47 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.53 | 517.47 | -0.00 | *power drive good* |
| `session_2026-07-05_16-27-16` | 528.21 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.54 | 528.26 | +0.05 | *power drive good* |
| `session_2026-07-05_16-27-16` | 534.36 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.49 | 534.12 | -0.24 | *push shot okay* |
| `session_2026-07-05_16-27-16` | 542.44 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.53 | 542.17 | -0.27 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 550.52 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.49 | 550.35 | -0.17 | *power drive good* |
| `session_2026-07-05_16-27-16` | 565.74 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.41 | 565.42 | -0.32 | *good shot okay* |
| `session_2026-07-05_16-27-16` | 573.71 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.54 | 573.21 | -0.50 | *power drive or* |
| `session_2026-07-05_16-27-16` | 598.25 | **DRIVE/DEFENCE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.54 | 598.31 | +0.06 | *no drive edge* |
| `session_2026-07-05_16-27-16` | 608.17 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.51 | 606.71 | -1.46 | *quick shot edge* |
| `session_2026-07-05_16-27-16` | 639.71 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.51 | 639.95 | +0.24 | *power shot good* |
| `session_2026-07-05_16-27-16` | 648.26 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.51 | 648.34 | +0.08 | *power drive good* |
| `session_2026-07-05_16-27-16` | 655.52 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.58 | 655.23 | -0.29 | *quick shot good end of round* |
| `session_2026-07-05_16-27-16` | 934.00 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.43 | 933.43 | -0.57 | *power drive good facing up power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 949.27 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.43 | 949.25 | -0.02 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 958.22 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.37 | 958.26 | +0.04 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 976.73 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.46 | 976.74 | +0.01 | *power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 992.00 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.40 | 991.67 | -0.33 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1000.80 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.35 | 1000.50 | -0.30 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1032.78 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.39 | 1032.96 | +0.18 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1043.02 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.49 | 1042.56 | -0.46 | *power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 1048.27 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.48 | 1048.01 | -0.26 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1058.11 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.38 | 1058.37 | +0.26 | *power drive good* |
| `session_2026-07-05_16-27-16` | 1067.52 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.46 | 1067.40 | -0.12 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1075.66 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.80 | 1074.97 | -0.69 | *make oh shot okay facing up power drive good* |
| `session_2026-07-05_16-27-16` | 1095.94 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1093.93 | -2.01 | *pull shot okay facing up* |
| `session_2026-07-05_16-27-16` | 1101.13 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.35 | 1101.17 | +0.04 | *power shot okay* |
| `session_2026-07-20_12-42-16` | 62.99 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.48 | 62.99 | +0.00 | *sweep shot okay* |
| `session_2026-07-20_12-42-16` | 78.12 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.37 | 78.12 | +0.00 | *sweep shot miss* |
| `session_2026-07-20_12-42-16` | 106.04 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.62 | 106.04 | +0.00 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 375.43 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 380.12 | +4.69 | *sweep shot miss facing up* |
| `session_2026-07-20_12-42-16` | 429.95 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.57 | 429.95 | +0.00 | *flip shot edge* |
| `session_2026-07-20_12-42-16` | 459.47 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 467.25 | +7.79 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 513.73 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.67 | 513.73 | +0.00 | *swipe shot okay* |
| `session_2026-07-20_12-42-16` | 557.88 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.72 | 557.88 | +0.00 | *straight shot good end of round* |
| `session_2026-07-20_12-42-16` | 749.59 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 753.46 | +3.87 | *slip shot okay facing up* |
| `session_2026-07-25_15-16-32` | 82.82 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.57 | 82.82 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 109.58 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.58 | 109.58 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 119.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.49 | 119.11 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 134.36 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.46 | 134.36 | +0.00 | *power drive good* |
| `session_2026-07-25_15-16-32` | 142.49 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.44 | 142.49 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 158.84 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.45 | 158.84 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 186.74 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.53 | 186.74 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 226.76 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.61 | 226.76 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 236.32 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.54 | 236.32 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 711.04 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.54 | 711.04 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 719.08 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.51 | 719.08 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 721.81 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 719.08 | -2.73 | *slog good facing up* |
| `session_2026-07-25_15-16-32` | 735.36 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.52 | 735.37 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 751.12 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.56 | 751.12 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 761.25 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.62 | 761.26 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 768.77 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.40 | 768.77 | +0.00 | *power drive good* |
| `session_2026-07-25_15-16-32` | 809.14 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.43 | 809.14 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 819.15 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.54 | 819.15 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 835.20 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.58 | 835.20 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 844.40 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.39 | 844.09 | -0.31 | *slog good* |
| `session_2026-07-25_15-16-32` | 857.54 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.49 | 857.54 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1043.07 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.38 | 1043.07 | +0.00 | *power drive okay facing up* |
| `session_2026-07-25_15-16-32` | 1052.24 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.48 | 1052.24 | +0.00 | *flick shot okay* |
| `session_2026-07-25_15-16-32` | 1061.78 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.45 | 1061.78 | +0.00 | *slog okay facing up* |
| `session_2026-07-25_15-16-32` | 1092.55 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.52 | 1092.55 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1101.77 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.38 | 1101.77 | +0.00 | *flick shot good* |
| `session_2026-07-25_15-16-32` | 1109.60 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.56 | 1109.60 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1137.55 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.43 | 1137.56 | +0.00 | *power drive terrible four facing up* |
| `session_2026-07-25_15-16-32` | 1179.12 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.61 | 1179.12 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1201.60 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.41 | 1201.60 | +0.00 | *power drive terrible facing up* |
| `session_2026-07-25_15-16-32` | 1212.40 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.52 | 1212.40 | +0.00 | *power drive good* |
| `session_2026-08-11_12-49-31` | 107.93 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.92 | 107.93 | +0.00 | *back foot punch good facing up cut shot okay* |
| `session_2026-08-11_12-49-31` | 150.83 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.50 | 150.89 | +0.06 | *cut shot four facing up* |
| `session_2026-08-11_12-49-31` | 194.92 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.35 | 194.61 | -0.31 | *touch up good* |
| `session_2026-08-11_12-49-31` | 689.61 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.47 | 689.61 | +0.00 | *back foot punch good facing up* |
| `session_2026-08-11_12-49-31` | 719.06 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.77 | 719.06 | +0.00 | *back foot punch okay* |
| `session_2026-08-11_12-49-31` | 1134.52 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1132.48 | -2.05 | *facing back foot punch good* |
| `session_2026-08-11_12-49-31` | 1155.67 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.79 | 1155.67 | +0.00 | *back foot defense good facing up cut shot miss* |
| `session_2026-08-21_12-50-53` | 100.66 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.37 | 100.67 | +0.00 | *back foot punch four* |
| `session_2026-08-21_12-50-53` | 172.13 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 169.05 | -3.08 | *facing up back foot punch miss* |
| `session_2026-08-21_12-50-53` | 538.55 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.59 | 538.55 | +0.00 | *back foot punch four facing up* |
| `session_2026-08-21_12-50-53` | 604.39 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.76 | 604.39 | +0.00 | *back foot punch miss* |
| `session_2026-08-21_12-50-53` | 609.36 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 604.39 | -4.97 | *facing up back foot punch okay* |
| `session_2026-08-21_12-50-53` | 626.70 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.64 | 626.70 | +0.00 | *back foot punch good* |
| `session_2026-08-21_12-50-53` | 640.80 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 635.46 | -5.35 | *facing up back foot punch okay* |
| `session_2026-08-21_12-50-53` | 647.85 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.84 | 647.85 | +0.00 | *glide pull* |
| `session_2026-08-21_12-50-53` | 687.22 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 679.57 | -7.65 | *glide good facing up* |
| `session_2026-08-21_12-50-53` | 695.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.40 | 695.30 | +0.00 | *back foot punch four facing up* |
| `session_2026-08-21_12-50-53` | 704.71 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 711.80 | +7.09 | *glide okay* |
| `session_2026-08-21_12-50-53` | 751.15 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.70 | 751.15 | +0.00 | *glide okay* |
| `session_2026-08-21_12-50-53` | 770.32 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.43 | 770.32 | +0.00 | *back foot punch edge facing up* |
| `session_2026-08-21_12-50-53` | 1037.31 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.64 | 1037.31 | +0.00 | *guide four facing up* |
| `session_2026-08-21_12-50-53` | 1089.59 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.50 | 1089.59 | +0.00 | *cut shot good* |
| `session_2026-08-21_12-50-53` | 1125.47 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.52 | 1125.47 | +0.00 | *back foot punch good* |
| `session_2026-08-21_12-50-53` | 1162.70 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1160.62 | -2.07 | *facing up guide good* |
| `session_2026-08-21_12-50-53` | 1187.47 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.59 | 1187.47 | +0.00 | *cut shot okay* |
| `session_2026-08-21_12-50-53` | 1236.81 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1228.81 | -8.00 | *guide four* |
| `session_2026-09-08_12-52-30` | 86.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 93.58 | +7.23 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 119.46 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.64 | 119.46 | +0.00 | *click shot or facing up* |
| `session_2026-09-08_12-52-30` | 124.67 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.82 | 124.67 | +0.00 | *glide okay facing up* |
| `session_2026-09-08_12-52-30` | 142.71 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.83 | 142.71 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 209.12 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 207.59 | -1.52 | *facing up cut shot okay* |
| `session_2026-09-08_12-52-30` | 254.51 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.75 | 254.51 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 269.40 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 260.92 | -8.48 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 576.33 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.56 | 576.33 | +0.00 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 594.85 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.22 | 594.58 | -0.26 | *back foot defense four* |
| `session_2026-09-08_12-52-30` | 594.58 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.22 | 594.58 | +0.00 | *facing up back foot defense okay* |
| `session_2026-09-08_12-52-30` | 707.62 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 718.52 | +10.90 | *glide good facing* |
| `session_2026-09-08_12-52-30` | 732.04 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.50 | 732.04 | +0.00 | *back foot punch okay facing up* |
| `session_2026-09-08_12-52-30` | 805.18 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.50 | 805.18 | +0.00 | *push up good facing up* |
| `session_2026-09-08_12-52-30` | 815.13 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 822.57 | +7.44 | *push up facing up* |
| `session_2026-09-08_12-52-30` | 1204.95 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1203.14 | -1.80 | *glide miss* |
| `session_2026-09-08_12-52-30` | 1217.89 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.71 | 1217.89 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 1227.88 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1230.17 | +2.30 | *squad good facing up back foot punch good* |
| `session_2026-09-08_12-52-30` | 1259.47 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.69 | 1259.48 | +0.00 | *back foot punch good facing up glide edge facing* |
| `session_2026-09-08_12-52-30` | 1289.69 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1280.66 | -9.03 | *wide miss* |
| `session_2026-09-08_12-52-30` | 1345.95 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.79 | 1345.95 | +0.00 | *back foot punch good* |
| `session_2026-09-17_12-48-47` | 118.16 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.31 | +8.15 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 135.02 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +8.66 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 138.93 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +4.75 | *straight drive edge* |
| `session_2026-09-17_12-48-47` | 177.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.74 | 177.87 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 185.69 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.50 | 185.70 | +0.00 | *straight drive poor* |
| `session_2026-09-17_12-48-47` | 254.51 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.64 | 254.51 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 560.86 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.42 | 560.86 | +0.00 | *on drive good facing up* |
| `session_2026-09-17_12-48-47` | 570.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.76 | 570.88 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 646.60 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.61 | 646.61 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 677.45 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 680.90 | +3.45 | *facing up switch shot okay* |
| `session_2026-09-17_12-48-47` | 699.56 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.58 | 699.57 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 752.91 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 754.72 | +1.81 | *facing up good shot okay in the ground* |
| `session_2026-09-17_12-48-47` | 1005.67 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1008.22 | +2.54 | *facing up flick shot okay* |
| `session_2026-09-17_12-48-47` | 1129.36 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.71 | 1129.36 | +0.00 | *push shot miss* |
| `session_2026-09-17_12-48-47` | 1146.77 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.74 | 1146.77 | +0.00 | *on drive 4 facing up* |
| `session_2026-09-17_12-48-47` | 1210.75 | **DRIVE/DEFENCE** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.38 | 1210.75 | +0.00 | *on drive good end of round end of sessions* |
| `session_2026-10-05_12-53-51` | 103.26 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 101.02 | -2.24 | *facing up back foot punch okay* |
| `session_2026-10-05_12-53-51` | 141.66 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.22 | +1.57 | *facing up cover drive okay* |
| `session_2026-10-05_12-53-51` | 207.21 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.51 | 206.97 | -0.25 | *glide good* |
| `session_2026-10-05_12-53-51` | 208.35 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.51 | 206.97 | -1.38 | *facing up glide good* |
| `session_2026-10-05_12-53-51` | 215.29 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 212.86 | -2.43 | *glide good* |
| `session_2026-10-05_12-53-51` | 584.77 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.46 | 584.77 | +0.00 | *push shot* |
| `session_2026-10-05_12-53-51` | 605.29 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.29 | 605.43 | +0.14 | *right edge* |
| `session_2026-10-05_12-53-51` | 615.09 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.66 | 615.09 | +0.00 | *facing up back foot defense okay* |
| `session_2026-10-05_12-53-51` | 738.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 745.74 | +6.80 | *facing up glide good* |
| `session_2026-10-05_12-53-51` | 1146.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1139.26 | -7.68 | *glide good* |
| `session_2026-10-05_12-53-51` | 1162.63 | **DEFLECTION/GUIDE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.23 | 1164.00 | +1.37 | *glide okay* |
| `session_2026-10-09_12-41-17` | 175.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.63 | 175.55 | +0.00 | *back foot defense or* |
| `session_2026-10-09_12-41-17` | 256.66 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.89 | 256.66 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 269.28 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.43 | 269.29 | +0.00 | *foot shot okay facing up back foot defense okay in the ground* |
| `session_2026-10-09_12-41-17` | 609.90 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.37 | 609.91 | +0.00 | *back foot defense poor* |
| `session_2026-10-09_12-41-17` | 620.65 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.61 | 620.65 | +0.00 | *back foot punch good* |
| `session_2026-10-09_12-41-17` | 674.49 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.45 | 674.49 | +0.00 | *back foot punch edge* |
| `session_2026-10-09_12-41-17` | 688.03 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.48 | 688.04 | +0.00 | *glide okay facing it* |
| `session_2026-10-09_12-41-17` | 696.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.69 | 696.30 | +0.00 | *crackle punch okay facing it* |
| `session_2026-10-09_12-41-17` | 704.35 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.39 | 704.35 | +0.00 | *glide edge* |
| `session_2026-10-09_12-41-17` | 1097.32 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.84 | 1097.32 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 1102.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1097.32 | -4.99 | *facing clive okay* |
| `session_2026-10-09_12-41-17` | 1152.49 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1144.86 | -7.64 | *guide miss* |

