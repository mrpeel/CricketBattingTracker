# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining, Joint 9-Class Hierarchical NLL + Cross-Family Power Drive Suppression + On-the-Fly Kinematic Augmentation (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.5, 1.0, 1.3], Rejection Threshold $\theta_{no\_shot} = 0.35$)  
**Holdout Test Sessions**: `session_2026-06-12_12-24-37, session_2026-06-19_12-25-55, session_2026-06-25_12-25-07, session_2026-06-28_11-28-09, session_2026-07-27_12-47-20, session_2026-08-08_10-43-42, session_2026-08-16_14-10-23, session_2026-08-22_14-25-31, session_2026-09-08_12-52-30, session_2026-09-17_12-48-47, session_2026-10-09_12-41-17, session_2026-10-17_11-47-47` (12 sessions)  
**Validation Sessions**: `session_2026-06-21_13-53-17, session_2026-06-27_14-12-40, session_2026-07-02_12-38-53, session_2026-07-24_12-52-29, session_2026-08-06_12-51-06, session_2026-08-17_12-51-22, session_2026-09-10_12-55-41, session_2026-10-04_15-30-15, session_2026-10-15_12-49-52` (9 sessions)  
**Quarantined Faulted Sessions**: `session_2026-05-30_15-04-41, session_2026-05-31_14-12-10, session_2026-07-11_12-51-39, session_2026-07-17_12-30-41, session_2026-07-18_13-44-09, session_2026-09-05_16-26-41, session_2026-09-06_12-14-46, session_2026-09-11_12-44-50` (8 sessions)  
**Training Sessions Count**: 66 physical sessions  
**Clean Benchmark Sessions Count**: 87 physical sessions  
**Total Dataset Duration**: 1563.0 minutes (26.0 hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch 18 (Best Val Macro-F1: 0.8166, Shot Acc: 86.80%, Val Loss: 1.5135, Stopped at Epoch 24)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-10-29_17-04-03.log`  
**Date**: 2026-10-29 17:59

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set (12 Sessions)** | **714** | **722** | **92.72%** (662/714) | **91.69%** (662/722) | **92.20%** |
| **Training Set Micro Average (66 Sessions)** | **4288** | **4207** | **90.14%** (3865/4288) | **91.87%** (3865/4207) | **90.99%** |
| 🏆 **Clean Benchmark Micro Average (87 Sessions)** | **5002** | **4929** | 🏆 **90.50%** (4527/5002) | 🏆 **91.84%** (4527/4929) | 🏆 **91.17%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (12 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 134 | 126 | 94.0% | 106 | **84.1%** | **79.1%** |
| **DRIVE/DEFENCE** | 196 | 181 | 92.3% | 147 | **81.2%** | **75.0%** |
| **GLANCE/FLICK** | 131 | 124 | 94.7% | 104 | **83.9%** | **79.4%** |
| **CUT/PUNCH** | 70 | 65 | 92.9% | 52 | **80.0%** | **74.3%** |
| **DEFLECTION/GUIDE** | 76 | 66 | 86.8% | 58 | **87.9%** | **76.3%** |
| **POWER DRIVE** | 48 | 45 | 93.8% | 44 | **97.8%** | **91.7%** |
| **SWEEP** | 59 | 55 | 93.2% | 49 | **89.1%** | **83.1%** |
| **OVERALL TOTAL** | **714** | **662** | **92.7%** | **560** | 🏆 **84.6%** | 🏆 **78.4%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (75 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1166 | 1056 | 90.6% | 979 | **92.7%** | **84.0%** |
| **DRIVE/DEFENCE** | 1025 | 936 | 91.3% | 883 | **94.3%** | **86.1%** |
| **GLANCE/FLICK** | 792 | 716 | 90.4% | 669 | **93.4%** | **84.5%** |
| **CUT/PUNCH** | 560 | 502 | 89.6% | 472 | **94.0%** | **84.3%** |
| **DEFLECTION/GUIDE** | 240 | 196 | 81.7% | 192 | **98.0%** | **80.0%** |
| **POWER DRIVE** | 294 | 267 | 90.8% | 265 | **99.3%** | **90.1%** |
| **SWEEP** | 211 | 192 | 91.0% | 174 | **90.6%** | **82.5%** |
| **OVERALL TOTAL** | **4288** | **3865** | **90.1%** | **3634** | 🏆 **94.0%** | 🏆 **84.7%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 87 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1300 | 1182 | 90.9% | 1085 | **91.8%** | **83.5%** |
| **DRIVE/DEFENCE** | 1221 | 1117 | 91.5% | 1030 | **92.2%** | **84.4%** |
| **GLANCE/FLICK** | 923 | 840 | 91.0% | 773 | **92.0%** | **83.7%** |
| **CUT/PUNCH** | 630 | 567 | 90.0% | 524 | **92.4%** | **83.2%** |
| **DEFLECTION/GUIDE** | 316 | 262 | 82.9% | 250 | **95.4%** | **79.1%** |
| **POWER DRIVE** | 342 | 312 | 91.2% | 309 | **99.0%** | **90.4%** |
| **SWEEP** | 270 | 247 | 91.5% | 223 | **90.3%** | **82.6%** |
| **OVERALL TOTAL** | **5002** | **4527** | **90.5%** | **4194** | 🏆 **92.6%** | 🏆 **83.8%** |

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 5 | 100.0% | 80.0% | 88.9%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 58 | 93.4% | 98.3% | 95.8%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 96.4% | 96.4% | 96.4%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 40 | 70.6% | 90.0% | 79.1%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 40 | 68.9% | 77.5% | 72.9%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 58 | 94.8% | 94.8% | 94.8%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 51 | 94.1% | 94.1% | 94.1%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 89.9% | 96.9% | 93.2%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 61 | 100.0% | 93.4% | 96.6%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 55 | 96.5% | 100.0% | 98.2%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 56 | 93.0% | 94.6% | 93.8%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 59 | 96.6% | 96.6% | 96.6%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 60 | 100.0% | 96.7% | 98.3%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 53 | 98.0% | 90.6% | 94.1%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 57 | 96.5% | 96.5% | 96.5%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 54 | 91.4% | 98.1% | 94.6%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 56 | 96.2% | 89.3% | 92.6%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 60 | 100.0% | 96.7% | 98.3%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 54 | 100.0% | 94.4% | 97.1%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 19 | 30.4% | 89.5% | 45.3%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 61 | 66 | 90.2% | 83.3% | 86.6%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 37 | 42 | 91.9% | 81.0% | 86.1%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 58 | 59 | 70.7% | 69.5% | 70.1%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 96.5% | 91.7% | 94.0%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 61 | 64 | 98.4% | 93.8% | 96.0%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 57 | 98.2% | 94.7% | 96.4%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 44 | 46 | 88.6% | 84.8% | 86.7%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 57 | 90.9% | 87.7% | 89.3%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 26 | 88.9% | 92.3% | 90.6%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 49 | 93.9% | 93.9% | 93.9%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 61 | 83.6% | 83.6% | 83.6%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 58 | 91.9% | 98.3% | 95.0%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 62 | 93.4% | 91.9% | 92.7%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 70 | 87.7% | 91.4% | 89.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 68 | 97.0% | 94.1% | 95.5%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 67 | 92.8% | 95.5% | 94.1%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 64 | 92.5% | 96.9% | 94.7%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 65 | 92.3% | 92.3% | 92.3%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 64 | 94.8% | 85.9% | 90.2%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 55 | 85.7% | 87.3% | 86.5%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 64 | 58 | 89.1% | 98.3% | 93.4%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 63 | 93.9% | 98.4% | 96.1%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 49 | 85.2% | 93.9% | 89.3%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 65 | 61 | 89.2% | 95.1% | 92.1%
| `session_2026-09-06_11-41-57` | Training | 1.8 | 7 | 6 | 85.7% | 100.0% | 92.3%
| `session_2026-09-06_12-35-47` | Training | 5.3 | 27 | 25 | 92.6% | 100.0% | 96.2%
| `session_2026-09-07_12-29-10` | Training | 20.3 | 60 | 51 | 71.7% | 84.3% | 77.5%
| `session_2026-09-14_12-56-40` | Training | 21.2 | 53 | 56 | 96.2% | 91.1% | 93.6%
| `session_2026-09-18_12-48-53` | Training | 20.5 | 68 | 66 | 94.1% | 97.0% | 95.5%
| `session_2026-09-30_12-52-29` | Training | 20.2 | 63 | 61 | 92.1% | 95.1% | 93.5%
| `session_2026-10-05_12-53-51` | Training | 20.6 | 67 | 64 | 86.6% | 90.6% | 88.5%
| `session_2026-10-06_12-49-35` | Training | 24.2 | 73 | 69 | 89.0% | 94.2% | 91.5%
| `session_2026-10-08_12-55-02` | Training | 20.6 | 69 | 70 | 82.6% | 81.4% | 82.0%
| `session_2026-10-16_12-59-39` | Training | 19.6 | 69 | 68 | 88.4% | 89.7% | 89.1%
| `session_2026-10-18_14-46-16` | Training | 19.2 | 64 | 64 | 87.5% | 87.5% | 87.5%
| `session_2026-10-19_12-47-59` | Training | 19.4 | 67 | 71 | 94.0% | 88.7% | 91.3%
| `session_2026-10-20_12-39-32` | Training | 18.9 | 70 | 67 | 88.6% | 92.5% | 90.5%
| `session_2026-10-22_12-57-41` | Training | 19.7 | 73 | 68 | 87.7% | 94.1% | 90.8%
| `session_2026-10-23_13-02-03` | Training | 20.4 | 62 | 66 | 88.7% | 83.3% | 85.9%
| `session_2026-10-26_12-57-14` | Training | 27.0 | 64 | 60 | 81.2% | 86.7% | 83.9%
| `session_2026-10-27_12-44-30` | Training | 18.9 | 72 | 63 | 81.9% | 93.7% | 87.4%
| `session_2026-10-29_12-19-24` | Training | 19.6 | 72 | 73 | 90.3% | 89.0% | 89.7%
| `session_2026-06-21_13-53-17` | 🔹 VALIDATION | 20.2 | 55 | 61 | 100.0% | 90.2% | 94.8%
| `session_2026-06-27_14-12-40` | 🔹 VALIDATION | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-07-02_12-38-53` | 🔹 VALIDATION | 20.9 | 59 | 58 | 98.3% | 100.0% | 99.1%
| `session_2026-07-24_12-52-29` | 🔹 VALIDATION | 17.9 | 52 | 54 | 82.7% | 79.6% | 81.1%
| `session_2026-08-06_12-51-06` | 🔹 VALIDATION | 17.0 | 58 | 59 | 84.5% | 83.1% | 83.8%
| `session_2026-08-17_12-51-22` | 🔹 VALIDATION | 19.2 | 64 | 58 | 87.5% | 96.6% | 91.8%
| `session_2026-09-10_12-55-41` | 🔹 VALIDATION | 19.4 | 60 | 56 | 88.3% | 94.6% | 91.4%
| `session_2026-10-04_15-30-15` | 🔹 VALIDATION | 15.0 | 67 | 65 | 92.5% | 95.4% | 93.9%
| `session_2026-10-15_12-49-52` | 🔹 VALIDATION | 20.0 | 58 | 60 | 93.1% | 90.0% | 91.5%
| `session_2026-06-12_12-24-37` | 🌟 HOLDOUT TEST | 20.9 | 70 | 69 | 97.1% | 98.6% | 97.8%
| `session_2026-06-19_12-25-55` | 🌟 HOLDOUT TEST | 16.7 | 56 | 59 | 98.2% | 93.2% | 95.7%
| `session_2026-06-25_12-25-07` | 🌟 HOLDOUT TEST | 21.2 | 65 | 64 | 95.4% | 96.9% | 96.1%
| `session_2026-06-28_11-28-09` | 🌟 HOLDOUT TEST | 19.8 | 52 | 54 | 96.2% | 92.6% | 94.3%
| `session_2026-07-27_12-47-20` | 🌟 HOLDOUT TEST | 18.1 | 53 | 56 | 94.3% | 89.3% | 91.7%
| `session_2026-08-08_10-43-42` | 🌟 HOLDOUT TEST | 29.8 | 77 | 81 | 90.9% | 86.4% | 88.6%
| `session_2026-08-16_14-10-23` | 🌟 HOLDOUT TEST | 11.8 | 50 | 46 | 92.0% | 100.0% | 95.8%
| `session_2026-08-22_14-25-31` | 🌟 HOLDOUT TEST | 12.0 | 51 | 49 | 90.2% | 93.9% | 92.0%
| `session_2026-09-08_12-52-30` | 🌟 HOLDOUT TEST | 22.7 | 57 | 56 | 84.2% | 85.7% | 85.0%
| `session_2026-09-17_12-48-47` | 🌟 HOLDOUT TEST | 20.3 | 62 | 59 | 91.9% | 96.6% | 94.2%
| `session_2026-10-09_12-41-17` | 🌟 HOLDOUT TEST | 20.1 | 51 | 62 | 96.1% | 79.0% | 86.7%
| `session_2026-10-17_11-47-47` | 🌟 HOLDOUT TEST | 18.9 | 70 | 67 | 87.1% | 91.0% | 89.1%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **NOT_DETECTED (MISSING_CANDIDATE)** | **48** | DRIVE/DEFENCE (14), GLANCE/FLICK (9), DEFLECTION/GUIDE (9) |
| **SUBCLASS_CONFUSION** | **40** | DRIVE/DEFENCE (25), GLANCE/FLICK (8), DEFLECTION/GUIDE (6) |
| **VERTICAL_BAT_CONFUSION** | **31** | PULL/HOOK/SLOG (18), CUT/PUNCH (13) |
| **SWEEP_CONFUSION** | **22** | GLANCE/FLICK (9), SWEEP (6), DRIVE/DEFENCE (5) |
| **CROSS_BAT_CONFUSION** | **10** | DRIVE/DEFENCE (6), GLANCE/FLICK (2), DEFLECTION/GUIDE (2) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-06-12_12-24-37` | 138.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 132.22 | -6.13 | *pull shot four facing up* |
| `session_2026-06-12_12-24-37` | 197.07 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 195.39 | -1.68 | *flick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 578.02 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.46 | 578.29 | +0.27 | *pull shot good* |
| `session_2026-06-12_12-24-37` | 627.23 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.44 | 627.36 | +0.13 | *pull shot okay facing up* |
| `session_2026-06-12_12-24-37` | 632.67 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 627.36 | -5.31 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 643.43 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.53 | 643.65 | +0.22 | *pull shot good* |
| `session_2026-06-12_12-24-37` | 664.87 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.73 | 663.70 | -1.17 | *quick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 705.68 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.44 | 705.77 | +0.09 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 753.15 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.66 | 752.84 | -0.31 | *pull shot good* |
| `session_2026-06-12_12-24-37` | 1091.77 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.54 | 1092.03 | +0.26 | *pull shot okay facing up* |
| `session_2026-06-12_12-24-37` | 1134.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.89 | 1134.83 | -0.00 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 1210.09 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.54 | 1210.29 | +0.20 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 1234.72 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.84 | 1234.11 | -0.61 | *which shot okay facing up* |
| `session_2026-06-19_12-25-55` | 45.30 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.60 | 44.29 | -1.01 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 82.28 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.77 | 82.14 | -0.14 | *touch shot four* |
| `session_2026-06-19_12-25-55` | 173.51 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.60 | 173.05 | -0.46 | *cut shot four* |
| `session_2026-06-19_12-25-55` | 500.81 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.87 | 500.29 | -0.52 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 515.69 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.93 | 515.62 | -0.07 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 526.84 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.59 | 525.88 | -0.96 | *cut shot okay* |
| `session_2026-06-19_12-25-55` | 537.24 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.93 | 537.01 | -0.23 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 595.40 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.93 | 595.25 | -0.15 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 797.11 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.63 | 796.48 | -0.63 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 810.97 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 805.91 | -5.06 | *back foot drive good facing up* |
| `session_2026-06-19_12-25-55` | 845.75 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.58 | 845.61 | -0.14 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 860.39 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.69 | 859.04 | -1.35 | *cut shot four facing up* |
| `session_2026-06-25_12-25-07` | 12.82 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 63.80 | +50.98 | *alright let's get going* |
| `session_2026-06-25_12-25-07` | 53.84 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 63.80 | +9.96 | *alright facing up* |
| `session_2026-06-25_12-25-07` | 65.20 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.67 | 63.80 | -1.40 | *flick shot okay facing up* |
| `session_2026-06-25_12-25-07` | 101.08 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.89 | 100.93 | -0.15 | *flip shot okay* |
| `session_2026-06-25_12-25-07` | 142.89 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.84 | 142.99 | +0.10 | *forward defense okay* |
| `session_2026-06-25_12-25-07` | 190.29 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.44 | 189.94 | -0.35 | *good shot okay* |
| `session_2026-06-25_12-25-07` | 602.93 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.74 | 602.43 | -0.50 | *on drive good* |
| `session_2026-06-25_12-25-07` | 645.95 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.60 | 645.01 | -0.94 | *back defense good facing up flick shot okay* |
| `session_2026-06-25_12-25-07` | 1019.92 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1027.93 | +8.01 | *alright match day bat facing up* |
| `session_2026-06-25_12-25-07` | 1138.55 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.91 | 1138.30 | -0.25 | *pull shot miss* |
| `session_2026-06-28_11-28-09` | 206.55 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.74 | 206.44 | -0.11 | *weep shot okay* |
| `session_2026-06-28_11-28-09` | 216.85 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.90 | 216.83 | -0.02 | *pull shot ah sweep shot okay* |
| `session_2026-06-28_11-28-09` | 303.94 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.52 | 304.02 | +0.08 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 596.17 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.52 | 596.52 | +0.35 | *slip shot good* |
| `session_2026-06-28_11-28-09` | 605.08 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.89 | 605.25 | +0.17 | *flick shot good* |
| `session_2026-06-28_11-28-09` | 673.45 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 671.90 | -1.55 | *forward defense okay facing up* |
| `session_2026-06-28_11-28-09` | 756.41 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.78 | 756.62 | +0.21 | *slip shot miss in the round* |
| `session_2026-06-28_11-28-09` | 996.15 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1004.92 | +8.77 | *fence four* |
| `session_2026-06-28_11-28-09` | 1012.49 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.36 | 1012.87 | +0.38 | *sweep shot good* |
| `session_2026-06-28_11-28-09` | 1035.39 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.81 | 1035.35 | -0.04 | *slip shot okay* |
| `session_2026-06-28_11-28-09` | 1097.21 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.64 | 1096.96 | -0.25 | *slip shot okay* |
| `session_2026-06-28_11-28-09` | 1105.97 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.61 | 1106.10 | +0.13 | *sweep shot okay* |
| `session_2026-06-28_11-28-09` | 1128.90 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.57 | 1128.66 | -0.24 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 1139.97 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.73 | 1140.13 | +0.16 | *slip shot miss* |
| `session_2026-06-28_11-28-09` | 1175.13 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1170.49 | -4.64 | *losing up sweep shot four* |
| `session_2026-07-27_12-47-20` | 58.09 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 49.45 | -8.64 | *back fence good* |
| `session_2026-07-27_12-47-20` | 111.97 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.53 | 111.97 | +0.00 | *on drive pour* |
| `session_2026-07-27_12-47-20` | 143.34 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.56 | 143.35 | +0.00 | *pull shot okay* |
| `session_2026-07-27_12-47-20` | 593.84 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 588.87 | -4.97 | *quick shot miss* |
| `session_2026-07-27_12-47-20` | 995.06 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 999.57 | +4.51 | *back foot defense good facing up* |
| `session_2026-07-27_12-47-20` | 1041.11 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.53 | 1041.11 | +0.00 | *which shot good* |
| `session_2026-08-08_10-43-42` | 4.03 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.03 | +71.00 | *alright* |
| `session_2026-08-08_10-43-42` | 547.09 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.94 | 547.09 | +0.00 | *power drive flog good* |
| `session_2026-08-08_10-43-42` | 550.07 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 547.09 | -2.98 | *facing up power drive good* |
| `session_2026-08-08_10-43-42` | 621.53 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.84 | 621.53 | +0.00 | *flick shot good* |
| `session_2026-08-08_10-43-42` | 646.99 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.46 | 646.99 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 650.49 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 646.99 | -3.49 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 698.30 | **DRIVE/DEFENCE** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.97 | 698.30 | +0.00 | *facing up on drive good* |
| `session_2026-08-08_10-43-42` | 1023.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.58 | 1023.83 | +0.00 | *pull shot pour* |
| `session_2026-08-08_10-43-42` | 1148.89 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.99 | 1148.90 | +0.00 | *power drive good facing up pull shot okay* |
| `session_2026-08-08_10-43-42` | 1730.94 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.40 | 1730.94 | +0.00 | *guide okay* |
| `session_2026-08-08_10-43-42` | 1756.25 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1753.03 | -3.22 | *guide okay* |
| `session_2026-08-16_14-10-23` | 41.96 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 52.18 | +10.22 | *straight shot okay* |
| `session_2026-08-16_14-10-23` | 88.11 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.74 | 88.11 | +0.00 | *swipe shot okay* |
| `session_2026-08-16_14-10-23` | 108.31 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 97.29 | -11.02 | *sweep shot okay* |
| `session_2026-08-16_14-10-23` | 117.57 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.85 | +9.28 | *sweep shot good* |
| `session_2026-08-16_14-10-23` | 154.34 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.78 | 154.34 | +0.00 | *slip shot okay* |
| `session_2026-08-16_14-10-23` | 174.52 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.17 | 174.52 | +0.00 | *we've shot good* |
| `session_2026-08-16_14-10-23` | 198.42 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.79 | 198.42 | +0.00 | *on drive okay* |
| `session_2026-08-16_14-10-23` | 207.71 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.62 | 207.71 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 294.37 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.30 | 295.63 | +1.25 | *facing up sweep shot okay* |
| `session_2026-08-16_14-10-23` | 315.28 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.70 | 315.28 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 324.98 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.74 | 324.98 | +0.00 | *flick shot good* |
| `session_2026-08-16_14-10-23` | 349.05 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.74 | 349.05 | +0.00 | *quick shot okay* |
| `session_2026-08-16_14-10-23` | 546.84 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.74 | 546.84 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 560.04 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 568.24 | +8.19 | *pull shot okay* |
| `session_2026-08-16_14-10-23` | 568.24 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.91 | 568.24 | +0.00 | *sweep shot pull* |
| `session_2026-08-16_14-10-23` | 642.60 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.79 | 642.60 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 652.74 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.93 | 652.74 | +0.00 | *straight shot okay* |
| `session_2026-08-22_14-25-31` | 59.97 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.61 | 59.97 | +0.00 | *back foot punch good facing up* |
| `session_2026-08-22_14-25-31` | 115.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 113.39 | -2.54 | *glide four* |
| `session_2026-08-22_14-25-31` | 186.91 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 184.91 | -1.99 | *facing back foot punch okay* |
| `session_2026-08-22_14-25-31` | 328.01 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 324.85 | -3.17 | *facing up cut shot four* |
| `session_2026-08-22_14-25-31` | 363.73 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.97 | 363.73 | +0.00 | *back foot punch okay facing up cut shot okay* |
| `session_2026-08-22_14-25-31` | 414.57 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.98 | 414.57 | +0.00 | *alright foot defense okay end of round* |
| `session_2026-08-22_14-25-31` | 584.56 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.82 | 584.56 | +0.00 | *guide okay facing up* |
| `session_2026-08-22_14-25-31` | 649.80 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.93 | 649.80 | +0.00 | *back foot punch okay facing up* |
| `session_2026-08-22_14-25-31` | 685.21 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.56 | 685.22 | +0.00 | *that's a punch four* |
| `session_2026-09-08_12-52-30` | 86.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 93.58 | +7.23 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 119.46 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.83 | 119.46 | +0.00 | *click shot or facing up* |
| `session_2026-09-08_12-52-30` | 124.67 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.74 | 124.67 | +0.00 | *glide okay facing up* |
| `session_2026-09-08_12-52-30` | 142.71 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.84 | 142.71 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 209.12 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 207.59 | -1.52 | *facing up cut shot okay* |
| `session_2026-09-08_12-52-30` | 269.40 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 260.92 | -8.48 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 594.85 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.36 | 594.58 | -0.26 | *back foot defense four* |
| `session_2026-09-08_12-52-30` | 594.58 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.36 | 594.58 | +0.00 | *facing up back foot defense okay* |
| `session_2026-09-08_12-52-30` | 738.76 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.89 | 738.76 | +0.00 | *back foot punch good facing up cut shot pour* |
| `session_2026-09-08_12-52-30` | 805.18 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.95 | 805.18 | +0.00 | *push up good facing up* |
| `session_2026-09-08_12-52-30` | 815.13 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 822.57 | +7.44 | *push up facing up* |
| `session_2026-09-08_12-52-30` | 1204.95 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1203.14 | -1.80 | *glide miss* |
| `session_2026-09-08_12-52-30` | 1217.89 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.76 | 1217.89 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 1227.88 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1230.17 | +2.30 | *squad good facing up back foot punch good* |
| `session_2026-09-08_12-52-30` | 1259.47 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.93 | 1259.48 | +0.00 | *back foot punch good facing up glide edge facing* |
| `session_2026-09-08_12-52-30` | 1289.69 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1280.66 | -9.03 | *wide miss* |
| `session_2026-09-08_12-52-30` | 1345.95 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.83 | 1345.95 | +0.00 | *back foot punch good* |
| `session_2026-09-17_12-48-47` | 118.16 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.31 | +8.15 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 135.02 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +8.66 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 138.93 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +4.75 | *straight drive edge* |
| `session_2026-09-17_12-48-47` | 177.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.63 | 177.87 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 254.51 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.62 | 254.51 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 298.25 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.35 | 299.71 | +1.46 | *facing up on drive good* |
| `session_2026-09-17_12-48-47` | 560.86 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.48 | 560.86 | +0.00 | *on drive good facing up* |
| `session_2026-09-17_12-48-47` | 570.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.65 | 570.88 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 646.60 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.54 | 646.61 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 677.45 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 680.90 | +3.45 | *facing up switch shot okay* |
| `session_2026-09-17_12-48-47` | 699.56 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.47 | 699.57 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 752.91 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 754.72 | +1.81 | *facing up good shot okay in the ground* |
| `session_2026-09-17_12-48-47` | 1005.67 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1017.22 | +11.55 | *facing up flick shot okay* |
| `session_2026-09-17_12-48-47` | 1129.36 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.72 | 1129.36 | +0.00 | *push shot miss* |
| `session_2026-09-17_12-48-47` | 1146.77 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.76 | 1146.77 | +0.00 | *on drive 4 facing up* |
| `session_2026-09-17_12-48-47` | 1210.75 | **DRIVE/DEFENCE** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.51 | 1210.75 | +0.00 | *on drive good end of round end of sessions* |
| `session_2026-10-09_12-41-17` | 175.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.70 | 175.55 | +0.00 | *back foot defense or* |
| `session_2026-10-09_12-41-17` | 233.34 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 226.52 | -6.83 | *flick shot okay* |
| `session_2026-10-09_12-41-17` | 256.66 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.84 | 256.66 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 269.28 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.58 | 269.29 | +0.00 | *foot shot okay facing up back foot defense okay in the ground* |
| `session_2026-10-09_12-41-17` | 609.90 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.76 | 609.91 | +0.00 | *back foot defense poor* |
| `session_2026-10-09_12-41-17` | 665.70 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.85 | 665.70 | +0.00 | *back foot defense four* |
| `session_2026-10-09_12-41-17` | 674.49 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.65 | 674.49 | +0.00 | *back foot punch edge* |
| `session_2026-10-09_12-41-17` | 688.03 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.56 | 688.04 | +0.00 | *glide okay facing it* |
| `session_2026-10-09_12-41-17` | 696.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.90 | 696.30 | +0.00 | *crackle punch okay facing it* |
| `session_2026-10-09_12-41-17` | 1002.62 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.70 | 1002.62 | +0.00 | *back foot defense good* |
| `session_2026-10-09_12-41-17` | 1097.32 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.73 | 1097.32 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 1102.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1097.32 | -4.99 | *facing clive okay* |
| `session_2026-10-09_12-41-17` | 1152.49 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.50 | 1152.49 | +0.00 | *guide miss* |
| `session_2026-10-17_11-47-47` | 122.63 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 120.27 | -2.36 | *facing up glance good* |
| `session_2026-10-17_11-47-47` | 140.46 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 135.17 | -5.29 | *facing up oh blanks miss* |
| `session_2026-10-17_11-47-47` | 167.64 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 166.07 | -1.57 | *lacing up flick shot good* |
| `session_2026-10-17_11-47-47` | 216.38 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 213.49 | -2.88 | *facing up on drive okay facing up* |
| `session_2026-10-17_11-47-47` | 233.82 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.56 | 233.82 | +0.00 | *back foot defense or facing up* |
| `session_2026-10-17_11-47-47` | 609.03 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 605.40 | -3.63 | *facing up glance miss* |
| `session_2026-10-17_11-47-47` | 631.08 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 634.35 | +3.27 | *facing up pull shot okay* |
| `session_2026-10-17_11-47-47` | 641.00 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.69 | 641.00 | +0.00 | *flick shot okay facing up* |
| `session_2026-10-17_11-47-47` | 648.89 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.60 | 648.90 | +0.00 | *pull shot four* |
| `session_2026-10-17_11-47-47` | 968.86 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 963.65 | -5.20 | *facing up pull shot miss* |
| `session_2026-10-17_11-47-47` | 1016.02 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1010.32 | -5.69 | *facing up pull shot good* |
| `session_2026-10-17_11-47-47` | 1048.96 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1055.30 | +6.34 | *facing up pull shot okay* |

