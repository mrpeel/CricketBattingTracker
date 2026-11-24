# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining, Joint 9-Class Hierarchical NLL + Cross-Family Power Drive Suppression + On-the-Fly Kinematic Augmentation (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.5, 1.0, 1.3], Rejection Threshold $\theta_{no\_shot} = 0.35$)  
**Holdout Test Sessions**: `session_2026-06-12_12-24-37, session_2026-06-19_12-25-55, session_2026-06-25_12-25-07, session_2026-06-28_11-28-09, session_2026-07-27_12-47-20, session_2026-08-08_10-43-42, session_2026-08-16_14-10-23, session_2026-08-22_14-25-31, session_2026-09-08_12-52-30, session_2026-09-17_12-48-47, session_2026-10-09_12-41-17, session_2026-10-17_11-47-47` (12 sessions)  
**Validation Sessions**: `session_2026-06-21_13-53-17, session_2026-06-27_14-12-40, session_2026-07-02_12-38-53, session_2026-07-24_12-52-29, session_2026-08-06_12-51-06, session_2026-08-17_12-51-22, session_2026-09-10_12-55-41, session_2026-10-04_15-30-15, session_2026-10-15_12-49-52` (9 sessions)  
**Quarantined Faulted Sessions**: `session_2026-05-30_15-04-41, session_2026-05-31_14-12-10, session_2026-07-11_12-51-39, session_2026-07-12_11-23-59, session_2026-07-17_12-30-41, session_2026-07-18_13-44-09, session_2026-07-21_12-43-37, session_2026-09-05_16-26-41, session_2026-09-06_12-14-46, session_2026-09-11_12-44-50, session_2026-11-16_12-45-46` (11 sessions)  
**Training Sessions Count**: 79 physical sessions  
**Clean Benchmark Sessions Count**: 100 physical sessions  
**Total Dataset Duration**: 1813.8 minutes (30.2 hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch 10 (Best Val Macro-F1: 0.8786, Shot Acc: 91.22%, Val Loss: 1.1989, Stopped at Epoch 24)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-11-24_12-56-47.log`  
**Date**: 2026-11-24 14:12

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set (12 Sessions)** | **769** | **771** | **96.23%** (740/769) | **95.98%** (740/771) | **96.10%** |
| **Training Set Micro Average (79 Sessions)** | **5465** | **5575** | **96.69%** (5284/5465) | **94.78%** (5284/5575) | **95.72%** |
| 🏆 **Clean Benchmark Micro Average (100 Sessions)** | **6234** | **6346** | 🏆 **96.63%** (6024/6234) | 🏆 **94.93%** (6024/6346) | 🏆 **95.77%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (12 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 142 | 140 | 98.6% | 126 | **90.0%** | **88.7%** |
| **DRIVE/DEFENCE** | 182 | 170 | 93.4% | 123 | **72.4%** | **67.6%** |
| **GLANCE/FLICK** | 129 | 127 | 98.4% | 114 | **89.8%** | **88.4%** |
| **CUT/PUNCH** | 120 | 120 | 100.0% | 116 | **96.7%** | **96.7%** |
| **DEFLECTION/GUIDE** | 79 | 67 | 84.8% | 63 | **94.0%** | **79.7%** |
| **POWER DRIVE** | 50 | 49 | 98.0% | 45 | **91.8%** | **90.0%** |
| **SWEEP** | 67 | 67 | 100.0% | 63 | **94.0%** | **94.0%** |
| **OVERALL TOTAL** | **769** | **740** | **96.2%** | **650** | 🏆 **87.8%** | 🏆 **84.5%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (88 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1465 | 1434 | 97.9% | 1335 | **93.1%** | **91.1%** |
| **DRIVE/DEFENCE** | 1168 | 1107 | 94.8% | 948 | **85.6%** | **81.2%** |
| **GLANCE/FLICK** | 1040 | 1017 | 97.8% | 958 | **94.2%** | **92.1%** |
| **CUT/PUNCH** | 993 | 972 | 97.9% | 960 | **98.8%** | **96.7%** |
| **DEFLECTION/GUIDE** | 246 | 214 | 87.0% | 206 | **96.3%** | **83.7%** |
| **POWER DRIVE** | 309 | 301 | 97.4% | 266 | **88.4%** | **86.1%** |
| **SWEEP** | 244 | 239 | 98.0% | 229 | **95.8%** | **93.9%** |
| **OVERALL TOTAL** | **5465** | **5284** | **96.7%** | **4902** | 🏆 **92.8%** | 🏆 **89.7%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 100 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1607 | 1574 | 97.9% | 1461 | **92.8%** | **90.9%** |
| **DRIVE/DEFENCE** | 1350 | 1277 | 94.6% | 1071 | **83.9%** | **79.3%** |
| **GLANCE/FLICK** | 1169 | 1144 | 97.9% | 1072 | **93.7%** | **91.7%** |
| **CUT/PUNCH** | 1113 | 1092 | 98.1% | 1076 | **98.5%** | **96.7%** |
| **DEFLECTION/GUIDE** | 325 | 281 | 86.5% | 269 | **95.7%** | **82.8%** |
| **POWER DRIVE** | 359 | 350 | 97.5% | 311 | **88.9%** | **86.6%** |
| **SWEEP** | 311 | 306 | 98.4% | 292 | **95.4%** | **93.9%** |
| **OVERALL TOTAL** | **6234** | **6024** | **96.6%** | **5552** | 🏆 **92.2%** | 🏆 **89.1%** |

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-31_10-06-52` | Training | 1.1 | 5 | 4 | 80.0% | 100.0% | 88.9%
| `session_2026-06-01_12-23-38` | Training | 17.9 | 68 | 66 | 97.1% | 100.0% | 98.5%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 29 | 31 | 100.0% | 93.5% | 96.7%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 57 | 56 | 94.7% | 96.4% | 95.6%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 52 | 60 | 96.2% | 83.3% | 89.3%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 63 | 62 | 98.4% | 100.0% | 99.2%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 55 | 57 | 98.2% | 94.7% | 96.4%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 65 | 64 | 96.9% | 98.4% | 97.7%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 72 | 71 | 94.4% | 95.8% | 95.1%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 63 | 65 | 100.0% | 96.9% | 98.4%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 69 | 65 | 92.8% | 98.5% | 95.5%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 66 | 62 | 92.4% | 98.4% | 95.3%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 64 | 64 | 96.9% | 96.9% | 96.9%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 65 | 64 | 95.4% | 96.9% | 96.1%
| `session_2026-06-29_12-21-45` | Training | 18.2 | 65 | 65 | 100.0% | 100.0% | 100.0%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 55 | 57 | 98.2% | 94.7% | 96.4%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 61 | 60 | 98.4% | 100.0% | 99.2%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 60 | 60 | 100.0% | 100.0% | 100.0%
| `session_2026-07-07_15-10-50` | Training | 22.0 | 44 | 57 | 88.6% | 68.4% | 77.2%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 64 | 64 | 98.4% | 98.4% | 98.4%
| `session_2026-07-10_12-30-15` | Training | 18.8 | 64 | 62 | 93.8% | 96.8% | 95.2%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 70 | 68 | 95.7% | 98.5% | 97.1%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 41 | 52 | 100.0% | 78.8% | 88.2%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 63 | 65 | 96.8% | 93.8% | 95.3%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 66 | 68 | 100.0% | 97.1% | 98.5%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 63 | 63 | 98.4% | 98.4% | 98.4%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 66 | 67 | 98.5% | 97.0% | 97.7%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 30 | 32 | 96.7% | 90.6% | 93.5%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 51 | 52 | 98.0% | 96.2% | 97.1%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 67 | 67 | 98.5% | 98.5% | 98.5%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 64 | 64 | 100.0% | 100.0% | 100.0%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 67 | 67 | 95.5% | 95.5% | 95.5%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 64 | 68 | 96.9% | 91.2% | 93.9%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 77 | 75 | 97.4% | 100.0% | 98.7%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 69 | 100.0% | 95.7% | 97.8%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 71 | 66 | 91.5% | 98.5% | 94.9%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 69 | 71 | 100.0% | 97.2% | 98.6%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 66 | 69 | 98.5% | 94.2% | 96.3%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 61 | 70 | 98.4% | 85.7% | 91.6%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 62 | 69 | 100.0% | 89.9% | 94.7%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 71 | 72 | 100.0% | 98.6% | 99.3%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 70 | 70 | 100.0% | 100.0% | 100.0%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 57 | 58 | 94.7% | 93.1% | 93.9%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 73 | 71 | 94.5% | 97.2% | 95.8%
| `session_2026-09-06_11-41-57` | Training | 1.8 | 6 | 6 | 100.0% | 100.0% | 100.0%
| `session_2026-09-06_12-35-47` | Training | 5.3 | 26 | 25 | 96.2% | 100.0% | 98.0%
| `session_2026-09-07_12-29-10` | Training | 20.3 | 62 | 64 | 96.8% | 93.8% | 95.2%
| `session_2026-09-14_12-56-40` | Training | 21.2 | 53 | 58 | 98.1% | 89.7% | 93.7%
| `session_2026-09-18_12-48-53` | Training | 20.5 | 68 | 69 | 98.5% | 97.1% | 97.8%
| `session_2026-09-30_12-52-29` | Training | 20.2 | 63 | 67 | 98.4% | 92.5% | 95.4%
| `session_2026-10-05_12-53-51` | Training | 20.6 | 66 | 64 | 90.9% | 93.8% | 92.3%
| `session_2026-10-06_12-49-35` | Training | 24.2 | 73 | 73 | 100.0% | 100.0% | 100.0%
| `session_2026-10-08_12-55-02` | Training | 20.6 | 71 | 74 | 87.3% | 83.8% | 85.5%
| `session_2026-10-16_12-59-39` | Training | 19.6 | 72 | 74 | 100.0% | 97.3% | 98.6%
| `session_2026-10-18_14-46-16` | Training | 19.2 | 64 | 70 | 98.4% | 90.0% | 94.0%
| `session_2026-10-19_12-47-59` | Training | 19.4 | 69 | 73 | 97.1% | 91.8% | 94.4%
| `session_2026-10-20_12-39-32` | Training | 18.9 | 71 | 72 | 100.0% | 98.6% | 99.3%
| `session_2026-10-22_12-57-41` | Training | 19.7 | 73 | 73 | 97.3% | 97.3% | 97.3%
| `session_2026-10-23_13-02-03` | Training | 20.4 | 64 | 69 | 95.3% | 88.4% | 91.7%
| `session_2026-10-26_12-57-14` | Training | 27.0 | 64 | 63 | 95.3% | 96.8% | 96.1%
| `session_2026-10-27_12-44-30` | Training | 18.9 | 74 | 73 | 98.6% | 100.0% | 99.3%
| `session_2026-10-29_12-19-24` | Training | 19.6 | 73 | 75 | 98.6% | 96.0% | 97.3%
| `session_2026-10-30_12-49-13` | Training | 22.0 | 67 | 72 | 100.0% | 93.1% | 96.4%
| `session_2026-11-01_15-20-45` | Training | 20.6 | 77 | 78 | 98.7% | 97.4% | 98.1%
| `session_2026-11-02_10-53-03` | Training | 15.3 | 71 | 70 | 97.2% | 98.6% | 97.9%
| `session_2026-11-03_16-38-01` | Training | 20.7 | 74 | 80 | 98.6% | 91.2% | 94.8%
| `session_2026-11-05_12-59-39` | Training | 20.4 | 59 | 70 | 100.0% | 84.3% | 91.5%
| `session_2026-11-06_12-46-07` | Training | 19.2 | 75 | 72 | 90.7% | 94.4% | 92.5%
| `session_2026-11-09_12-48-50` | Training | 19.4 | 69 | 72 | 100.0% | 95.8% | 97.9%
| `session_2026-11-10_12-49-55` | Training | 21.2 | 74 | 74 | 100.0% | 100.0% | 100.0%
| `session_2026-11-12_13-00-31` | Training | 20.0 | 73 | 74 | 98.6% | 97.3% | 98.0%
| `session_2026-11-13_12-48-24` | Training | 20.3 | 67 | 73 | 98.5% | 90.4% | 94.3%
| `session_2026-11-17_12-39-55` | Training | 8.8 | 40 | 42 | 100.0% | 95.2% | 97.6%
| `session_2026-11-19_12-55-38` | Training | 21.9 | 75 | 72 | 96.0% | 100.0% | 98.0%
| `session_2026-11-20_12-49-37` | Training | 12.4 | 47 | 47 | 74.5% | 74.5% | 74.5%
| `session_2026-11-21_10-48-27` | Training | 21.9 | 71 | 70 | 97.2% | 98.6% | 97.9%
| `session_2026-11-23_12-47-01` | Training | 17.6 | 72 | 73 | 90.3% | 89.0% | 89.7%
| `session_2026-06-21_13-53-17` | 🔹 VALIDATION | 20.2 | 61 | 63 | 96.7% | 93.7% | 95.2%
| `session_2026-06-27_14-12-40` | 🔹 VALIDATION | 17.6 | 55 | 57 | 100.0% | 96.5% | 98.2%
| `session_2026-07-02_12-38-53` | 🔹 VALIDATION | 20.9 | 67 | 62 | 92.5% | 100.0% | 96.1%
| `session_2026-07-24_12-52-29` | 🔹 VALIDATION | 17.9 | 65 | 60 | 92.3% | 100.0% | 96.0%
| `session_2026-08-06_12-51-06` | 🔹 VALIDATION | 17.0 | 64 | 65 | 87.5% | 86.2% | 86.8%
| `session_2026-08-17_12-51-22` | 🔹 VALIDATION | 19.2 | 72 | 69 | 91.7% | 95.7% | 93.6%
| `session_2026-09-10_12-55-41` | 🔹 VALIDATION | 19.4 | 66 | 65 | 95.5% | 96.9% | 96.2%
| `session_2026-10-04_15-30-15` | 🔹 VALIDATION | 15.0 | 68 | 67 | 97.1% | 98.5% | 97.8%
| `session_2026-10-15_12-49-52` | 🔹 VALIDATION | 20.0 | 58 | 65 | 100.0% | 89.2% | 94.3%
| `session_2026-06-12_12-24-37` | 🌟 HOLDOUT TEST | 20.9 | 76 | 75 | 97.4% | 98.7% | 98.0%
| `session_2026-06-19_12-25-55` | 🌟 HOLDOUT TEST | 16.7 | 64 | 63 | 93.8% | 95.2% | 94.5%
| `session_2026-06-25_12-25-07` | 🌟 HOLDOUT TEST | 21.2 | 66 | 66 | 97.0% | 97.0% | 97.0%
| `session_2026-06-28_11-28-09` | 🌟 HOLDOUT TEST | 19.8 | 56 | 55 | 98.2% | 100.0% | 99.1%
| `session_2026-07-27_12-47-20` | 🌟 HOLDOUT TEST | 18.1 | 62 | 61 | 98.4% | 100.0% | 99.2%
| `session_2026-08-08_10-43-42` | 🌟 HOLDOUT TEST | 29.8 | 86 | 81 | 91.9% | 97.5% | 94.6%
| `session_2026-08-16_14-10-23` | 🌟 HOLDOUT TEST | 11.8 | 50 | 51 | 100.0% | 98.0% | 99.0%
| `session_2026-08-22_14-25-31` | 🌟 HOLDOUT TEST | 12.0 | 53 | 52 | 98.1% | 100.0% | 99.0%
| `session_2026-09-08_12-52-30` | 🌟 HOLDOUT TEST | 22.7 | 66 | 67 | 93.9% | 92.5% | 93.2%
| `session_2026-09-17_12-48-47` | 🌟 HOLDOUT TEST | 20.3 | 66 | 68 | 98.5% | 95.6% | 97.0%
| `session_2026-10-09_12-41-17` | 🌟 HOLDOUT TEST | 20.1 | 54 | 61 | 94.4% | 83.6% | 88.7%
| `session_2026-10-17_11-47-47` | 🌟 HOLDOUT TEST | 18.9 | 70 | 71 | 95.7% | 94.4% | 95.0%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **SUBCLASS_CONFUSION** | **43** | DRIVE/DEFENCE (35), POWER DRIVE (4), GLANCE/FLICK (2) |
| **NOT_DETECTED (MISSING_CANDIDATE)** | **25** | DRIVE/DEFENCE (10), DEFLECTION/GUIDE (10), PULL/HOOK/SLOG (2) |
| **CROSS_BAT_CONFUSION** | **18** | DRIVE/DEFENCE (8), GLANCE/FLICK (7), DEFLECTION/GUIDE (3) |
| **VERTICAL_BAT_CONFUSION** | **16** | PULL/HOOK/SLOG (12), CUT/PUNCH (4) |
| **SWEEP_CONFUSION** | **16** | DRIVE/DEFENCE (6), SWEEP (4), GLANCE/FLICK (4) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-06-12_12-24-37` | 195.39 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.89 | 195.39 | +0.00 | *flick shot okay* |
| `session_2026-06-12_12-24-37` | 219.32 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.30 | 219.32 | +0.00 | *back foot punch okay* |
| `session_2026-06-12_12-24-37` | 580.66 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 578.29 | -2.37 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 654.65 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.77 | 654.65 | +0.00 | *good shot okay* |
| `session_2026-06-12_12-24-37` | 663.70 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.49 | 663.70 | +0.00 | *quick shot okay* |
| `session_2026-06-12_12-24-37` | 758.62 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.88 | 758.63 | +0.01 | *which shot okay* |
| `session_2026-06-12_12-24-37` | 776.47 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.66 | 776.48 | +0.00 | *flick shot good* |
| `session_2026-06-12_12-24-37` | 1007.25 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.58 | 1007.25 | +0.00 | *back defense good* |
| `session_2026-06-12_12-24-37` | 1032.93 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.55 | 1032.94 | +0.00 | *back foot defense okay* |
| `session_2026-06-12_12-24-37` | 1074.55 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1069.25 | -5.30 | *defense okay* |
| `session_2026-06-19_12-25-55` | 108.21 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 102.79 | -5.41 | *glide good* |
| `session_2026-06-19_12-25-55` | 119.53 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.47 | 119.55 | +0.02 | *glide edge* |
| `session_2026-06-19_12-25-55` | 154.36 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 149.28 | -5.08 | *glide okay* |
| `session_2026-06-19_12-25-55` | 173.03 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.92 | 173.05 | +0.02 | *cut shot four* |
| `session_2026-06-19_12-25-55` | 549.54 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 544.10 | -5.44 | *glide good* |
| `session_2026-06-19_12-25-55` | 600.09 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.68 | 600.22 | +0.13 | *back foot drive okay* |
| `session_2026-06-19_12-25-55` | 809.96 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.97 | 809.99 | +0.03 | *back foot drive good* |
| `session_2026-06-19_12-25-55` | 837.09 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 831.89 | -5.20 | *back foot drive okay* |
| `session_2026-06-19_12-25-55` | 913.45 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.75 | 913.48 | +0.02 | *back foot punch four* |
| `session_2026-06-25_12-25-07` | 142.96 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.88 | 142.99 | +0.02 | *forward defense okay* |
| `session_2026-06-25_12-25-07` | 204.64 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.93 | 204.66 | +0.02 | *and on drive forward* |
| `session_2026-06-25_12-25-07` | 224.87 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 222.56 | -2.31 | *forward defense good* |
| `session_2026-06-25_12-25-07` | 274.92 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 270.13 | -4.79 | *push shot okay* |
| `session_2026-06-25_12-25-07` | 544.97 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.59 | 544.99 | +0.02 | *forward fence okay* |
| `session_2026-06-25_12-25-07` | 602.41 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.88 | 602.43 | +0.02 | *on drive good* |
| `session_2026-06-25_12-25-07` | 628.43 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.42 | 628.45 | +0.02 | *on drive pour* |
| `session_2026-06-25_12-25-07` | 1138.27 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.63 | 1138.30 | +0.02 | *pull shot miss* |
| `session_2026-06-28_11-28-09` | 206.44 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.89 | 206.44 | +0.00 | *weep shot okay* |
| `session_2026-06-28_11-28-09` | 216.83 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.87 | 216.83 | +0.00 | *pull shot ah sweep shot okay* |
| `session_2026-06-28_11-28-09` | 237.17 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.74 | 237.17 | +0.00 | *on drive good* |
| `session_2026-06-28_11-28-09` | 304.02 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.84 | 304.02 | +0.00 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 552.69 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.65 | 552.69 | +0.00 | *straight drive or* |
| `session_2026-06-28_11-28-09` | 605.25 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.88 | 605.25 | +0.00 | *flick shot good* |
| `session_2026-06-28_11-28-09` | 985.49 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.73 | 985.49 | +0.00 | *edge drive* |
| `session_2026-06-28_11-28-09` | 995.22 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1004.92 | +9.70 | *fence four* |
| `session_2026-06-28_11-28-09` | 1128.66 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.77 | 1128.66 | +0.00 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 1176.74 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.31 | 1176.75 | +0.01 | *losing up sweep shot four* |
| `session_2026-07-27_12-47-20` | 49.45 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 58.10 | +8.65 | *back defense or* |
| `session_2026-07-27_12-47-20` | 96.36 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.54 | 96.36 | +0.00 | *back defense or* |
| `session_2026-07-27_12-47-20` | 111.97 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.50 | 111.97 | +0.00 | *on drive pour* |
| `session_2026-07-27_12-47-20` | 157.92 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.42 | 157.92 | +0.00 | *back foot defense okay* |
| `session_2026-07-27_12-47-20` | 517.89 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.74 | 517.89 | +0.00 | *pull shot or* |
| `session_2026-07-27_12-47-20` | 623.75 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.57 | 623.75 | +0.00 | *pull shot okay* |
| `session_2026-07-27_12-47-20` | 1041.11 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.70 | 1041.11 | +0.00 | *which shot good* |
| `session_2026-08-08_10-43-42` | 93.73 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.43 | 93.41 | -0.32 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 547.09 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.95 | 547.09 | +0.00 | *power drive flog good* |
| `session_2026-08-08_10-43-42` | 621.52 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.95 | 621.53 | +0.00 | *flick shot good* |
| `session_2026-08-08_10-43-42` | 650.49 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 646.99 | -3.49 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 1023.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.74 | 1023.83 | +0.00 | *pull shot pour* |
| `session_2026-08-08_10-43-42` | 1065.54 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.51 | 1065.54 | +0.00 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 1065.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.51 | 1065.54 | +0.00 | *forward defense good* |
| `session_2026-08-08_10-43-42` | 1077.46 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.71 | 1077.39 | -0.08 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 1111.81 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.82 | 1111.81 | +0.00 | *power drive okay* |
| `session_2026-08-08_10-43-42` | 1153.40 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.53 | 1153.41 | +0.00 | *pull shot okay* |
| `session_2026-08-08_10-43-42` | 1570.64 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1580.04 | +9.40 | *guide good* |
| `session_2026-08-08_10-43-42` | 1686.63 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1702.75 | +16.12 | *guide good* |
| `session_2026-08-08_10-43-42` | 1694.94 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1702.75 | +7.81 | *guide okay* |
| `session_2026-08-08_10-43-42` | 1706.14 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1702.75 | -3.39 | *guide okay* |
| `session_2026-08-08_10-43-42` | 1743.71 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1739.39 | -4.31 | *guide miss* |
| `session_2026-08-16_14-10-23` | 41.96 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.60 | 41.96 | +0.00 | *straight shot okay* |
| `session_2026-08-16_14-10-23` | 74.47 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.73 | 74.48 | +0.00 | *switch shot okay* |
| `session_2026-08-16_14-10-23` | 88.10 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.93 | 88.11 | +0.00 | *swipe shot okay* |
| `session_2026-08-16_14-10-23` | 198.42 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.88 | 198.42 | +0.00 | *on drive okay* |
| `session_2026-08-16_14-10-23` | 207.71 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.70 | 207.71 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 315.28 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.74 | 315.28 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 324.98 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.75 | 324.98 | +0.00 | *flick shot good* |
| `session_2026-08-16_14-10-23` | 349.05 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.76 | 349.05 | +0.00 | *quick shot okay* |
| `session_2026-08-16_14-10-23` | 408.37 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.93 | 408.37 | +0.00 | *slip shot edge* |
| `session_2026-08-16_14-10-23` | 546.84 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.50 | 546.84 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 560.04 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.28 | 560.04 | +0.00 | *pull shot okay* |
| `session_2026-08-16_14-10-23` | 568.23 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.69 | 568.24 | +0.00 | *sweep shot pull* |
| `session_2026-08-16_14-10-23` | 642.59 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.71 | 642.60 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 652.74 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.82 | 652.74 | +0.00 | *straight shot okay* |
| `session_2026-08-22_14-25-31` | 101.21 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.75 | 101.23 | +0.01 | *back foot defense good* |
| `session_2026-08-22_14-25-31` | 136.69 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.25 | 136.70 | +0.01 | *back foot defense okay* |
| `session_2026-08-22_14-25-31` | 184.90 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.55 | 184.91 | +0.01 | *cover drive okay* |
| `session_2026-08-22_14-25-31` | 310.62 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 301.84 | -8.77 | *forward defense four* |
| `session_2026-08-22_14-25-31` | 414.55 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.44 | 414.57 | +0.01 | *alright foot defense okay* |
| `session_2026-08-22_14-25-31` | 584.55 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.67 | 584.56 | +0.01 | *guide okay* |
| `session_2026-09-08_12-52-30` | 86.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 93.58 | +7.23 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 119.46 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.78 | 119.46 | +0.00 | *click shot or* |
| `session_2026-09-08_12-52-30` | 124.67 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.79 | 124.67 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 142.71 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.82 | 142.71 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 586.46 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.41 | 586.46 | +0.00 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 594.58 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.40 | 594.58 | +0.00 | *back foot defense four* |
| `session_2026-09-08_12-52-30` | 805.18 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.84 | 805.18 | +0.00 | *push up good* |
| `session_2026-09-08_12-52-30` | 815.13 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.74 | 815.13 | +0.00 | *push up* |
| `session_2026-09-08_12-52-30` | 830.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.34 | 830.54 | +0.00 | *on drive okay* |
| `session_2026-09-08_12-52-30` | 1149.94 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.66 | 1149.94 | +0.00 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 1259.47 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.94 | 1259.48 | +0.00 | *glide edge* |
| `session_2026-09-08_12-52-30` | 1289.69 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1280.66 | -9.03 | *wide miss* |
| `session_2026-09-17_12-48-47` | 177.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.89 | 177.87 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 185.69 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.69 | 185.70 | +0.00 | *straight drive poor* |
| `session_2026-09-17_12-48-47` | 254.51 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.82 | 254.51 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 299.71 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.70 | 299.71 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 306.98 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.64 | 306.99 | +0.00 | *on drive okay* |
| `session_2026-09-17_12-48-47` | 560.86 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.83 | 560.86 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 570.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.84 | 570.88 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 646.60 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.87 | 646.61 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 699.56 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.73 | 699.57 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 1025.77 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.90 | 1025.77 | +0.00 | *straight drive okay* |
| `session_2026-09-17_12-48-47` | 1129.36 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.83 | 1129.36 | +0.00 | *push shot miss* |
| `session_2026-09-17_12-48-47` | 1146.77 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.87 | 1146.77 | +0.00 | *on drive 4* |
| `session_2026-09-17_12-48-47` | 1210.75 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.82 | 1210.75 | +0.00 | *on drive good* |
| `session_2026-10-09_12-41-17` | 175.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.91 | 175.55 | +0.00 | *back foot defense or* |
| `session_2026-10-09_12-41-17` | 256.66 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.56 | 256.66 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 269.28 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.46 | 269.29 | +0.00 | *foot shot okay* |
| `session_2026-10-09_12-41-17` | 583.44 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.70 | 583.44 | +0.00 | *cover drive good* |
| `session_2026-10-09_12-41-17` | 590.78 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.35 | 590.78 | +0.00 | *back foot punch okay* |
| `session_2026-10-09_12-41-17` | 609.90 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 600.83 | -9.07 | *back foot defense poor* |
| `session_2026-10-09_12-41-17` | 665.70 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 658.76 | -6.94 | *back foot defense four* |
| `session_2026-10-09_12-41-17` | 1002.62 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.48 | 1002.62 | +0.00 | *back foot defense good* |
| `session_2026-10-09_12-41-17` | 1097.32 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.50 | 1097.32 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 1152.49 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1144.86 | -7.64 | *guide miss* |
| `session_2026-10-17_11-47-47` | 140.46 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 135.17 | -5.29 | *oh blanks miss* |
| `session_2026-10-17_11-47-47` | 218.43 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 213.49 | -4.94 | *on drive okay* |
| `session_2026-10-17_11-47-47` | 233.82 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.54 | 233.82 | +0.00 | *back foot defense or* |
| `session_2026-10-17_11-47-47` | 610.81 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 605.40 | -5.41 | *glance miss* |


---

## 🔍 Stage 3 Rule Health & Jev Shadow Audit
- **Config Version**: `v1.1.0` ([`stage3_rules_config.json`](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/stage3_rules_config.json))
- **Jev Shadow Auditor (`jev-1.13-free`, `v1.1.0-mount-aware-1q`)**: `1` cache hits, `350` live calls (median latency `366 ms`, estimated cost `$0.0000 USD`)

### 1. Stage 3 Rule Health & Shadow Telemetry Table
| Rule ID | State | Clean Benchmark Fires (89s) | Helped / Hurt | **Clean Net Impact** | Holdout Fires (12s) | **Holdout Net Impact** | Rule Precision (%) | Jev Agreement (%) | Health Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `bat_vertical_guard_rule1` | **ENABLED** | 0 | `+0 / -0` | **+0 shots** | 0 | **+0 shots** | 100.0% | 100.0% | ℹ️ DORMANT (SAFE GUARD) |
| `bat_ahrs_glance_rule2` | **ENABLED** | 0 | `+0 / -0` | **+0 shots** | 0 | **+0 shots** | 100.0% | 100.0% | ℹ️ DORMANT (SAFE GUARD) |
| `non_bat_sweep_to_glance` | SHADOW | 12 | `+2 / -9` | **-7 shots** | 1 | **-1 shots** | 16.7% | 0.0% | ⏸️ DISABLED (Net -7) |
| `s1_ahrs_flat_bat` | SHADOW | 125 | `+6 / -106` | **-100 shots** | 19 | **-18 shots** | 9.6% | 0.0% | ⏸️ DISABLED (Net -100) |
| `s2_power_drive_vs_pull` | SHADOW | 19 | `+13 / -6` | **+7 shots** | 0 | **+0 shots** | 68.4% | 0.0% | ⏸️ DISABLED (Net +7) |
| `s3_cut_punch_recovery` | SHADOW | 0 | `+0 / -0` | **+0 shots** | 0 | **+0 shots** | 100.0% | 100.0% | ⏸️ DISABLED (Net +0) |

### 2. Missed-Regime Clusters (Validation + Holdout Shots Where TCN Missed & Jev Agreed with GT)
| TCN Prediction | True GT + Jev Class | Sensor Mount | Shot Count | Sample Shots |
|---|---|---|:---:|---|
| **GLANCE/FLICK** | **DRIVE/DEFENCE** | `NONE` | 15 | `session_2026-06-27_14-12-40`@108.7s (conf 0.94), `session_2026-06-27_14-12-40`@241.4s (conf 0.98), `session_2026-06-27_14-12-40`@480.8s (conf 0.98) |
| **GLANCE/FLICK** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 14 | `session_2026-09-08_12-52-30`@830.5s (conf 0.74), `session_2026-09-17_12-48-47`@177.9s (conf 0.96), `session_2026-09-17_12-48-47`@185.7s (conf 0.98) |
| **CUT/PUNCH** | **DRIVE/DEFENCE** | `WRIST` | 7 | `session_2026-07-24_12-52-29`@188.3s (conf 0.92), `session_2026-07-24_12-52-29`@577.1s (conf 0.74), `session_2026-07-24_12-52-29`@595.6s (conf 0.62) |
| **SWEEP** | **DRIVE/DEFENCE** | `WRIST` | 6 | `session_2026-08-16_14-10-23`@42.0s (conf 0.93), `session_2026-08-16_14-10-23`@207.7s (conf 0.96), `session_2026-08-16_14-10-23`@315.3s (conf 0.98) |
| **CUT/PUNCH** | **DRIVE/DEFENCE** | `NONE` | 3 | `session_2026-06-12_12-24-37`@1007.2s (conf 0.89), `session_2026-06-19_12-25-55`@600.2s (conf 0.85), `session_2026-06-19_12-25-55`@810.0s (conf 0.95) |
| **GLANCE/FLICK** | **DRIVE/DEFENCE** | `WRIST` | 3 | `session_2026-07-27_12-47-20`@112.0s (conf 0.94), `session_2026-07-27_12-47-20`@157.9s (conf 0.92), `session_2026-08-16_14-10-23`@198.4s (conf 1.0) |
| **PULL/HOOK/SLOG** | **DRIVE/DEFENCE** | `WRIST` | 2 | `session_2026-07-24_12-52-29`@172.7s (conf 0.66), `session_2026-08-06_12-51-06`@95.0s (conf 0.94) |
| **CUT/PUNCH** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 2 | `session_2026-09-08_12-52-30`@586.5s (conf 0.87) |
| **DEFLECTION/GUIDE** | **DRIVE/DEFENCE** | `BAT_HANDLE` | 2 | `session_2026-09-08_12-52-30`@594.6s (conf 0.64) |
| **POWER DRIVE** | **DRIVE/DEFENCE** | `NONE` | 1 | `session_2026-06-27_14-12-40`@852.4s (conf 0.73) |
| **DEFLECTION/GUIDE** | **DRIVE/DEFENCE** | `NONE` | 1 | `session_2026-06-12_12-24-37`@1032.9s (conf 0.79) |
| **DEFLECTION/GUIDE** | **DRIVE/DEFENCE** | `WRIST` | 1 | `session_2026-07-27_12-47-20`@96.4s (conf 0.64) |

### 3. Validation Threshold Drift & Calibration Check
- ✅ **All Stage 3 rule thresholds are optimal** on the 9-session Validation Set (no perturbation gains ≥ 2 shots).
