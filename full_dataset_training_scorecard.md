# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining, Joint 9-Class Hierarchical NLL + Cross-Family Power Drive Suppression + On-the-Fly Kinematic Augmentation (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.5, 1.0, 1.3], Rejection Threshold $\theta_{no\_shot} = 0.35$)  
**Holdout Test Sessions**: `session_2026-06-12_12-24-37, session_2026-06-19_12-25-55, session_2026-06-25_12-25-07, session_2026-06-28_11-28-09, session_2026-07-27_12-47-20, session_2026-08-08_10-43-42, session_2026-08-16_14-10-23, session_2026-08-22_14-25-31, session_2026-09-08_12-52-30, session_2026-09-17_12-48-47, session_2026-10-09_12-41-17, session_2026-10-17_11-47-47` (12 sessions)  
**Validation Sessions**: `session_2026-06-21_13-53-17, session_2026-06-27_14-12-40, session_2026-07-02_12-38-53, session_2026-07-24_12-52-29, session_2026-08-06_12-51-06, session_2026-08-17_12-51-22, session_2026-09-10_12-55-41, session_2026-10-04_15-30-15, session_2026-10-15_12-49-52` (9 sessions)  
**Quarantined Faulted Sessions**: `session_2026-05-30_15-04-41, session_2026-05-31_14-12-10, session_2026-07-11_12-51-39, session_2026-07-17_12-30-41, session_2026-07-18_13-44-09, session_2026-09-05_16-26-41, session_2026-09-06_12-14-46, session_2026-09-11_12-44-50` (8 sessions)  
**Training Sessions Count**: 68 physical sessions  
**Clean Benchmark Sessions Count**: 89 physical sessions  
**Total Dataset Duration**: 1605.5 minutes (26.8 hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch 21 (Best Val Macro-F1: 0.8194, Shot Acc: 86.80%, Val Loss: 1.4984, Stopped at Epoch 24)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-11-02_08-12-15.log`  
**Date**: 2026-11-02 09:08

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set (12 Sessions)** | **714** | **711** | **91.88%** (656/714) | **92.26%** (656/711) | **92.07%** |
| **Training Set Micro Average (68 Sessions)** | **4431** | **4305** | **89.84%** (3981/4431) | **92.47%** (3981/4305) | **91.14%** |
| 🏆 **Clean Benchmark Micro Average (89 Sessions)** | **5145** | **5016** | 🏆 **90.13%** (4637/5145) | 🏆 **92.44%** (4637/5016) | 🏆 **91.27%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (12 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 134 | 126 | 94.0% | 111 | **88.1%** | **82.8%** |
| **DRIVE/DEFENCE** | 196 | 180 | 91.8% | 145 | **80.6%** | **74.0%** |
| **GLANCE/FLICK** | 131 | 124 | 94.7% | 106 | **85.5%** | **80.9%** |
| **CUT/PUNCH** | 70 | 64 | 91.4% | 53 | **82.8%** | **75.7%** |
| **DEFLECTION/GUIDE** | 76 | 64 | 84.2% | 55 | **85.9%** | **72.4%** |
| **POWER DRIVE** | 48 | 45 | 93.8% | 41 | **91.1%** | **85.4%** |
| **SWEEP** | 59 | 53 | 89.8% | 46 | **86.8%** | **78.0%** |
| **OVERALL TOTAL** | **714** | **656** | **91.9%** | **557** | 🏆 **84.9%** | 🏆 **78.0%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (77 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1253 | 1138 | 90.8% | 1064 | **93.5%** | **84.9%** |
| **DRIVE/DEFENCE** | 1028 | 934 | 90.9% | 880 | **94.2%** | **85.6%** |
| **GLANCE/FLICK** | 844 | 759 | 89.9% | 716 | **94.3%** | **84.8%** |
| **CUT/PUNCH** | 560 | 498 | 88.9% | 487 | **97.8%** | **87.0%** |
| **DEFLECTION/GUIDE** | 240 | 195 | 81.2% | 189 | **96.9%** | **78.8%** |
| **POWER DRIVE** | 294 | 267 | 90.8% | 265 | **99.3%** | **90.1%** |
| **SWEEP** | 212 | 190 | 89.6% | 167 | **87.9%** | **78.8%** |
| **OVERALL TOTAL** | **4431** | **3981** | **89.8%** | **3768** | 🏆 **94.6%** | 🏆 **85.0%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 89 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1387 | 1264 | 91.1% | 1175 | **93.0%** | **84.7%** |
| **DRIVE/DEFENCE** | 1224 | 1114 | 91.0% | 1025 | **92.0%** | **83.7%** |
| **GLANCE/FLICK** | 975 | 883 | 90.6% | 822 | **93.1%** | **84.3%** |
| **CUT/PUNCH** | 630 | 562 | 89.2% | 540 | **96.1%** | **85.7%** |
| **DEFLECTION/GUIDE** | 316 | 259 | 82.0% | 244 | **94.2%** | **77.2%** |
| **POWER DRIVE** | 342 | 312 | 91.2% | 306 | **98.1%** | **89.5%** |
| **SWEEP** | 271 | 243 | 89.7% | 213 | **87.7%** | **78.6%** |
| **OVERALL TOTAL** | **5145** | **4637** | **90.1%** | **4325** | 🏆 **93.3%** | 🏆 **84.1%** |

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 5 | 100.0% | 80.0% | 88.9%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 58 | 93.4% | 98.3% | 95.8%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 96.4% | 96.4% | 96.4%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 39 | 70.6% | 92.3% | 80.0%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 38 | 66.7% | 78.9% | 72.3%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 56 | 93.1% | 96.4% | 94.7%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 50 | 94.1% | 96.0% | 95.0%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 89.9% | 96.9% | 93.2%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 61 | 100.0% | 93.4% | 96.6%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 55 | 96.5% | 100.0% | 98.2%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 56 | 93.0% | 94.6% | 93.8%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 59 | 96.6% | 96.6% | 96.6%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 60 | 100.0% | 96.7% | 98.3%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 52 | 98.0% | 92.3% | 95.0%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 56 | 96.5% | 98.2% | 97.3%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 53 | 89.7% | 98.1% | 93.7%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 55 | 96.2% | 90.9% | 93.5%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 60 | 100.0% | 96.7% | 98.3%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 54 | 100.0% | 94.4% | 97.1%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 19 | 30.4% | 89.5% | 45.3%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 61 | 65 | 88.5% | 83.1% | 85.7%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 37 | 34 | 83.8% | 91.2% | 87.3%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 58 | 57 | 69.0% | 70.2% | 69.6%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 61 | 98.2% | 91.8% | 94.9%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 61 | 64 | 98.4% | 93.8% | 96.0%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 55 | 98.2% | 98.2% | 98.2%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 44 | 45 | 88.6% | 86.7% | 87.6%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 57 | 90.9% | 87.7% | 89.3%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 26 | 88.9% | 92.3% | 90.6%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 49 | 93.9% | 93.9% | 93.9%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 61 | 83.6% | 83.6% | 83.6%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 58 | 91.9% | 98.3% | 95.0%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 59 | 91.9% | 96.6% | 94.2%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 60 | 93.4% | 95.0% | 94.2%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 70 | 87.7% | 91.4% | 89.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 68 | 97.0% | 94.1% | 95.5%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 66 | 91.3% | 95.5% | 93.3%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 64 | 94.0% | 98.4% | 96.2%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 66 | 92.3% | 90.9% | 91.6%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 64 | 94.8% | 85.9% | 90.2%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 56 | 87.5% | 87.5% | 87.5%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 64 | 59 | 90.6% | 98.3% | 94.3%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 63 | 93.9% | 98.4% | 96.1%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 48 | 85.2% | 95.8% | 90.2%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 65 | 61 | 89.2% | 95.1% | 92.1%
| `session_2026-09-06_11-41-57` | Training | 1.8 | 7 | 6 | 85.7% | 100.0% | 92.3%
| `session_2026-09-06_12-35-47` | Training | 5.3 | 27 | 25 | 92.6% | 100.0% | 96.2%
| `session_2026-09-07_12-29-10` | Training | 20.3 | 60 | 50 | 71.7% | 86.0% | 78.2%
| `session_2026-09-14_12-56-40` | Training | 21.2 | 53 | 56 | 96.2% | 91.1% | 93.6%
| `session_2026-09-18_12-48-53` | Training | 20.5 | 68 | 66 | 94.1% | 97.0% | 95.5%
| `session_2026-09-30_12-52-29` | Training | 20.2 | 63 | 60 | 90.5% | 95.0% | 92.7%
| `session_2026-10-05_12-53-51` | Training | 20.6 | 67 | 61 | 85.1% | 93.4% | 89.1%
| `session_2026-10-06_12-49-35` | Training | 24.2 | 73 | 68 | 89.0% | 95.6% | 92.2%
| `session_2026-10-08_12-55-02` | Training | 20.6 | 69 | 69 | 82.6% | 82.6% | 82.6%
| `session_2026-10-16_12-59-39` | Training | 19.6 | 69 | 65 | 85.5% | 90.8% | 88.1%
| `session_2026-10-18_14-46-16` | Training | 19.2 | 64 | 64 | 87.5% | 87.5% | 87.5%
| `session_2026-10-19_12-47-59` | Training | 19.4 | 67 | 71 | 94.0% | 88.7% | 91.3%
| `session_2026-10-20_12-39-32` | Training | 18.9 | 70 | 66 | 88.6% | 93.9% | 91.2%
| `session_2026-10-22_12-57-41` | Training | 19.7 | 73 | 67 | 87.7% | 95.5% | 91.4%
| `session_2026-10-23_13-02-03` | Training | 20.4 | 62 | 65 | 87.1% | 83.1% | 85.0%
| `session_2026-10-26_12-57-14` | Training | 27.0 | 64 | 57 | 78.1% | 87.7% | 82.6%
| `session_2026-10-27_12-44-30` | Training | 18.9 | 72 | 62 | 81.9% | 95.2% | 88.1%
| `session_2026-10-29_12-19-24` | Training | 19.6 | 72 | 72 | 90.3% | 90.3% | 90.3%
| `session_2026-10-30_12-49-13` | Training | 22.0 | 66 | 72 | 95.5% | 87.5% | 91.3%
| `session_2026-11-01_15-20-45` | Training | 20.6 | 77 | 75 | 90.9% | 93.3% | 92.1%
| `session_2026-06-21_13-53-17` | 🔹 VALIDATION | 20.2 | 55 | 59 | 98.2% | 91.5% | 94.7%
| `session_2026-06-27_14-12-40` | 🔹 VALIDATION | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-07-02_12-38-53` | 🔹 VALIDATION | 20.9 | 59 | 58 | 98.3% | 100.0% | 99.1%
| `session_2026-07-24_12-52-29` | 🔹 VALIDATION | 17.9 | 52 | 52 | 78.8% | 78.8% | 78.8%
| `session_2026-08-06_12-51-06` | 🔹 VALIDATION | 17.0 | 58 | 59 | 84.5% | 83.1% | 83.8%
| `session_2026-08-17_12-51-22` | 🔹 VALIDATION | 19.2 | 64 | 57 | 84.4% | 94.7% | 89.3%
| `session_2026-09-10_12-55-41` | 🔹 VALIDATION | 19.4 | 60 | 56 | 88.3% | 94.6% | 91.4%
| `session_2026-10-04_15-30-15` | 🔹 VALIDATION | 15.0 | 67 | 65 | 92.5% | 95.4% | 93.9%
| `session_2026-10-15_12-49-52` | 🔹 VALIDATION | 20.0 | 58 | 59 | 93.1% | 91.5% | 92.3%
| `session_2026-06-12_12-24-37` | 🌟 HOLDOUT TEST | 20.9 | 70 | 69 | 97.1% | 98.6% | 97.8%
| `session_2026-06-19_12-25-55` | 🌟 HOLDOUT TEST | 16.7 | 56 | 57 | 96.4% | 94.7% | 95.6%
| `session_2026-06-25_12-25-07` | 🌟 HOLDOUT TEST | 21.2 | 65 | 64 | 95.4% | 96.9% | 96.1%
| `session_2026-06-28_11-28-09` | 🌟 HOLDOUT TEST | 19.8 | 52 | 54 | 96.2% | 92.6% | 94.3%
| `session_2026-07-27_12-47-20` | 🌟 HOLDOUT TEST | 18.1 | 53 | 55 | 92.5% | 89.1% | 90.7%
| `session_2026-08-08_10-43-42` | 🌟 HOLDOUT TEST | 29.8 | 77 | 79 | 88.3% | 86.1% | 87.2%
| `session_2026-08-16_14-10-23` | 🌟 HOLDOUT TEST | 11.8 | 50 | 45 | 90.0% | 100.0% | 94.7%
| `session_2026-08-22_14-25-31` | 🌟 HOLDOUT TEST | 12.0 | 51 | 48 | 90.2% | 95.8% | 92.9%
| `session_2026-09-08_12-52-30` | 🌟 HOLDOUT TEST | 22.7 | 57 | 55 | 84.2% | 87.3% | 85.7%
| `session_2026-09-17_12-48-47` | 🌟 HOLDOUT TEST | 20.3 | 62 | 60 | 91.9% | 95.0% | 93.4%
| `session_2026-10-09_12-41-17` | 🌟 HOLDOUT TEST | 20.1 | 51 | 59 | 96.1% | 83.1% | 89.1%
| `session_2026-10-17_11-47-47` | 🌟 HOLDOUT TEST | 18.9 | 70 | 66 | 85.7% | 90.9% | 88.2%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **NOT_DETECTED (MISSING_CANDIDATE)** | **54** | DRIVE/DEFENCE (15), DEFLECTION/GUIDE (11), GLANCE/FLICK (9) |
| **SUBCLASS_CONFUSION** | **40** | DRIVE/DEFENCE (25), GLANCE/FLICK (6), DEFLECTION/GUIDE (5) |
| **VERTICAL_BAT_CONFUSION** | **24** | PULL/HOOK/SLOG (13), CUT/PUNCH (11) |
| **SWEEP_CONFUSION** | **22** | GLANCE/FLICK (8), SWEEP (7), DRIVE/DEFENCE (5) |
| **CROSS_BAT_CONFUSION** | **14** | DRIVE/DEFENCE (7), DEFLECTION/GUIDE (4), GLANCE/FLICK (3) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-06-12_12-24-37` | 138.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 132.22 | -6.13 | *pull shot four facing up* |
| `session_2026-06-12_12-24-37` | 197.07 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 195.39 | -1.68 | *flick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 632.67 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 627.36 | -5.31 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 654.71 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.54 | 654.65 | -0.06 | *good shot okay facing up* |
| `session_2026-06-12_12-24-37` | 753.15 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.62 | 752.84 | -0.31 | *pull shot good* |
| `session_2026-06-12_12-24-37` | 1091.77 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.48 | 1092.03 | +0.26 | *pull shot okay facing up* |
| `session_2026-06-12_12-24-37` | 1134.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.87 | 1134.83 | -0.00 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 1210.09 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.48 | 1210.29 | +0.20 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 1234.72 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.87 | 1234.11 | -0.61 | *which shot okay facing up* |
| `session_2026-06-19_12-25-55` | 45.30 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.52 | 44.29 | -1.01 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 82.28 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.52 | 82.14 | -0.14 | *touch shot four* |
| `session_2026-06-19_12-25-55` | 173.51 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.82 | 173.05 | -0.46 | *cut shot four* |
| `session_2026-06-19_12-25-55` | 500.81 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.72 | 500.29 | -0.52 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 515.69 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.81 | 515.62 | -0.07 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 526.84 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.56 | 525.88 | -0.96 | *cut shot okay* |
| `session_2026-06-19_12-25-55` | 537.24 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.68 | 537.01 | -0.23 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 595.40 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.75 | 595.25 | -0.15 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 810.97 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 805.91 | -5.06 | *back foot drive good facing up* |
| `session_2026-06-19_12-25-55` | 860.39 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 867.78 | +7.39 | *cut shot four facing up* |
| `session_2026-06-25_12-25-07` | 12.82 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 63.80 | +50.98 | *alright let's get going* |
| `session_2026-06-25_12-25-07` | 53.84 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 63.80 | +9.96 | *alright facing up* |
| `session_2026-06-25_12-25-07` | 65.20 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.63 | 63.80 | -1.40 | *flick shot okay facing up* |
| `session_2026-06-25_12-25-07` | 101.08 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.89 | 100.93 | -0.15 | *flip shot okay* |
| `session_2026-06-25_12-25-07` | 142.89 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.92 | 142.99 | +0.10 | *forward defense okay* |
| `session_2026-06-25_12-25-07` | 222.57 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.57 | 222.56 | -0.01 | *quick shot good* |
| `session_2026-06-25_12-25-07` | 602.93 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.80 | 602.43 | -0.50 | *on drive good* |
| `session_2026-06-25_12-25-07` | 645.95 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.55 | 645.01 | -0.94 | *back defense good facing up flick shot okay* |
| `session_2026-06-25_12-25-07` | 1019.92 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1027.93 | +8.01 | *alright match day bat facing up* |
| `session_2026-06-25_12-25-07` | 1138.55 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.91 | 1138.30 | -0.25 | *pull shot miss* |
| `session_2026-06-28_11-28-09` | 192.39 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.65 | 192.79 | +0.40 | *sweep shot four* |
| `session_2026-06-28_11-28-09` | 206.55 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.81 | 206.44 | -0.11 | *weep shot okay* |
| `session_2026-06-28_11-28-09` | 216.85 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.87 | 216.83 | -0.02 | *pull shot ah sweep shot okay* |
| `session_2026-06-28_11-28-09` | 303.94 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.62 | 304.02 | +0.08 | *on drive okay* |
| `session_2026-06-28_11-28-09` | 596.17 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.46 | 596.52 | +0.35 | *slip shot good* |
| `session_2026-06-28_11-28-09` | 605.08 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.81 | 605.25 | +0.17 | *flick shot good* |
| `session_2026-06-28_11-28-09` | 673.45 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 671.90 | -1.55 | *forward defense okay facing up* |
| `session_2026-06-28_11-28-09` | 756.41 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.70 | 756.62 | +0.21 | *slip shot miss in the round* |
| `session_2026-06-28_11-28-09` | 996.15 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1004.92 | +8.77 | *fence four* |
| `session_2026-06-28_11-28-09` | 1012.49 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.45 | 1012.87 | +0.38 | *sweep shot good* |
| `session_2026-06-28_11-28-09` | 1035.39 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.76 | 1035.35 | -0.04 | *slip shot okay* |
| `session_2026-06-28_11-28-09` | 1105.97 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.55 | 1106.10 | +0.13 | *sweep shot okay* |
| `session_2026-06-28_11-28-09` | 1139.97 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.73 | 1140.13 | +0.16 | *slip shot miss* |
| `session_2026-06-28_11-28-09` | 1170.12 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.62 | 1170.49 | +0.37 | *sweep shot okay* |
| `session_2026-06-28_11-28-09` | 1175.13 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1170.49 | -4.64 | *losing up sweep shot four* |
| `session_2026-07-27_12-47-20` | 49.45 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 67.63 | +18.17 | *back defense or* |
| `session_2026-07-27_12-47-20` | 58.09 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 67.63 | +9.53 | *back fence good* |
| `session_2026-07-27_12-47-20` | 593.84 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 588.87 | -4.97 | *quick shot miss* |
| `session_2026-07-27_12-47-20` | 623.75 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.65 | 623.75 | +0.00 | *pull shot okay* |
| `session_2026-07-27_12-47-20` | 995.06 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 999.57 | +4.51 | *back foot defense good facing up* |
| `session_2026-07-27_12-47-20` | 1041.11 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.46 | 1041.11 | +0.00 | *which shot good* |
| `session_2026-08-08_10-43-42` | 4.03 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.03 | +71.00 | *alright* |
| `session_2026-08-08_10-43-42` | 93.73 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.50 | 93.41 | -0.32 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 547.09 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.94 | 547.09 | +0.00 | *power drive flog good* |
| `session_2026-08-08_10-43-42` | 550.07 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 547.09 | -2.98 | *facing up power drive good* |
| `session_2026-08-08_10-43-42` | 576.77 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.45 | 576.77 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 621.53 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.71 | 621.53 | +0.00 | *flick shot good* |
| `session_2026-08-08_10-43-42` | 646.99 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.54 | 646.99 | +0.00 | *power drive good* |
| `session_2026-08-08_10-43-42` | 650.49 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 646.99 | -3.49 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 698.30 | **DRIVE/DEFENCE** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.98 | 698.30 | +0.00 | *facing up on drive good* |
| `session_2026-08-08_10-43-42` | 1023.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.65 | 1023.83 | +0.00 | *pull shot pour* |
| `session_2026-08-08_10-43-42` | 1111.81 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.70 | 1111.81 | +0.00 | *power drive okay facing up* |
| `session_2026-08-08_10-43-42` | 1148.89 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.99 | 1148.90 | +0.00 | *power drive good facing up pull shot okay* |
| `session_2026-08-08_10-43-42` | 1658.33 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1646.78 | -11.55 | *guide okay* |
| `session_2026-08-08_10-43-42` | 1694.85 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1702.75 | +7.90 | *guide okay facing up* |
| `session_2026-08-08_10-43-42` | 1756.25 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1753.03 | -3.22 | *guide okay* |
| `session_2026-08-16_14-10-23` | 41.96 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 52.18 | +10.22 | *straight shot okay* |
| `session_2026-08-16_14-10-23` | 88.11 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.85 | 88.11 | +0.00 | *swipe shot okay* |
| `session_2026-08-16_14-10-23` | 97.28 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 88.11 | -9.18 | *sweep shot okay* |
| `session_2026-08-16_14-10-23` | 108.31 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.85 | +18.54 | *sweep shot okay* |
| `session_2026-08-16_14-10-23` | 117.57 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.85 | +9.28 | *sweep shot good* |
| `session_2026-08-16_14-10-23` | 154.34 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.84 | 154.34 | +0.00 | *slip shot okay* |
| `session_2026-08-16_14-10-23` | 174.52 | **SWEEP** | POWER DRIVE | `SWEEP_CONFUSION` | 0.18 | 174.52 | +0.00 | *we've shot good* |
| `session_2026-08-16_14-10-23` | 198.42 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.86 | 198.42 | +0.00 | *on drive okay* |
| `session_2026-08-16_14-10-23` | 207.71 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.50 | 207.71 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 315.28 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.69 | 315.28 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 324.98 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.56 | 324.98 | +0.00 | *flick shot good* |
| `session_2026-08-16_14-10-23` | 349.05 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.68 | 349.05 | +0.00 | *quick shot okay* |
| `session_2026-08-16_14-10-23` | 546.84 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.72 | 546.84 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 568.24 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.85 | 568.24 | +0.00 | *sweep shot pull* |
| `session_2026-08-16_14-10-23` | 642.60 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.73 | 642.60 | +0.00 | *straight shot good* |
| `session_2026-08-16_14-10-23` | 652.74 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.91 | 652.74 | +0.00 | *straight shot okay* |
| `session_2026-08-16_14-10-23` | 686.70 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 695.84 | +9.15 | *sweep shot good* |
| `session_2026-08-22_14-25-31` | 59.97 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.58 | 59.97 | +0.00 | *back foot punch good facing up* |
| `session_2026-08-22_14-25-31` | 115.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 113.39 | -2.54 | *glide four* |
| `session_2026-08-22_14-25-31` | 186.91 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 184.91 | -1.99 | *facing back foot punch okay* |
| `session_2026-08-22_14-25-31` | 328.01 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 324.85 | -3.17 | *facing up cut shot four* |
| `session_2026-08-22_14-25-31` | 363.73 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.94 | 363.73 | +0.00 | *back foot punch okay facing up cut shot okay* |
| `session_2026-08-22_14-25-31` | 406.87 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.48 | 406.87 | +0.00 | *cut shot good* |
| `session_2026-08-22_14-25-31` | 414.57 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.96 | 414.57 | +0.00 | *alright foot defense okay end of round* |
| `session_2026-08-22_14-25-31` | 584.56 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.84 | 584.56 | +0.00 | *guide okay facing up* |
| `session_2026-08-22_14-25-31` | 649.80 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.93 | 649.80 | +0.00 | *back foot punch okay facing up* |
| `session_2026-08-22_14-25-31` | 685.21 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.64 | 685.22 | +0.00 | *that's a punch four* |
| `session_2026-09-08_12-52-30` | 86.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 93.58 | +7.23 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 119.46 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.86 | 119.46 | +0.00 | *click shot or facing up* |
| `session_2026-09-08_12-52-30` | 124.67 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.66 | 124.67 | +0.00 | *glide okay facing up* |
| `session_2026-09-08_12-52-30` | 142.71 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.86 | 142.71 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 209.12 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 207.59 | -1.52 | *facing up cut shot okay* |
| `session_2026-09-08_12-52-30` | 269.40 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 260.92 | -8.48 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 576.33 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.56 | 576.33 | +0.00 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 594.85 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.41 | 594.58 | -0.26 | *back foot defense four* |
| `session_2026-09-08_12-52-30` | 594.58 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.41 | 594.58 | +0.00 | *facing up back foot defense okay* |
| `session_2026-09-08_12-52-30` | 738.76 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.82 | 738.76 | +0.00 | *back foot punch good facing up cut shot pour* |
| `session_2026-09-08_12-52-30` | 805.18 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.97 | 805.18 | +0.00 | *push up good facing up* |
| `session_2026-09-08_12-52-30` | 815.13 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 822.57 | +7.44 | *push up facing up* |
| `session_2026-09-08_12-52-30` | 830.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.63 | 830.54 | +0.00 | *on drive okay facing up* |
| `session_2026-09-08_12-52-30` | 1204.95 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1203.14 | -1.80 | *glide miss* |
| `session_2026-09-08_12-52-30` | 1217.89 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.78 | 1217.89 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 1227.88 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1230.17 | +2.30 | *squad good facing up back foot punch good* |
| `session_2026-09-08_12-52-30` | 1259.47 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.91 | 1259.48 | +0.00 | *back foot punch good facing up glide edge facing* |
| `session_2026-09-08_12-52-30` | 1289.69 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1280.66 | -9.03 | *wide miss* |
| `session_2026-09-08_12-52-30` | 1345.95 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.77 | 1345.95 | +0.00 | *back foot punch good* |
| `session_2026-09-17_12-48-47` | 118.16 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.31 | +8.15 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 135.02 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +8.66 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 138.93 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +4.75 | *straight drive edge* |
| `session_2026-09-17_12-48-47` | 177.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.77 | 177.87 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 254.51 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.75 | 254.51 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 298.25 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.39 | 299.71 | +1.46 | *facing up on drive good* |
| `session_2026-09-17_12-48-47` | 560.86 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.57 | 560.86 | +0.00 | *on drive good facing up* |
| `session_2026-09-17_12-48-47` | 570.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.73 | 570.88 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 646.60 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.68 | 646.61 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 677.45 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 680.90 | +3.45 | *facing up switch shot okay* |
| `session_2026-09-17_12-48-47` | 699.56 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.53 | 699.57 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 752.91 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 754.72 | +1.81 | *facing up good shot okay in the ground* |
| `session_2026-09-17_12-48-47` | 1005.67 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1017.22 | +11.55 | *facing up flick shot okay* |
| `session_2026-09-17_12-48-47` | 1129.36 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.81 | 1129.36 | +0.00 | *push shot miss* |
| `session_2026-09-17_12-48-47` | 1146.77 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.81 | 1146.77 | +0.00 | *on drive 4 facing up* |
| `session_2026-09-17_12-48-47` | 1210.75 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.40 | 1210.75 | +0.00 | *on drive good end of round end of sessions* |
| `session_2026-10-09_12-41-17` | 175.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.74 | 175.55 | +0.00 | *back foot defense or* |
| `session_2026-10-09_12-41-17` | 233.34 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 226.52 | -6.83 | *flick shot okay* |
| `session_2026-10-09_12-41-17` | 256.66 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.86 | 256.66 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 269.28 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.59 | 269.29 | +0.00 | *foot shot okay facing up back foot defense okay in the ground* |
| `session_2026-10-09_12-41-17` | 609.90 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.59 | 609.91 | +0.00 | *back foot defense poor* |
| `session_2026-10-09_12-41-17` | 665.70 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.83 | 665.70 | +0.00 | *back foot defense four* |
| `session_2026-10-09_12-41-17` | 674.49 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.44 | 674.49 | +0.00 | *back foot punch edge* |
| `session_2026-10-09_12-41-17` | 688.03 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.68 | 688.04 | +0.00 | *glide okay facing it* |
| `session_2026-10-09_12-41-17` | 696.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.94 | 696.30 | +0.00 | *crackle punch okay facing it* |
| `session_2026-10-09_12-41-17` | 704.35 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.50 | 704.35 | +0.00 | *glide edge* |
| `session_2026-10-09_12-41-17` | 1002.62 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.68 | 1002.62 | +0.00 | *back foot defense good* |
| `session_2026-10-09_12-41-17` | 1097.32 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.80 | 1097.32 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 1102.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1097.32 | -4.99 | *facing clive okay* |
| `session_2026-10-09_12-41-17` | 1144.86 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.44 | 1144.86 | +0.00 | *glide okay facing up* |
| `session_2026-10-09_12-41-17` | 1152.49 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.57 | 1152.49 | +0.00 | *guide miss* |
| `session_2026-10-17_11-47-47` | 122.63 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 120.27 | -2.36 | *facing up glance good* |
| `session_2026-10-17_11-47-47` | 140.46 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 135.17 | -5.29 | *facing up oh blanks miss* |
| `session_2026-10-17_11-47-47` | 167.64 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 166.07 | -1.57 | *lacing up flick shot good* |
| `session_2026-10-17_11-47-47` | 216.38 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 213.49 | -2.88 | *facing up on drive okay facing up* |
| `session_2026-10-17_11-47-47` | 233.82 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.65 | 233.82 | +0.00 | *back foot defense or facing up* |
| `session_2026-10-17_11-47-47` | 255.05 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.64 | 255.05 | +0.00 | *on drive good* |
| `session_2026-10-17_11-47-47` | 609.03 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 605.40 | -3.63 | *facing up glance miss* |
| `session_2026-10-17_11-47-47` | 631.08 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 634.35 | +3.27 | *facing up pull shot okay* |
| `session_2026-10-17_11-47-47` | 968.86 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 963.65 | -5.20 | *facing up pull shot miss* |
| `session_2026-10-17_11-47-47` | 990.21 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 997.12 | +6.91 | *pull shot edge* |
| `session_2026-10-17_11-47-47` | 1016.02 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1010.32 | -5.69 | *facing up pull shot good* |
| `session_2026-10-17_11-47-47` | 1048.96 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1055.30 | +6.34 | *facing up pull shot okay* |

