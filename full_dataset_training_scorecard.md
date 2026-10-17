# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline with Phase 2 Learned False-Positive Rejection (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN with Binary Rejection Head)  
**Training Design**: Peak-Centered Candidate Window Training with Hard-Negative Mining (Rejection Head [208d -> 64d -> 2], Backbone L1-7: 1.5e-4, L8-10+Heads: 5e-4, 3-Epoch Warmup, CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.0, 1.0, 1.0], Rejection Threshold $\theta_{no\_shot} = 0.35$)  
**Holdout Test Sessions**: `session_2026-06-12_12-24-37, session_2026-06-16_15-39-33, session_2026-06-19_12-25-55, session_2026-07-05_16-27-16, session_2026-07-20_12-42-16, session_2026-07-25_15-16-32, session_2026-08-11_12-49-31, session_2026-08-21_12-50-53, session_2026-09-08_12-52-30, session_2026-09-17_12-48-47, session_2026-10-05_12-53-51, session_2026-10-09_12-41-17` (12 sessions)  
**Validation Sessions**: `session_2026-06-27_14-12-40, session_2026-07-02_12-38-53, session_2026-08-01_10-18-20, session_2026-08-17_12-51-22, session_2026-08-30_11-05-11, session_2026-09-10_12-55-41, session_2026-10-04_15-30-15` (7 sessions)  
**Quarantined Faulted Sessions (Phase 5 Candidates)**: `session_2026-07-11_12-51-39, session_2026-07-17_12-30-41, session_2026-09-05_16-26-41, session_2026-09-06_12-14-46` (4 sessions)  
**Archived Impaired Sessions**: `session_2026-05-30_15-04-41, session_2026-05-31_14-12-10, session_2026-07-18_13-44-09, session_2026-09-11_12-44-50` (4 sessions)  
**Training Sessions Count**: 59 physical sessions  
**Clean Benchmark Sessions Count**: 78 physical sessions (+5 recovered sessions: `06-29`, `07-12`, `08-07`, `08-27`, `09-30`)  
**Total Dataset Duration**: 1378.2 minutes (23.0 hours)  
**Validation Macro-F1 Checkpointing**: Best Epoch Reloaded Checkpoint (Best Val Macro-F1: 0.6356, Shot Acc: 63.59%, Val Loss: 1.1914, Stopped at Epoch 28)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-10-16_15-33-31.log`  
**Date**: 2026-10-17 17:13  

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Test Set (12 Sessions)** | **701** | **710** | **91.73%** (643/701) | **90.56%** (643/710) | **91.14%** |
| **Training Set Micro Average (59 Sessions)** | **3687** | **3694** | **89.97%** (3317/3687) | **89.79%** (3317/3694) | **89.88%** |
| 🏆 **Clean Benchmark Micro Average (78 Sessions)** | **4388** | **4404** | 🏆 **90.25%** (3960/4388) | 🏆 **89.92%** (3960/4404) | 🏆 **90.08%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (12 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 111 | 105 | 94.6% | 69 | **65.7%** | **62.2%** |
| **DRIVE/DEFENCE** | 198 | 180 | 90.9% | 149 | **82.8%** | **75.3%** |
| **GLANCE/FLICK** | 59 | 56 | 94.9% | 29 | **51.8%** | **49.2%** |
| **CUT/PUNCH** | 102 | 96 | 94.1% | 89 | **92.7%** | **87.3%** |
| **DEFLECTION/GUIDE** | 112 | 90 | 80.4% | 79 | **87.8%** | **70.5%** |
| **POWER DRIVE** | 57 | 57 | 100.0% | 25 | **43.9%** | **43.9%** |
| **SWEEP** | 62 | 59 | 95.2% | 46 | **78.0%** | **74.2%** |
| **OVERALL TOTAL** | **701** | **643** | **91.7%** | **486** | 🏆 **75.6%** | 🏆 **69.3%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (66 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1060 | 958 | 90.4% | 854 | **89.1%** | **80.6%** |
| **DRIVE/DEFENCE** | 899 | 820 | 91.2% | 719 | **87.7%** | **80.0%** |
| **GLANCE/FLICK** | 694 | 631 | 90.9% | 535 | **84.8%** | **77.1%** |
| **CUT/PUNCH** | 345 | 319 | 92.5% | 302 | **94.7%** | **87.5%** |
| **DEFLECTION/GUIDE** | 196 | 145 | 74.0% | 131 | **90.3%** | **66.8%** |
| **POWER DRIVE** | 285 | 255 | 89.5% | 249 | **97.6%** | **87.4%** |
| **SWEEP** | 208 | 189 | 90.9% | 176 | **93.1%** | **84.6%** |
| **OVERALL TOTAL** | **3687** | **3317** | **90.0%** | **2966** | 🏆 **89.4%** | 🏆 **80.4%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 78 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1171 | 1063 | 90.8% | 923 | **86.8%** | **78.8%** |
| **DRIVE/DEFENCE** | 1097 | 1000 | 91.2% | 868 | **86.8%** | **79.1%** |
| **GLANCE/FLICK** | 753 | 687 | 91.2% | 564 | **82.1%** | **74.9%** |
| **CUT/PUNCH** | 447 | 415 | 92.8% | 391 | **94.2%** | **87.5%** |
| **DEFLECTION/GUIDE** | 308 | 235 | 76.3% | 210 | **89.4%** | **68.2%** |
| **POWER DRIVE** | 342 | 312 | 91.2% | 274 | **87.8%** | **80.1%** |
| **SWEEP** | 270 | 248 | 91.9% | 222 | **89.5%** | **82.2%** |
| **OVERALL TOTAL** | **4388** | **3960** | **90.2%** | **3452** | 🏆 **87.2%** | 🏆 **78.7%** |

---

## 📋 Session-by-Session Clean Benchmark Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 4 | 75.0% | 75.0% | 75.0%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 60 | 93.4% | 95.0% | 94.2%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 96.4% | 96.4% | 96.4%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 41 | 70.6% | 87.8% | 78.3%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 41 | 68.9% | 75.6% | 72.1%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 58 | 94.8% | 94.8% | 94.8%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 96.1% | 92.5% | 94.2%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 55 | 87.1% | 98.2% | 92.3%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 65 | 89.9% | 95.4% | 92.5%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 60 | 98.2% | 90.0% | 93.9%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 54 | 94.7% | 100.0% | 97.3%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 55 | 91.2% | 94.5% | 92.9%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 65 | 95.4% | 95.4% | 95.4%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 60 | 96.6% | 95.0% | 95.8%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 52 | 92.3% | 92.3% | 92.3%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 53 | 98.0% | 90.6% | 94.1%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 55 | 93.1% | 98.2% | 95.6%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 51 | 86.5% | 88.2% | 87.4%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 62 | 100.0% | 93.5% | 96.7%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 55 | 94.1% | 87.3% | 90.6%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 61 | 67 | 90.2% | 82.1% | 85.9%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 58 | 62 | 72.4% | 67.7% | 70.0%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 61 | 98.2% | 91.8% | 94.9%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 52 | 57 | 82.7% | 75.4% | 78.9%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 59 | 98.2% | 91.5% | 94.7%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 54 | 90.6% | 88.9% | 89.7%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 44 | 47 | 81.8% | 76.6% | 79.1%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 63 | 90.9% | 79.4% | 84.7%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 51 | 93.9% | 90.2% | 92.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 64 | 83.6% | 79.7% | 81.6%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 58 | 59 | 84.5% | 83.1% | 83.8%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 79 | 88.3% | 86.1% | 87.2%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 64 | 93.4% | 89.1% | 91.2%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 70 | 87.7% | 91.4% | 89.5%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 51 | 98.0% | 96.1% | 97.0%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 67 | 93.9% | 92.5% | 93.2%
| `session_2026-08-22_14-25-31` | Training | 12.0 | 51 | 51 | 90.2% | 90.2% | 90.2%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 66 | 94.0% | 95.5% | 94.7%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 92.3% | 89.6% | 90.9%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 62 | 89.3% | 80.6% | 84.7%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 64 | 92.4% | 95.3% | 93.8%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 51 | 81.5% | 86.3% | 83.8%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 65 | 61 | 89.2% | 95.1% | 92.1%
| `session_2026-09-06_11-41-57` | Training | 1.8 | 7 | 6 | 85.7% | 100.0% | 92.3%
| `session_2026-09-06_12-35-47` | Training | 5.3 | 27 | 26 | 92.6% | 96.2% | 94.3%
| `session_2026-09-07_12-29-10` | Training | 20.3 | 60 | 56 | 73.3% | 78.6% | 75.9%
| `session_2026-09-14_12-56-40` | Training | 21.2 | 53 | 58 | 96.2% | 87.9% | 91.9%
| `session_2026-09-18_12-48-53` | Training | 20.5 | 68 | 66 | 92.6% | 95.5% | 94.0%
| `session_2026-10-06_12-49-35` | Training | 24.2 | 73 | 72 | 89.0% | 90.3% | 89.7%
| `session_2026-10-08_12-55-02` | Training | 20.6 | 69 | 70 | 81.2% | 80.0% | 80.6%
| `session_2026-10-15_12-49-52` | Training | 20.0 | 58 | 61 | 93.1% | 88.5% | 90.8%
| `session_2026-10-16_12-59-39` | Training | 19.6 | 69 | 71 | 87.0% | 84.5% | 85.7%
| `session_2026-06-27_14-12-40` | 🔹 VALIDATION | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-07-02_12-38-53` | 🔹 VALIDATION | 20.9 | 59 | 59 | 98.3% | 98.3% | 98.3%
| `session_2026-08-01_10-18-20` | 🔹 VALIDATION | 8.9 | 27 | 27 | 88.9% | 88.9% | 88.9%
| `session_2026-08-17_12-51-22` | 🔹 VALIDATION | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
| `session_2026-08-30_11-05-11` | 🔹 VALIDATION | 21.1 | 64 | 63 | 90.6% | 92.1% | 91.3%
| `session_2026-09-10_12-55-41` | 🔹 VALIDATION | 19.4 | 60 | 57 | 88.3% | 93.0% | 90.6%
| `session_2026-10-04_15-30-15` | 🔹 VALIDATION | 15.0 | 67 | 65 | 92.5% | 95.4% | 93.9%
| `session_2026-06-12_12-24-37` | 🌟 HOLDOUT TEST | 20.9 | 70 | 69 | 95.7% | 97.1% | 96.4%
| `session_2026-06-16_15-39-33` | 🌟 HOLDOUT TEST | 16.5 | 52 | 53 | 96.2% | 94.3% | 95.2%
| `session_2026-06-19_12-25-55` | 🌟 HOLDOUT TEST | 16.7 | 56 | 55 | 94.6% | 96.4% | 95.5%
| `session_2026-07-05_16-27-16` | 🌟 HOLDOUT TEST | 18.5 | 57 | 56 | 94.7% | 96.4% | 95.6%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT TEST | 15.3 | 37 | 48 | 91.9% | 70.8% | 80.0%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT TEST | 20.6 | 61 | 65 | 98.4% | 92.3% | 95.2%
| `session_2026-08-11_12-49-31` | 🌟 HOLDOUT TEST | 19.8 | 62 | 64 | 91.9% | 89.1% | 90.5%
| `session_2026-08-21_12-50-53` | 🌟 HOLDOUT TEST | 21.0 | 69 | 63 | 87.0% | 95.2% | 90.9%
| `session_2026-09-08_12-52-30` | 🌟 HOLDOUT TEST | 22.7 | 57 | 57 | 82.5% | 82.5% | 82.5%
| `session_2026-09-17_12-48-47` | 🌟 HOLDOUT TEST | 20.3 | 62 | 59 | 90.3% | 94.9% | 92.6%
| `session_2026-10-05_12-53-51` | 🌟 HOLDOUT TEST | 20.6 | 67 | 63 | 83.6% | 88.9% | 86.2%
| `session_2026-10-09_12-41-17` | 🌟 HOLDOUT TEST | 20.1 | 51 | 57 | 96.1% | 86.0% | 90.7%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **NOT_DETECTED (MISSING_CANDIDATE)** | **53** | DEFLECTION/GUIDE (18), DRIVE/DEFENCE (18), PULL/HOOK/SLOG (7) |
| **VERTICAL_BAT_CONFUSION** | **41** | PULL/HOOK/SLOG (34), CUT/PUNCH (7) |
| **CROSS_BAT_CONFUSION** | **34** | DRIVE/DEFENCE (22), GLANCE/FLICK (10), DEFLECTION/GUIDE (2) |
| **SUBCLASS_CONFUSION** | **27** | DEFLECTION/GUIDE (10), DRIVE/DEFENCE (7), GLANCE/FLICK (5) |
| **CROSS_BAT_CONFUSION (Macro Gate)** | **27** | POWER DRIVE (27) |
| **SWEEP_CONFUSION** | **26** | SWEEP (13), GLANCE/FLICK (10), DRIVE/DEFENCE (2) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-06-12_12-24-37` | 138.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 132.22 | -6.13 | *pull shot four facing up* |
| `session_2026-06-12_12-24-37` | 197.07 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 195.39 | -1.68 | *flick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 627.23 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.32 | 627.36 | +0.13 | *pull shot okay facing up* |
| `session_2026-06-12_12-24-37` | 632.67 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 627.36 | -5.31 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 664.87 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.59 | 663.70 | -1.17 | *quick shot okay facing up* |
| `session_2026-06-12_12-24-37` | 705.68 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 696.20 | -9.48 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 753.15 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.40 | 752.84 | -0.31 | *pull shot good* |
| `session_2026-06-12_12-24-37` | 1068.99 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.45 | 1069.25 | +0.26 | *pull shot okay* |
| `session_2026-06-12_12-24-37` | 1134.83 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.42 | 1134.83 | -0.00 | *pull shot okay* |
| `session_2026-06-16_15-39-33` | 6.79 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 64.51 | +57.72 | *alright* |
| `session_2026-06-16_15-39-33` | 64.26 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.62 | 64.51 | +0.25 | *straight shot with miss* |
| `session_2026-06-16_15-39-33` | 89.19 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.68 | 89.28 | +0.09 | *quick shot missed* |
| `session_2026-06-16_15-39-33` | 99.53 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.38 | 99.87 | +0.34 | *slip shot four* |
| `session_2026-06-16_15-39-33` | 113.70 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.58 | 113.96 | +0.26 | *quick shot miss* |
| `session_2026-06-16_15-39-33` | 129.64 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.68 | 129.62 | -0.02 | *slip shot miss* |
| `session_2026-06-16_15-39-33` | 139.62 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.63 | 139.63 | +0.01 | *sweep shot okay* |
| `session_2026-06-16_15-39-33` | 150.35 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.68 | 150.59 | +0.24 | *three shot four* |
| `session_2026-06-16_15-39-33` | 169.68 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.62 | 170.00 | +0.32 | *free shot okay* |
| `session_2026-06-16_15-39-33` | 178.56 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.61 | 178.73 | +0.17 | *slip shot okay* |
| `session_2026-06-16_15-39-33` | 199.11 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.56 | 199.32 | +0.21 | *sling shot okay* |
| `session_2026-06-16_15-39-33` | 209.36 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.56 | 209.56 | +0.20 | *sweep shot good* |
| `session_2026-06-16_15-39-33` | 448.21 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.68 | 448.56 | +0.35 | *slip shot four* |
| `session_2026-06-16_15-39-33` | 472.40 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.30 | 472.62 | +0.22 | *slip shot okay* |
| `session_2026-06-16_15-39-33` | 505.82 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.49 | 506.17 | +0.35 | *flick shot okay* |
| `session_2026-06-16_15-39-33` | 534.01 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.35 | 534.39 | +0.38 | *sweet shot okay* |
| `session_2026-06-16_15-39-33` | 555.77 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.52 | 555.79 | +0.02 | *flip shot miss* |
| `session_2026-06-16_15-39-33` | 576.60 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.31 | 576.70 | +0.10 | *foot shot four* |
| `session_2026-06-16_15-39-33` | 791.41 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.36 | 790.77 | -0.64 | *on drive miss* |
| `session_2026-06-16_15-39-33` | 804.61 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 790.77 | -13.84 | *let's try miss* |
| `session_2026-06-16_15-39-33` | 832.41 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.62 | 832.48 | +0.07 | *flip shot miss* |
| `session_2026-06-16_15-39-33` | 844.81 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.71 | 844.50 | -0.31 | *sweep shot four* |
| `session_2026-06-16_15-39-33` | 864.30 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.56 | 864.43 | +0.13 | *flip shot okay* |
| `session_2026-06-16_15-39-33` | 910.66 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.66 | 910.79 | +0.13 | *sleep shot good* |
| `session_2026-06-16_15-39-33` | 920.42 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.56 | 920.86 | +0.44 | *sleep shot good* |
| `session_2026-06-16_15-39-33` | 968.92 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.76 | 969.00 | +0.08 | *flick shot poor* |
| `session_2026-06-16_15-39-33` | 978.36 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.56 | 978.45 | +0.09 | *flick shot good end of round in the session* |
| `session_2026-06-19_12-25-55` | 45.30 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.78 | 44.29 | -1.01 | *cut shot okay facing up* |
| `session_2026-06-19_12-25-55` | 52.19 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 44.29 | -7.90 | *glide good* |
| `session_2026-06-19_12-25-55` | 62.59 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 72.78 | +10.19 | *glide miss* |
| `session_2026-06-19_12-25-55` | 173.51 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.47 | 173.05 | -0.46 | *cut shot four* |
| `session_2026-06-19_12-25-55` | 477.79 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.49 | 477.13 | -0.66 | *back foot punch good* |
| `session_2026-06-19_12-25-55` | 515.69 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.52 | 515.62 | -0.07 | *cut shot good* |
| `session_2026-06-19_12-25-55` | 810.97 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 805.91 | -5.06 | *back foot drive good facing up* |
| `session_2026-06-19_12-25-55` | 832.73 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.67 | 831.89 | -0.84 | *back foot punch okay facing up back foot drive okay facing up* |
| `session_2026-06-19_12-25-55` | 860.39 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.61 | 859.04 | -1.35 | *cut shot four facing up* |
| `session_2026-06-19_12-25-55` | 988.68 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.68 | 987.71 | -0.97 | *back foot punch okay facing up* |
| `session_2026-07-05_16-27-16` | 4.33 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 51.30 | +46.97 | *alright* |
| `session_2026-07-05_16-27-16` | 53.80 | **POWER DRIVE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 51.30 | -2.50 | *power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 89.89 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 97.37 | +7.48 | *fence edge facing up* |
| `session_2026-07-05_16-27-16` | 115.02 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.44 | 114.21 | -0.81 | *slog good* |
| `session_2026-07-05_16-27-16` | 129.97 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 121.63 | -8.34 | *defense edge* |
| `session_2026-07-05_16-27-16` | 160.88 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.35 | 161.02 | +0.14 | *power drive missed* |
| `session_2026-07-05_16-27-16` | 170.57 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.33 | 170.57 | +0.00 | *power drive edge* |
| `session_2026-07-05_16-27-16` | 212.30 | **POWER DRIVE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.69 | 211.64 | -0.66 | *power drive edge* |
| `session_2026-07-05_16-27-16` | 470.56 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 468.74 | -1.82 | *straight drive good good facing up* |
| `session_2026-07-05_16-27-16` | 498.94 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.51 | 499.19 | +0.25 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 517.47 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.66 | 517.47 | -0.00 | *power drive good* |
| `session_2026-07-05_16-27-16` | 528.21 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.48 | 528.26 | +0.05 | *power drive good* |
| `session_2026-07-05_16-27-16` | 542.44 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.55 | 542.17 | -0.27 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 550.52 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.56 | 550.35 | -0.17 | *power drive good* |
| `session_2026-07-05_16-27-16` | 565.74 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.47 | 565.42 | -0.32 | *good shot okay* |
| `session_2026-07-05_16-27-16` | 573.71 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.55 | 573.21 | -0.50 | *power drive or* |
| `session_2026-07-05_16-27-16` | 598.25 | **DRIVE/DEFENCE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.55 | 598.31 | +0.06 | *no drive edge* |
| `session_2026-07-05_16-27-16` | 608.17 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.52 | 606.71 | -1.46 | *quick shot edge* |
| `session_2026-07-05_16-27-16` | 639.71 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.46 | 639.95 | +0.24 | *power shot good* |
| `session_2026-07-05_16-27-16` | 648.26 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.48 | 648.34 | +0.08 | *power drive good* |
| `session_2026-07-05_16-27-16` | 655.52 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.35 | 655.23 | -0.29 | *quick shot good end of round* |
| `session_2026-07-05_16-27-16` | 934.00 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.44 | 933.43 | -0.57 | *power drive good facing up power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 949.27 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.55 | 949.25 | -0.02 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 958.22 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.53 | 958.26 | +0.04 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 976.73 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.53 | 976.74 | +0.01 | *power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 983.77 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.44 | 983.07 | -0.70 | *power drive four facing up* |
| `session_2026-07-05_16-27-16` | 1013.02 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.54 | 1012.98 | -0.04 | *power drive good* |
| `session_2026-07-05_16-27-16` | 1020.86 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.45 | 1020.86 | +0.00 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1032.78 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.46 | 1032.96 | +0.18 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1043.02 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.53 | 1042.56 | -0.46 | *power drive okay facing up* |
| `session_2026-07-05_16-27-16` | 1048.27 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.45 | 1048.01 | -0.26 | *power drive okay* |
| `session_2026-07-05_16-27-16` | 1075.66 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.55 | 1074.97 | -0.69 | *make oh shot okay facing up power drive good* |
| `session_2026-07-05_16-27-16` | 1095.94 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1093.93 | -2.01 | *pull shot okay facing up* |
| `session_2026-07-05_16-27-16` | 1101.13 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.39 | 1101.17 | +0.04 | *power shot okay* |
| `session_2026-07-20_12-42-16` | 62.99 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.32 | 62.99 | +0.00 | *sweep shot okay* |
| `session_2026-07-20_12-42-16` | 78.12 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 92.25 | +14.13 | *sweep shot miss* |
| `session_2026-07-20_12-42-16` | 142.16 | **SWEEP** | GLANCE/FLICK | `SWEEP_CONFUSION` | 0.44 | 142.16 | +0.00 | *sweep shot good* |
| `session_2026-07-20_12-42-16` | 165.86 | **SWEEP** | POWER DRIVE | `SWEEP_CONFUSION` | 0.27 | 165.30 | -0.55 | *sweep shot good* |
| `session_2026-07-20_12-42-16` | 375.43 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 380.12 | +4.69 | *sweep shot miss facing up* |
| `session_2026-07-20_12-42-16` | 429.95 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.54 | 429.95 | +0.00 | *flip shot edge* |
| `session_2026-07-20_12-42-16` | 459.47 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.31 | 459.47 | +0.00 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 557.88 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.74 | 557.88 | +0.00 | *straight shot good end of round* |
| `session_2026-07-20_12-42-16` | 749.59 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 753.46 | +3.87 | *slip shot okay facing up* |
| `session_2026-07-20_12-42-16` | 798.04 | **SWEEP** | CUT/PUNCH | `SWEEP_CONFUSION` | 0.25 | 797.38 | -0.66 | *sweep shot miss* |
| `session_2026-07-25_15-16-32` | 82.82 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.62 | 82.82 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 98.78 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.43 | 98.78 | +0.00 | *pull shot okay* |
| `session_2026-07-25_15-16-32` | 119.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.66 | 119.11 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 142.49 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.64 | 142.49 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 150.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.38 | 150.11 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 158.84 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.58 | 158.84 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 178.15 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.53 | 178.15 | +0.00 | *slog four* |
| `session_2026-07-25_15-16-32` | 186.74 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.48 | 186.74 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 226.76 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.40 | 226.76 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 236.32 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.56 | 236.32 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 690.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.51 | 690.11 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 701.13 | **PULL/HOOK/SLOG** | CUT/PUNCH | `SUBCLASS_CONFUSION` | 0.29 | 701.13 | +0.00 | *pull shot edge* |
| `session_2026-07-25_15-16-32` | 711.04 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.60 | 711.04 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 719.08 | **POWER DRIVE** | CUT/PUNCH | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.29 | 719.08 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 721.81 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 719.08 | -2.73 | *slog good facing up* |
| `session_2026-07-25_15-16-32` | 735.36 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.63 | 735.37 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 744.79 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.43 | 744.79 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 751.12 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.63 | 751.12 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 761.25 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.26 | 761.26 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 782.31 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.60 | 782.31 | +0.00 | *power drive pull* |
| `session_2026-07-25_15-16-32` | 809.14 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.53 | 809.14 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 819.15 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.65 | 819.15 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 844.40 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.35 | 844.09 | -0.31 | *slog good* |
| `session_2026-07-25_15-16-32` | 857.54 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.30 | 857.54 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 864.98 | **POWER DRIVE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.27 | 865.08 | +0.10 | *power drive 4 facing up slog good* |
| `session_2026-07-25_15-16-32` | 878.90 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.25 | 878.90 | +0.00 | *slog good in the ground* |
| `session_2026-07-25_15-16-32` | 1052.24 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.43 | 1052.24 | +0.00 | *flick shot okay* |
| `session_2026-07-25_15-16-32` | 1061.78 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.45 | 1061.78 | +0.00 | *slog okay facing up* |
| `session_2026-07-25_15-16-32` | 1069.06 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.52 | 1069.06 | +0.00 | *slog* |
| `session_2026-07-25_15-16-32` | 1078.21 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.48 | 1078.21 | +0.00 | *pull shot okay* |
| `session_2026-07-25_15-16-32` | 1092.55 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.58 | 1092.55 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1101.77 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.27 | 1101.77 | +0.00 | *flick shot good* |
| `session_2026-07-25_15-16-32` | 1109.60 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.45 | 1109.60 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1137.55 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.41 | 1137.56 | +0.00 | *power drive terrible four facing up* |
| `session_2026-07-25_15-16-32` | 1151.34 | **PULL/HOOK/SLOG** | CUT/PUNCH | `SUBCLASS_CONFUSION` | 0.25 | 1151.34 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1162.31 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.40 | 1162.31 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1170.71 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.23 | 1170.71 | +0.00 | *pull shot good* |
| `session_2026-07-25_15-16-32` | 1179.12 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.69 | 1179.12 | +0.00 | *slog good* |
| `session_2026-08-11_12-49-31` | 107.93 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.95 | 107.93 | +0.00 | *back foot punch good facing up cut shot okay* |
| `session_2026-08-11_12-49-31` | 582.38 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.47 | 582.38 | +0.00 | *back foot punch good* |
| `session_2026-08-11_12-49-31` | 689.61 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.58 | 689.61 | +0.00 | *back foot punch good facing up* |
| `session_2026-08-11_12-49-31` | 719.06 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.66 | 719.06 | +0.00 | *back foot punch okay* |
| `session_2026-08-11_12-49-31` | 1134.52 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1132.48 | -2.05 | *facing back foot punch good* |
| `session_2026-08-11_12-49-31` | 1155.67 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.79 | 1155.67 | +0.00 | *back foot defense good facing up cut shot miss* |
| `session_2026-08-21_12-50-53` | 110.49 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 119.23 | +8.74 | *forward defense four* |
| `session_2026-08-21_12-50-53` | 172.13 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 169.05 | -3.08 | *facing up back foot punch miss* |
| `session_2026-08-21_12-50-53` | 202.11 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.29 | 202.11 | +0.00 | *back foot punch miss* |
| `session_2026-08-21_12-50-53` | 538.55 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.62 | 538.55 | +0.00 | *back foot punch four facing up* |
| `session_2026-08-21_12-50-53` | 562.73 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.46 | 562.74 | +0.00 | *glide good* |
| `session_2026-08-21_12-50-53` | 587.89 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.35 | 587.89 | +0.00 | *cut shot okay facing up* |
| `session_2026-08-21_12-50-53` | 604.39 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.73 | 604.39 | +0.00 | *back foot punch miss* |
| `session_2026-08-21_12-50-53` | 609.36 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 604.39 | -4.97 | *facing up back foot punch okay* |
| `session_2026-08-21_12-50-53` | 626.70 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.63 | 626.70 | +0.00 | *back foot punch good* |
| `session_2026-08-21_12-50-53` | 640.80 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 647.85 | +7.05 | *facing up back foot punch okay* |
| `session_2026-08-21_12-50-53` | 647.85 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.67 | 647.85 | +0.00 | *glide pull* |
| `session_2026-08-21_12-50-53` | 687.22 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 679.57 | -7.65 | *glide good facing up* |
| `session_2026-08-21_12-50-53` | 695.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.40 | 695.30 | +0.00 | *back foot punch four facing up* |
| `session_2026-08-21_12-50-53` | 704.71 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 711.80 | +7.09 | *glide okay* |
| `session_2026-08-21_12-50-53` | 751.15 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.57 | 751.15 | +0.00 | *glide okay* |
| `session_2026-08-21_12-50-53` | 770.32 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.71 | 770.32 | +0.00 | *back foot punch edge facing up* |
| `session_2026-08-21_12-50-53` | 1037.31 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.45 | 1037.31 | +0.00 | *guide four facing up* |
| `session_2026-08-21_12-50-53` | 1042.68 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.50 | 1042.68 | +0.00 | *back foot punch good* |
| `session_2026-08-21_12-50-53` | 1125.47 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.63 | 1125.47 | +0.00 | *back foot punch good* |
| `session_2026-08-21_12-50-53` | 1160.62 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1151.71 | -8.91 | *guide good* |
| `session_2026-08-21_12-50-53` | 1162.70 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1151.71 | -10.98 | *facing up guide good* |
| `session_2026-08-21_12-50-53` | 1212.21 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.61 | 1212.21 | +0.00 | *back foot punch good* |
| `session_2026-08-21_12-50-53` | 1236.81 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1239.17 | +2.36 | *guide four* |
| `session_2026-09-08_12-52-30` | 86.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 93.58 | +7.23 | *back foot defense okay* |
| `session_2026-09-08_12-52-30` | 119.46 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.48 | 119.46 | +0.00 | *click shot or facing up* |
| `session_2026-09-08_12-52-30` | 124.67 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.88 | 124.67 | +0.00 | *glide okay facing up* |
| `session_2026-09-08_12-52-30` | 142.71 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.90 | 142.71 | +0.00 | *glide okay* |
| `session_2026-09-08_12-52-30` | 209.12 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 207.59 | -1.52 | *facing up cut shot okay* |
| `session_2026-09-08_12-52-30` | 254.51 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.66 | 254.51 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 269.40 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 260.92 | -8.48 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 576.33 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.64 | 576.33 | +0.00 | *back foot punch good facing up* |
| `session_2026-09-08_12-52-30` | 707.62 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 718.52 | +10.90 | *glide good facing* |
| `session_2026-09-08_12-52-30` | 805.18 | **PULL/HOOK/SLOG** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.35 | 805.18 | +0.00 | *push up good facing up* |
| `session_2026-09-08_12-52-30` | 815.13 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 822.57 | +7.44 | *push up facing up* |
| `session_2026-09-08_12-52-30` | 1204.95 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1203.14 | -1.80 | *glide miss* |
| `session_2026-09-08_12-52-30` | 1217.89 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.70 | 1217.89 | +0.00 | *back foot punch good* |
| `session_2026-09-08_12-52-30` | 1227.88 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1230.17 | +2.30 | *squad good facing up back foot punch good* |
| `session_2026-09-08_12-52-30` | 1259.47 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.75 | 1259.48 | +0.00 | *back foot punch good facing up glide edge facing* |
| `session_2026-09-08_12-52-30` | 1289.69 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1280.66 | -9.03 | *wide miss* |
| `session_2026-09-08_12-52-30` | 1345.95 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.76 | 1345.95 | +0.00 | *back foot punch good* |
| `session_2026-09-17_12-48-47` | 118.16 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 126.31 | +8.15 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 135.02 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +8.66 | *forward defense good* |
| `session_2026-09-17_12-48-47` | 138.93 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.68 | +4.75 | *straight drive edge* |
| `session_2026-09-17_12-48-47` | 177.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.49 | 177.87 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 254.51 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.32 | 254.51 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 570.87 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.40 | 570.88 | +0.00 | *on drive good* |
| `session_2026-09-17_12-48-47` | 677.45 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 680.90 | +3.45 | *facing up switch shot okay* |
| `session_2026-09-17_12-48-47` | 752.91 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 754.72 | +1.81 | *facing up good shot okay in the ground* |
| `session_2026-09-17_12-48-47` | 1005.67 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1008.22 | +2.54 | *facing up flick shot okay* |
| `session_2026-09-17_12-48-47` | 1111.53 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.28 | 1111.53 | +0.00 | *flick shot good* |
| `session_2026-09-17_12-48-47` | 1129.36 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.30 | 1129.36 | +0.00 | *push shot miss* |
| `session_2026-09-17_12-48-47` | 1153.15 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1146.77 | -6.39 | *glance miss* |
| `session_2026-09-17_12-48-47` | 1196.78 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.46 | 1196.78 | +0.00 | *flick shot good* |
| `session_2026-10-05_12-53-51` | 103.26 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 101.02 | -2.24 | *facing up back foot punch okay* |
| `session_2026-10-05_12-53-51` | 141.66 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 143.22 | +1.57 | *facing up cover drive okay* |
| `session_2026-10-05_12-53-51` | 207.21 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.77 | 206.97 | -0.25 | *glide good* |
| `session_2026-10-05_12-53-51` | 208.35 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.77 | 206.97 | -1.38 | *facing up glide good* |
| `session_2026-10-05_12-53-51` | 215.29 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 212.86 | -2.43 | *glide good* |
| `session_2026-10-05_12-53-51` | 232.95 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.44 | 232.95 | +0.00 | *glide four* |
| `session_2026-10-05_12-53-51` | 584.77 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 592.53 | +7.76 | *push shot* |
| `session_2026-10-05_12-53-51` | 615.09 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.63 | 615.09 | +0.00 | *facing up back foot defense okay* |
| `session_2026-10-05_12-53-51` | 738.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 745.74 | +6.80 | *facing up glide good* |
| `session_2026-10-05_12-53-51` | 1146.93 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1139.26 | -7.68 | *glide good* |
| `session_2026-10-05_12-53-51` | 1162.63 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1155.62 | -7.01 | *glide okay* |
| `session_2026-10-09_12-41-17` | 175.54 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.77 | 175.55 | +0.00 | *back foot defense or* |
| `session_2026-10-09_12-41-17` | 256.66 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.92 | 256.66 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 620.65 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.60 | 620.65 | +0.00 | *back foot punch good* |
| `session_2026-10-09_12-41-17` | 674.49 | **DRIVE/DEFENCE** | DEFLECTION/GUIDE | `SUBCLASS_CONFUSION` | 0.33 | 674.49 | +0.00 | *back foot punch edge* |
| `session_2026-10-09_12-41-17` | 688.03 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.68 | 688.04 | +0.00 | *glide okay facing it* |
| `session_2026-10-09_12-41-17` | 696.30 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.57 | 696.30 | +0.00 | *crackle punch okay facing it* |
| `session_2026-10-09_12-41-17` | 704.35 | **DEFLECTION/GUIDE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.31 | 704.35 | +0.00 | *glide edge* |
| `session_2026-10-09_12-41-17` | 1097.32 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.88 | 1097.32 | +0.00 | *back foot defense pull* |
| `session_2026-10-09_12-41-17` | 1102.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1097.32 | -4.99 | *facing clive okay* |
| `session_2026-10-09_12-41-17` | 1152.49 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1144.86 | -7.64 | *guide miss* |

