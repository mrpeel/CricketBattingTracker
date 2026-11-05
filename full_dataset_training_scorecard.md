# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining, Joint 9-Class Hierarchical NLL + Cross-Family Power Drive Suppression + On-the-Fly Kinematic Augmentation (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.5, 1.0, 1.3], Rejection Threshold $\theta_{no\_shot} = 0.35$)  
**Holdout Test Sessions**: `session_2026-06-12_12-24-37, session_2026-06-19_12-25-55, session_2026-06-25_12-25-07, session_2026-06-28_11-28-09, session_2026-07-27_12-47-20, session_2026-08-08_10-43-42, session_2026-08-16_14-10-23, session_2026-08-22_14-25-31, session_2026-09-08_12-52-30, session_2026-09-17_12-48-47, session_2026-10-09_12-41-17, session_2026-10-17_11-47-47` (12 sessions)  
**Validation Sessions**: `session_2026-06-21_13-53-17, session_2026-06-27_14-12-40, session_2026-07-02_12-38-53, session_2026-07-24_12-52-29, session_2026-08-06_12-51-06, session_2026-08-17_12-51-22, session_2026-09-10_12-55-41, session_2026-10-04_15-30-15, session_2026-10-15_12-49-52` (9 sessions)  
**Quarantined Faulted Sessions**: `session_2026-05-30_15-04-41, session_2026-05-31_14-12-10, session_2026-07-11_12-51-39, session_2026-07-17_12-30-41, session_2026-07-18_13-44-09, session_2026-09-05_16-26-41, session_2026-09-06_12-14-46, session_2026-09-11_12-44-50` (8 sessions)  
**Training Sessions Count**: 71 physical sessions  
**Clean Benchmark Sessions Count**: 92 physical sessions  
**Total Dataset Duration**: 1662.0 minutes (27.7 hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch 16 (Best Val Macro-F1: 0.8091, Shot Acc: 85.57%, Val Loss: 1.5339, Stopped at Epoch 24)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-11-05_13-25-46.log`  
**Date**: 2026-11-05 14:21

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set (12 Sessions)** | **714** | **723** | **92.58%** (661/714) | **91.42%** (661/723) | **92.00%** |
| **Training Set Micro Average (71 Sessions)** | **4631** | **4539** | **89.72%** (4155/4631) | **91.54%** (4155/4539) | **90.62%** |
| 🏆 **Clean Benchmark Micro Average (92 Sessions)** | **5345** | **5262** | 🏆 **90.10%** (4816/5345) | 🏆 **91.52%** (4816/5262) | 🏆 **90.81%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (12 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 134 | 126 | 94.0% | 113 | **89.7%** | **84.3%** |
| **DRIVE/DEFENCE** | 196 | 181 | 92.3% | 145 | **80.1%** | **74.0%** |
| **GLANCE/FLICK** | 131 | 122 | 93.1% | 99 | **81.1%** | **75.6%** |
| **CUT/PUNCH** | 70 | 65 | 92.9% | 55 | **84.6%** | **78.6%** |
| **DEFLECTION/GUIDE** | 76 | 65 | 85.5% | 58 | **89.2%** | **76.3%** |
| **POWER DRIVE** | 48 | 45 | 93.8% | 33 | **73.3%** | **68.8%** |
| **SWEEP** | 59 | 57 | 96.6% | 55 | **96.5%** | **93.2%** |
| **OVERALL TOTAL** | **714** | **661** | **92.6%** | **558** | 🏆 **84.4%** | 🏆 **78.2%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (80 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1383 | 1245 | 90.0% | 1187 | **95.3%** | **85.8%** |
| **DRIVE/DEFENCE** | 1057 | 963 | 91.1% | 892 | **92.6%** | **84.4%** |
| **GLANCE/FLICK** | 845 | 761 | 90.1% | 702 | **92.2%** | **83.1%** |
| **CUT/PUNCH** | 586 | 521 | 88.9% | 501 | **96.2%** | **85.5%** |
| **DEFLECTION/GUIDE** | 254 | 205 | 80.7% | 201 | **98.0%** | **79.1%** |
| **POWER DRIVE** | 294 | 266 | 90.5% | 253 | **95.1%** | **86.1%** |
| **SWEEP** | 212 | 194 | 91.5% | 185 | **95.4%** | **87.3%** |
| **OVERALL TOTAL** | **4631** | **4155** | **89.7%** | **3921** | 🏆 **94.4%** | 🏆 **84.7%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 92 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1517 | 1371 | 90.4% | 1300 | **94.8%** | **85.7%** |
| **DRIVE/DEFENCE** | 1253 | 1144 | 91.3% | 1037 | **90.6%** | **82.8%** |
| **GLANCE/FLICK** | 976 | 883 | 90.5% | 801 | **90.7%** | **82.1%** |
| **CUT/PUNCH** | 656 | 586 | 89.3% | 556 | **94.9%** | **84.8%** |
| **DEFLECTION/GUIDE** | 330 | 270 | 81.8% | 259 | **95.9%** | **78.5%** |
| **POWER DRIVE** | 342 | 311 | 90.9% | 286 | **92.0%** | **83.6%** |
| **SWEEP** | 271 | 251 | 92.6% | 240 | **95.6%** | **88.6%** |
| **OVERALL TOTAL** | **5345** | **4816** | **90.1%** | **4479** | 🏆 **93.0%** | 🏆 **83.8%** |

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 4 | 75.0% | 75.0% | 75.0%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 58 | 93.4% | 98.3% | 95.8%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 96.4% | 96.4% | 96.4%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 40 | 70.6% | 90.0% | 79.1%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 41 | 68.9% | 75.6% | 72.1%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 94.8% | 93.2% | 94.0%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 51 | 94.1% | 94.1% | 94.1%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 58 | 90.3% | 96.6% | 93.3%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 89.9% | 96.9% | 93.2%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 61 | 100.0% | 93.4% | 96.6%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 55 | 96.5% | 100.0% | 98.2%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 56 | 93.0% | 94.6% | 93.8%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 59 | 96.6% | 96.6% | 96.6%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 60 | 100.0% | 96.7% | 98.3%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 52 | 98.0% | 92.3% | 95.0%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 57 | 96.5% | 96.5% | 96.5%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 54 | 91.4% | 98.1% | 94.6%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 56 | 96.2% | 89.3% | 92.6%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 60 | 100.0% | 96.7% | 98.3%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 55 | 100.0% | 92.7% | 96.2%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 19 | 30.4% | 89.5% | 45.3%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 61 | 66 | 90.2% | 83.3% | 86.6%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 37 | 44 | 91.9% | 77.3% | 84.0%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 58 | 59 | 70.7% | 69.5% | 70.1%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 96.5% | 91.7% | 94.0%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 61 | 63 | 98.4% | 95.2% | 96.8%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 57 | 98.2% | 94.7% | 96.4%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 44 | 46 | 86.4% | 82.6% | 84.4%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 54 | 87.3% | 88.9% | 88.1%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 26 | 88.9% | 92.3% | 90.6%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 49 | 93.9% | 93.9% | 93.9%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 59 | 82.0% | 84.7% | 83.3%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 58 | 91.9% | 98.3% | 95.0%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 62 | 93.4% | 91.9% | 92.7%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 70 | 87.7% | 91.4% | 89.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 69 | 97.0% | 92.8% | 94.8%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 69 | 91.3% | 91.3% | 91.3%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 64 | 92.5% | 96.9% | 94.7%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 92.3% | 89.6% | 90.9%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 66 | 96.6% | 84.8% | 90.3%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 57 | 87.5% | 86.0% | 86.7%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 64 | 58 | 90.6% | 100.0% | 95.1%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 63 | 93.9% | 98.4% | 96.1%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 48 | 81.5% | 91.7% | 86.3%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 65 | 61 | 89.2% | 95.1% | 92.1%
| `session_2026-09-06_11-41-57` | Training | 1.8 | 7 | 6 | 85.7% | 100.0% | 92.3%
| `session_2026-09-06_12-35-47` | Training | 5.3 | 27 | 25 | 92.6% | 100.0% | 96.2%
| `session_2026-09-07_12-29-10` | Training | 20.3 | 60 | 53 | 73.3% | 83.0% | 77.9%
| `session_2026-09-14_12-56-40` | Training | 21.2 | 53 | 57 | 96.2% | 89.5% | 92.7%
| `session_2026-09-18_12-48-53` | Training | 20.5 | 68 | 66 | 94.1% | 97.0% | 95.5%
| `session_2026-09-30_12-52-29` | Training | 20.2 | 63 | 61 | 92.1% | 95.1% | 93.5%
| `session_2026-10-05_12-53-51` | Training | 20.6 | 67 | 63 | 85.1% | 90.5% | 87.7%
| `session_2026-10-06_12-49-35` | Training | 24.2 | 73 | 69 | 89.0% | 94.2% | 91.5%
| `session_2026-10-08_12-55-02` | Training | 20.6 | 69 | 70 | 82.6% | 81.4% | 82.0%
| `session_2026-10-16_12-59-39` | Training | 19.6 | 69 | 67 | 87.0% | 89.6% | 88.2%
| `session_2026-10-18_14-46-16` | Training | 19.2 | 64 | 65 | 87.5% | 86.2% | 86.8%
| `session_2026-10-19_12-47-59` | Training | 19.4 | 67 | 70 | 92.5% | 88.6% | 90.5%
| `session_2026-10-20_12-39-32` | Training | 18.9 | 70 | 66 | 88.6% | 93.9% | 91.2%
| `session_2026-10-22_12-57-41` | Training | 19.7 | 73 | 69 | 89.0% | 94.2% | 91.5%
| `session_2026-10-23_13-02-03` | Training | 20.4 | 62 | 66 | 88.7% | 83.3% | 85.9%
| `session_2026-10-26_12-57-14` | Training | 27.0 | 64 | 59 | 79.7% | 86.4% | 82.9%
| `session_2026-10-27_12-44-30` | Training | 18.9 | 72 | 63 | 81.9% | 93.7% | 87.4%
| `session_2026-10-29_12-19-24` | Training | 19.6 | 72 | 72 | 90.3% | 90.3% | 90.3%
| `session_2026-10-30_12-49-13` | Training | 22.0 | 66 | 72 | 95.5% | 87.5% | 91.3%
| `session_2026-11-01_15-20-45` | Training | 20.6 | 77 | 74 | 90.9% | 94.6% | 92.7%
| `session_2026-11-02_10-53-03` | Training | 15.3 | 67 | 62 | 88.1% | 95.2% | 91.5%
| `session_2026-11-03_16-38-01` | Training | 20.7 | 75 | 70 | 82.7% | 88.6% | 85.5%
| `session_2026-11-05_12-59-39` | Training | 20.4 | 58 | 56 | 82.8% | 85.7% | 84.2%
| `session_2026-06-21_13-53-17` | 🔹 VALIDATION | 20.2 | 55 | 60 | 98.2% | 90.0% | 93.9%
| `session_2026-06-27_14-12-40` | 🔹 VALIDATION | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-07-02_12-38-53` | 🔹 VALIDATION | 20.9 | 59 | 58 | 98.3% | 100.0% | 99.1%
| `session_2026-07-24_12-52-29` | 🔹 VALIDATION | 17.9 | 52 | 52 | 78.8% | 78.8% | 78.8%
| `session_2026-08-06_12-51-06` | 🔹 VALIDATION | 17.0 | 58 | 58 | 84.5% | 84.5% | 84.5%
| `session_2026-08-17_12-51-22` | 🔹 VALIDATION | 19.2 | 64 | 58 | 85.9% | 94.8% | 90.2%
| `session_2026-09-10_12-55-41` | 🔹 VALIDATION | 19.4 | 60 | 56 | 88.3% | 94.6% | 91.4%
| `session_2026-10-04_15-30-15` | 🔹 VALIDATION | 15.0 | 67 | 65 | 92.5% | 95.4% | 93.9%
| `session_2026-10-15_12-49-52` | 🔹 VALIDATION | 20.0 | 58 | 60 | 93.1% | 90.0% | 91.5%
| `session_2026-06-12_12-24-37` | 🌟 HOLDOUT TEST | 20.9 | 70 | 70 | 97.1% | 97.1% | 97.1%
| `session_2026-06-19_12-25-55` | 🌟 HOLDOUT TEST | 16.7 | 56 | 58 | 98.2% | 94.8% | 96.5%
| `session_2026-06-25_12-25-07` | 🌟 HOLDOUT TEST | 21.2 | 65 | 64 | 93.8% | 95.3% | 94.6%
| `session_2026-06-28_11-28-09` | 🌟 HOLDOUT TEST | 19.8 | 52 | 54 | 96.2% | 92.6% | 94.3%
| `session_2026-07-27_12-47-20` | 🌟 HOLDOUT TEST | 18.1 | 53 | 54 | 90.6% | 88.9% | 89.7%
| `session_2026-08-08_10-43-42` | 🌟 HOLDOUT TEST | 29.8 | 77 | 83 | 89.6% | 83.1% | 86.2%
| `session_2026-08-16_14-10-23` | 🌟 HOLDOUT TEST | 11.8 | 50 | 50 | 98.0% | 98.0% | 98.0%
| `session_2026-08-22_14-25-31` | 🌟 HOLDOUT TEST | 12.0 | 51 | 48 | 90.2% | 95.8% | 92.9%
| `session_2026-09-08_12-52-30` | 🌟 HOLDOUT TEST | 22.7 | 57 | 56 | 84.2% | 85.7% | 85.0%
| `session_2026-09-17_12-48-47` | 🌟 HOLDOUT TEST | 20.3 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-10-09_12-41-17` | 🌟 HOLDOUT TEST | 20.1 | 51 | 59 | 96.1% | 83.1% | 89.1%
| `session_2026-10-17_11-47-47` | 🌟 HOLDOUT TEST | 18.9 | 70 | 67 | 87.1% | 91.0% | 89.1%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **SUBCLASS_CONFUSION** | **51** | DRIVE/DEFENCE (25), POWER DRIVE (12), GLANCE/FLICK (10) |
| **NOT_DETECTED (MISSING_CANDIDATE)** | **49** | DRIVE/DEFENCE (14), GLANCE/FLICK (11), DEFLECTION/GUIDE (10) |
| **VERTICAL_BAT_CONFUSION** | **21** | PULL/HOOK/SLOG (11), CUT/PUNCH (10) |
| **SWEEP_CONFUSION** | **19** | GLANCE/FLICK (9), DRIVE/DEFENCE (6), SWEEP (2) |
| **CROSS_BAT_CONFUSION** | **13** | DRIVE/DEFENCE (7), GLANCE/FLICK (3), DEFLECTION/GUIDE (3) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-06-12_12-24-37` | 138.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 132.22 | -6.13 | *pull shot four facing up* |
| `session_2026-06-12_12-24-37` | 197.07 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 195.39 | -1.68 | *flick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 632.67 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 627.36 | -5.31 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 654.71 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.58 | 654.65 | -0.06 | *good shot okay facing up* |
| `session_2026-06-12_12-24-37` | 1091.77 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.56 | 1092.03 | +0.26 | *pull shot okay facing up* |
| `session_2026-06-12_12-24-37` | 1134.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.74 | 1134.83 | -0.00 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 1234.72 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.83 | 1234.11 | -0.61 | *which shot okay facing up* |
| `session_2026-06-19_12-25-55` | 45.30 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.66 | 44.29 | -1.01 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 82.28 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.55 | 82.14 | -0.14 | *touch shot four* |
| `session_2026-06-19_12-25-55` | 173.51 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.91 | 173.05 | -0.46 | *cut shot four* |
| `session_2026-06-19_12-25-55` | 500.81 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.74 | 500.29 | -0.52 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 515.69 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.76 | 515.62 | -0.07 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 537.24 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.84 | 537.01 | -0.23 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 595.40 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.79 | 595.25 | -0.15 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 810.97 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 805.91 | -5.06 | *back foot drive good facing up* |
| `session_2026-06-19_12-25-55` | 860.39 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.77 | 859.04 | -1.35 | *cut shot four facing up* |
| `session_2026-06-25_12-25-07` | 12.82 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 63.80 | +50.98 | *alright let's get going* |
| `session_2026-06-25_12-25-07` | 53.84 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 63.80 | +9.96 | *alright facing up* |
| `session_2026-06-25_12-25-07` | 65.20 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.68 | 63.80 | -1.40 | *flick shot okay facing up* |
| `session_2026-06-25_12-25-07` | 101.08 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.84 | 100.93 | -0.15 | *flip shot okay* |
| `session_2026-06-25_12-25-07` | 142.89 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.86 | 142.99 | +0.10 | *forward defense okay* |
| `session_2026-06-25_12-25-07` | 222.57 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.50 | 222.56 | -0.01 | *quick shot good* |
| `session_2026-06-25_12-25-07` | 602.93 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.68 | 602.43 | -0.50 | *on drive good* |
| `session_2026-06-25_12-25-07` | 629.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.63 | 628.45 | -1.09 | *on drive pour* |
| `session_2026-06-25_12-25-07` | 668.45 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.47 | 668.49 | +0.04 | *good shot okay* |
| `session_2026-06-25_12-25-07` | 1019.92 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1027.93 | +8.01 | *alright match day bat facing up* |
| `session_2026-06-25_12-25-07` | 1063.39 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.57 | 1063.17 | -0.22 | *quick shot okay* |
| `session_2026-06-25_12-25-07` | 1129.03 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1122.72 | -6.31 | *flick shot good facing up* |
| `session_2026-06-25_12-25-07` | 1138.55 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.70 | 1138.30 | -0.25 | *pull shot miss* |
| `session_2026-06-28_11-28-09` | 206.55 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.78 | 206.44 | -0.11 | *weep shot okay* |
| `session_2026-06-28_11-28-09` | 216.85 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.93 | 216.83 | -0.02 | *pull shot ah sweep shot okay* |
| `session_2026-06-28_11-28-09` | 237.76 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.43 | 237.17 | -0.59 | *on drive good* |
| `session_2026-06-28_11-28-09` | 303.94 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.71 | 304.02 | +0.08 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 596.17 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.76 | 596.52 | +0.35 | *slip shot good* |
| `session_2026-06-28_11-28-09` | 605.08 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.89 | 605.25 | +0.17 | *flick shot good* |
| `session_2026-06-28_11-28-09` | 673.45 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 671.90 | -1.55 | *forward defense okay facing up* |
| `session_2026-06-28_11-28-09` | 703.39 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.52 | 703.27 | -0.12 | *flick shot good* |
| `session_2026-06-28_11-28-09` | 756.41 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.79 | 756.62 | +0.21 | *slip shot miss in the round* |
| `session_2026-06-28_11-28-09` | 996.15 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1004.92 | +8.77 | *fence four* |
| `session_2026-06-28_11-28-09` | 1035.39 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.75 | 1035.35 | -0.04 | *slip shot okay* |
| `session_2026-06-28_11-28-09` | 1097.21 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.69 | 1096.96 | -0.25 | *slip shot okay* |
| `session_2026-06-28_11-28-09` | 1128.90 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.51 | 1128.66 | -0.24 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 1139.97 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.78 | 1140.13 | +0.16 | *slip shot miss* |
| `session_2026-06-28_11-28-09` | 1175.13 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1170.49 | -4.64 | *losing up sweep shot four* |
| `session_2026-07-27_12-47-20` | 49.45 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 67.63 | +18.17 | *back defense or* |
| `session_2026-07-27_12-47-20` | 58.09 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 67.63 | +9.53 | *back fence good* |
| `session_2026-07-27_12-47-20` | 473.17 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 479.11 | +5.94 | *click shot okay facing up* |
| `session_2026-07-27_12-47-20` | 593.84 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 588.87 | -4.97 | *quick shot miss* |
| `session_2026-07-27_12-47-20` | 623.75 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.44 | 623.75 | +0.00 | *pull shot okay* |
| `session_2026-07-27_12-47-20` | 995.06 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 999.57 | +4.51 | *back foot defense good facing up* |
| `session_2026-07-27_12-47-20` | 1041.11 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.58 | 1041.11 | +0.00 | *which shot good* |
| `session_2026-08-08_10-43-42` | 4.03 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.03 | +71.00 | *alright* |
| `session_2026-08-08_10-43-42` | 93.73 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.43 | 93.41 | -0.32 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 547.09 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.83 | 547.09 | +0.00 | *power drive flog good* |
| `session_2026-08-08_10-43-42` | 550.07 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 547.09 | -2.98 | *facing up power drive good* |
| `session_2026-08-08_10-43-42` | 569.82 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.55 | 569.91 | +0.09 | *power drive good* |
| `session_2026-08-08_10-43-42` | 576.77 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.63 | 576.77 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 592.99 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.67 | 592.99 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 614.23 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.63 | 614.23 | +0.00 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 639.20 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.69 | 639.20 | +0.00 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 646.99 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.75 | 646.99 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 650.49 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 646.99 | -3.49 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 698.30 | **DRIVE/DEFENCE** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.94 | 698.30 | +0.00 | *facing up on drive good* |
| `session_2026-08-08_10-43-42` | 1005.67 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.76 | 1005.67 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 1023.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.67 | 1023.83 | +0.00 | *pull shot pour* |
| `session_2026-08-08_10-43-42` | 1065.54 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.61 | 1065.54 | +0.00 | *power drive okay facing up forward defense good* |
| `session_2026-08-08_10-43-42` | 1077.47 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.65 | 1077.39 | -0.08 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 1102.73 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.60 | 1102.74 | +0.00 | *power drive good facing up* |
| `session_2026-08-08_10-43-42` | 1111.81 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.68 | 1111.81 | +0.00 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 1148.89 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.97 | 1148.90 | +0.00 | *power drive good facing up pull shot okay* |
| `session_2026-08-08_10-43-42` | 1570.64 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1580.04 | +9.40 | *guide good* |
| `session_2026-08-08_10-43-42` | 1756.25 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1753.03 | -3.22 | *guide okay* |
| `session_2026-08-16_14-10-23` | 41.96 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.53 | 41.96 | +0.00 | *straight shot okay* |
| `session_2026-08-16_14-10-23` | 88.11 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.80 | 88.11 | +0.00 | *swipe shot okay* |
| `session_2026-08-16_14-10-23` | 154.34 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.82 | 154.34 | +0.00 | *slip shot okay* |
| `session_2026-08-16_14-10-23` | 198.42 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.82 | 198.42 | +0.00 | *on drive okay* |
| `session_2026-08-16_14-10-23` | 207.71 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.68 | 207.71 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 315.28 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.85 | 315.28 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 324.98 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.84 | 324.98 | +0.00 | *flick shot good* |
| `session_2026-08-16_14-10-23` | 349.05 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.79 | 349.05 | +0.00 | *quick shot okay* |
| `session_2026-08-16_14-10-23` | 546.84 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.75 | 546.84 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 560.04 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 568.24 | +8.19 | *pull shot okay* |
| `session_2026-08-16_14-10-23` | 568.24 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.90 | 568.24 | +0.00 | *sweep shot pull* |
| `session_2026-08-16_14-10-23` | 642.60 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.81 | 642.60 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 652.74 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.94 | 652.74 | +0.00 | *straight shot okay* |
| `session_2026-08-22_14-25-31` | 59.97 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.75 | 59.97 | +0.00 | *back foot punch good facing up* |
| `session_2026-08-22_14-25-31` | 115.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 113.39 | -2.54 | *glide four* |
| `session_2026-08-22_14-25-31` | 186.91 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 184.91 | -1.99 | *facing back foot punch okay* |
| `session_2026-08-22_14-25-31` | 328.01 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 324.85 | -3.17 | *facing up cut shot four* |
| `session_2026-08-22_14-25-31` | 363.73 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.97 | 363.73 | +0.00 | *back foot punch okay facing up cut shot okay* |
| `session_2026-08-22_14-25-31` | 414.57 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.98 | 414.57 | +0.00 | *alright foot defense okay end of round* |
| `session_2026-08-22_14-25-31` | 584.56 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.78 | 584.56 | +0.00 | *guide okay facing up* |
| `session_2026-08-22_14-25-31` | 649.80 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.94 | 649.80 | +0.00 | *back foot punch okay facing up* |
| `session_2026-08-22_14-25-31` | 685.21 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.68 | 685.22 | +0.00 | *that's a punch four* |
| `session_2026-09-08_12-52-30` | 86.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 93.58 | +7.23 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 119.46 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.88 | 119.46 | +0.00 | *click shot or facing up* |
| `session_2026-09-08_12-52-30` | 124.67 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.76 | 124.67 | +0.00 | *glide okay facing up* |
| `session_2026-09-08_12-52-30` | 142.71 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.87 | 142.71 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 209.12 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 207.59 | -1.52 | *facing up cut shot okay* |
| `session_2026-09-08_12-52-30` | 269.40 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 260.92 | -8.48 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 576.33 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.45 | 576.33 | +0.00 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 594.85 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.23 | 594.58 | -0.26 | *back foot defense four* |
| `session_2026-09-08_12-52-30` | 594.58 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.23 | 594.58 | +0.00 | *facing up back foot defense okay* |
| `session_2026-09-08_12-52-30` | 738.76 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.78 | 738.76 | +0.00 | *back foot punch good facing up cut shot pour* |
| `session_2026-09-08_12-52-30` | 805.18 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.97 | 805.18 | +0.00 | *push up good facing up* |
| `session_2026-09-08_12-52-30` | 815.13 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 822.57 | +7.44 | *push up facing up* |
| `session_2026-09-08_12-52-30` | 1204.95 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1203.14 | -1.80 | *glide miss* |
| `session_2026-09-08_12-52-30` | 1217.89 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.80 | 1217.89 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 1227.88 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1230.17 | +2.30 | *squad good facing up back foot punch good* |
| `session_2026-09-08_12-52-30` | 1259.47 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.92 | 1259.48 | +0.00 | *back foot punch good facing up glide edge facing* |
| `session_2026-09-08_12-52-30` | 1289.69 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1280.66 | -9.03 | *wide miss* |
| `session_2026-09-08_12-52-30` | 1345.95 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.89 | 1345.95 | +0.00 | *back foot punch good* |
| `session_2026-09-17_12-48-47` | 118.16 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.31 | +8.15 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 135.02 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +8.66 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 138.93 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +4.75 | *straight drive edge* |
| `session_2026-09-17_12-48-47` | 177.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.74 | 177.87 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 254.51 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.76 | 254.51 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 298.25 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.41 | 299.71 | +1.46 | *facing up on drive good* |
| `session_2026-09-17_12-48-47` | 560.86 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.67 | 560.86 | +0.00 | *on drive good facing up* |
| `session_2026-09-17_12-48-47` | 570.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.75 | 570.88 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 646.60 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.64 | 646.61 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 677.45 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 680.90 | +3.45 | *facing up switch shot okay* |
| `session_2026-09-17_12-48-47` | 699.56 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.56 | 699.57 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 752.91 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 754.72 | +1.81 | *facing up good shot okay in the ground* |
| `session_2026-09-17_12-48-47` | 1005.67 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1017.22 | +11.55 | *facing up flick shot okay* |
| `session_2026-09-17_12-48-47` | 1129.36 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.77 | 1129.36 | +0.00 | *push shot miss* |
| `session_2026-09-17_12-48-47` | 1146.77 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.80 | 1146.77 | +0.00 | *on drive 4 facing up* |
| `session_2026-09-17_12-48-47` | 1210.75 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.71 | 1210.75 | +0.00 | *on drive good end of round end of sessions* |
| `session_2026-10-09_12-41-17` | 175.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.66 | 175.55 | +0.00 | *back foot defense or* |
| `session_2026-10-09_12-41-17` | 233.34 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 226.52 | -6.83 | *flick shot okay* |
| `session_2026-10-09_12-41-17` | 256.66 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.85 | 256.66 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 269.28 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.60 | 269.29 | +0.00 | *foot shot okay facing up back foot defense okay in the ground* |
| `session_2026-10-09_12-41-17` | 609.90 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.75 | 609.91 | +0.00 | *back foot defense poor* |
| `session_2026-10-09_12-41-17` | 665.70 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.86 | 665.70 | +0.00 | *back foot defense four* |
| `session_2026-10-09_12-41-17` | 674.49 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.70 | 674.49 | +0.00 | *back foot punch edge* |
| `session_2026-10-09_12-41-17` | 696.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.90 | 696.30 | +0.00 | *crackle punch okay facing it* |
| `session_2026-10-09_12-41-17` | 704.35 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.50 | 704.35 | +0.00 | *glide edge* |
| `session_2026-10-09_12-41-17` | 1002.62 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.76 | 1002.62 | +0.00 | *back foot defense good* |
| `session_2026-10-09_12-41-17` | 1097.32 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.54 | 1097.32 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 1102.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1097.32 | -4.99 | *facing clive okay* |
| `session_2026-10-09_12-41-17` | 1152.49 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.44 | 1152.49 | +0.00 | *guide miss* |
| `session_2026-10-17_11-47-47` | 122.63 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 120.27 | -2.36 | *facing up glance good* |
| `session_2026-10-17_11-47-47` | 140.46 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 135.17 | -5.29 | *facing up oh blanks miss* |
| `session_2026-10-17_11-47-47` | 167.64 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 166.07 | -1.57 | *lacing up flick shot good* |
| `session_2026-10-17_11-47-47` | 216.38 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 213.49 | -2.88 | *facing up on drive okay facing up* |
| `session_2026-10-17_11-47-47` | 233.82 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.51 | 233.82 | +0.00 | *back foot defense or facing up* |
| `session_2026-10-17_11-47-47` | 248.77 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.53 | 248.78 | +0.00 | *good shot okay* |
| `session_2026-10-17_11-47-47` | 609.03 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 605.40 | -3.63 | *facing up glance miss* |
| `session_2026-10-17_11-47-47` | 631.08 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 634.35 | +3.27 | *facing up pull shot okay* |
| `session_2026-10-17_11-47-47` | 641.00 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.57 | 641.00 | +0.00 | *flick shot okay facing up* |
| `session_2026-10-17_11-47-47` | 968.86 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 963.65 | -5.20 | *facing up pull shot miss* |
| `session_2026-10-17_11-47-47` | 1016.02 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1010.32 | -5.69 | *facing up pull shot good* |
| `session_2026-10-17_11-47-47` | 1048.96 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1055.30 | +6.34 | *facing up pull shot okay* |


---

## 🔍 Stage 3 Rule Health & Jev Shadow Audit
- **Config Version**: `v1.1.0` ([`stage3_rules_config.json`](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/stage3_rules_config.json))
- **Jev Shadow Auditor (`jev-1.13`, `v1.1.0-mount-aware-1q`)**: `0` cache hits, `336` live calls (median latency `412 ms`, estimated cost `$0.0161 USD`)

### 1. Stage 3 Rule Health & Shadow Telemetry Table
| Rule ID | State | Clean Benchmark Fires (89s) | Helped / Hurt | **Clean Net Impact** | Holdout Fires (12s) | **Holdout Net Impact** | Rule Precision (%) | Jev Agreement (%) | Health Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `bat_vertical_guard_rule1` | **ENABLED** | 0 | `+0 / -0` | **+0 shots** | 0 | **+0 shots** | 100.0% | 100.0% | ℹ️ DORMANT (SAFE GUARD) |
| `bat_ahrs_glance_rule2` | **ENABLED** | 0 | `+0 / -0` | **+0 shots** | 0 | **+0 shots** | 100.0% | 100.0% | ℹ️ DORMANT (SAFE GUARD) |
| `non_bat_sweep_to_glance` | SHADOW | 11 | `+5 / -5` | **+0 shots** | 3 | **-3 shots** | 45.5% | 0.0% | ⏸️ DISABLED (Net +0) |
| `s1_ahrs_flat_bat` | SHADOW | 76 | `+1 / -72` | **-71 shots** | 29 | **-24 shots** | 2.6% | 0.0% | ⏸️ DISABLED (Net -71) |
| `s2_power_drive_vs_pull` | SHADOW | 7 | `+1 / -6` | **-5 shots** | 0 | **+0 shots** | 14.3% | 0.0% | ⏸️ DISABLED (Net -5) |
| `s3_cut_punch_recovery` | SHADOW | 0 | `+0 / -0` | **+0 shots** | 0 | **+0 shots** | 100.0% | 100.0% | ⏸️ DISABLED (Net +0) |

### 2. Missed-Regime Clusters (Validation + Holdout Shots Where TCN Missed & Jev Agreed with GT)
| TCN Prediction | True GT + Jev Class | Sensor Mount | Shot Count | Sample Shots |
|---|---|---|:---:|---|
| **GLANCE/FLICK** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 12 | `session_2026-09-10_12-55-41`@694.1s (conf 0.95), `session_2026-09-17_12-48-47`@177.9s (conf 0.96), `session_2026-09-17_12-48-47`@254.5s (conf 0.92) |
| **GLANCE/FLICK** | **DRIVE/DEFENCE** | `NONE` | 9 | `session_2026-06-27_14-12-40`@480.8s (conf 0.98), `session_2026-06-27_14-12-40`@634.2s (conf 0.98), `session_2026-06-27_14-12-40`@852.4s (conf 0.99) |
| **CUT/PUNCH** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 8 | `session_2026-09-10_12-55-41`@141.5s (conf 0.91), `session_2026-09-10_12-55-41`@150.5s (conf 0.85), `session_2026-09-10_12-55-41`@204.0s (conf 0.92) |
| **SWEEP** | **DRIVE/DEFENCE** | `WRIST` | 6 | `session_2026-08-16_14-10-23`@42.0s (conf 0.94), `session_2026-08-16_14-10-23`@207.7s (conf 1.0), `session_2026-08-16_14-10-23`@315.3s (conf 1.0) |
| **CUT/PUNCH** | **DRIVE/DEFENCE** | `WRIST` | 4 | `session_2026-07-24_12-52-29`@132.8s (conf 0.8), `session_2026-08-22_14-25-31`@60.0s (conf 0.72), `session_2026-08-22_14-25-31`@649.8s (conf 0.93) |
| **GLANCE/FLICK** | **DRIVE/DEFENCE** | `WRIST` | 3 | `session_2026-08-17_12-51-22`@158.1s (conf 0.98), `session_2026-08-17_12-51-22`@1121.4s (conf 0.99), `session_2026-08-16_14-10-23`@198.4s (conf 0.98) |
| **DEFLECTION/GUIDE** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 3 | `session_2026-10-09_12-41-17`@609.9s (conf 0.94), `session_2026-10-09_12-41-17`@665.7s (conf 0.63), `session_2026-10-09_12-41-17`@1002.6s (conf 0.81) |
| **CUT/PUNCH** | **DRIVE/DEFENCE** | `NONE` | 2 | `session_2026-06-21_13-53-17`@563.0s (conf 0.8), `session_2026-06-21_13-53-17`@981.3s (conf 0.88) |
| **DEFLECTION/GUIDE** | **DRIVE/DEFENCE** | `WRIST` | 1 | `session_2026-07-24_12-52-29`@935.2s (conf 0.59) |
| **PULL/HOOK/SLOG** | **DRIVE/DEFENCE** | `WRIST` | 1 | `session_2026-08-06_12-51-06`@95.0s (conf 0.8) |
| **POWER DRIVE** | **DRIVE/DEFENCE** | `WRIST` | 1 | `session_2026-08-06_12-51-06`@540.8s (conf 0.71) |
| **PULL/HOOK/SLOG** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 1 | `session_2026-10-15_12-49-52`@607.6s (conf 0.93) |

### 3. Validation Threshold Drift & Calibration Check
- ✅ **All Stage 3 rule thresholds are optimal** on the 9-session Validation Set (no perturbation gains ≥ 2 shots).
