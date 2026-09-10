# 31-Channel Dual-Hand Relational TCN Experiment Scorecard Report

**Experiment**: 31-Channel TCN (28 Baseline Channels + 3 Frame-Independent Scalar Relational Channels: `rel_torque_ratio`, `rel_force_ratio`, `rel_diff_energy`)  
**Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN, `in_ch=31`)  
**Designated Holdout / Validation Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Training Sessions Count**: 63 physical sessions  
**Total Dataset Duration**: 1178.4 minutes (19.6 hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch 8 (Best Macro-F1: 0.6522, Candidate Acc: 67.48%, Val Loss: 1.0956, Stopped at Epoch 26)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/polar_relational_experiment_2026-09-04_17-21-04.log`  
**Date**: 2026-09-04 19:09

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (4 Sessions)** | **206** | **241** | **87.38%** (180/206) | **74.69%** (180/241) | **80.54%** |
| **Training Set Micro Average (63 Sessions)** | **3580** | **3513** | **80.25%** (2873/3580) | **81.78%** (2873/3513) | **81.01%** |
| 🏆 **Full Dataset Micro Average (All 67 Sessions)** | **3786** | **3754** | 🏆 **80.64%** (3053/3786) | 🏆 **81.33%** (3053/3754) | 🏆 **80.98%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (4 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 57 | 49 | 86.0% | 32 | **65.3%** | **56.1%** |
| **DRIVE/DEFENCE** | 30 | 27 | 90.0% | 17 | **63.0%** | **56.7%** |
| **GLANCE/FLICK** | 27 | 22 | 81.5% | 14 | **63.6%** | **51.9%** |
| **CUT/PUNCH** | 13 | 11 | 84.6% | 10 | **90.9%** | **76.9%** |
| **DEFLECTION/GUIDE** | 28 | 21 | 75.0% | 21 | **100.0%** | **75.0%** |
| **POWER DRIVE** | 20 | 20 | 100.0% | 5 | **25.0%** | **25.0%** |
| **SWEEP** | 31 | 30 | 96.8% | 30 | **100.0%** | **96.8%** |
| **OVERALL TOTAL** | **206** | **180** | **87.4%** | **129** | 🏆 **71.7%** | 🏆 **62.6%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (63 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 994 | 787 | 79.2% | 700 | **88.9%** | **70.4%** |
| **DRIVE/DEFENCE** | 914 | 731 | 80.0% | 638 | **87.3%** | **69.8%** |
| **GLANCE/FLICK** | 612 | 485 | 79.2% | 439 | **90.5%** | **71.7%** |
| **CUT/PUNCH** | 372 | 327 | 87.9% | 315 | **96.3%** | **84.7%** |
| **DEFLECTION/GUIDE** | 220 | 172 | 78.2% | 167 | **97.1%** | **75.9%** |
| **POWER DRIVE** | 256 | 190 | 74.2% | 186 | **97.9%** | **72.7%** |
| **SWEEP** | 212 | 181 | 85.4% | 172 | **95.0%** | **81.1%** |
| **OVERALL TOTAL** | **3580** | **2873** | **80.3%** | **2617** | 🏆 **91.1%** | 🏆 **73.1%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 67 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1051 | 836 | 79.5% | 732 | **87.6%** | **69.6%** |
| **DRIVE/DEFENCE** | 944 | 758 | 80.3% | 655 | **86.4%** | **69.4%** |
| **GLANCE/FLICK** | 639 | 507 | 79.3% | 453 | **89.3%** | **70.9%** |
| **CUT/PUNCH** | 385 | 338 | 87.8% | 325 | **96.2%** | **84.4%** |
| **DEFLECTION/GUIDE** | 248 | 193 | 77.8% | 188 | **97.4%** | **75.8%** |
| **POWER DRIVE** | 276 | 210 | 76.1% | 191 | **91.0%** | **69.2%** |
| **SWEEP** | 243 | 211 | 86.8% | 202 | **95.7%** | **83.1%** |
| **OVERALL TOTAL** | **3786** | **3053** | **80.6%** | **2746** | 🏆 **89.9%** | 🏆 **72.5%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.5 | 94 | 15 | 9.6% | 60.0% | 16.5%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 5 | 100.0% | 80.0% | 88.9%
| `session_2026-05-31_14-12-10` | Training | 13.0 | 41 | 10 | 9.8% | 40.0% | 15.7%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 62 | 91.8% | 90.3% | 91.1%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 92.9% | 92.9% | 92.9%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 39 | 62.7% | 82.1% | 71.1%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 37 | 55.6% | 67.6% | 61.0%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 93.1% | 91.5% | 92.3%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 92.2% | 88.7% | 90.4%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 70 | 70 | 94.3% | 94.3% | 94.3%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 88.7% | 91.7% | 90.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 88.4% | 95.3% | 91.7%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-19_12-25-55` | Training | 16.7 | 56 | 60 | 98.2% | 91.7% | 94.8%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 69 | 96.4% | 76.8% | 85.5%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 61 | 94.7% | 88.5% | 91.5%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 55 | 61.4% | 63.6% | 62.5%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 69 | 93.8% | 88.4% | 91.0%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 62 | 93.2% | 88.7% | 90.9%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 56 | 96.2% | 89.3% | 92.6%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 66 | 62.1% | 54.5% | 58.1%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 59 | 60 | 98.3% | 96.7% | 97.5%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 63 | 98.0% | 76.2% | 85.7%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 58 | 91.2% | 89.7% | 90.4%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 55 | 89.7% | 94.5% | 92.0%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 61 | 92.3% | 78.7% | 85.0%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 68 | 98.3% | 83.8% | 90.5%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 63 | 100.0% | 81.0% | 89.5%
| `session_2026-07-11_12-51-39` | Training | 17.1 | 55 | 16 | 10.9% | 37.5% | 16.9%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 4 | 3.6% | 50.0% | 6.7%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 74 | 90.0% | 73.0% | 80.6%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 7 | 10.5% | 85.7% | 18.7%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 60 | 43.9% | 48.3% | 46.0%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT | 15.3 | 37 | 51 | 94.6% | 68.6% | 79.5%
| `session_2026-07-21_12-43-37` | 🌟 HOLDOUT | 18.3 | 56 | 63 | 73.2% | 65.1% | 68.9%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 96.5% | 91.7% | 94.0%
| `session_2026-07-24_12-52-29` | 🌟 HOLDOUT | 17.9 | 52 | 58 | 84.6% | 75.9% | 80.0%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT | 20.6 | 61 | 69 | 98.4% | 87.0% | 92.3%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 62 | 98.2% | 87.1% | 92.3%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 62 | 90.7% | 62.9% | 74.3%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 89.1% | 76.6% | 82.4%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 85.2% | 79.3% | 82.1%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 52 | 93.9% | 88.5% | 91.1%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 62 | 77.0% | 75.8% | 76.4%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 58 | 61 | 82.8% | 78.7% | 80.7%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 21.0% | 21.7% | 21.3%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 85 | 90.9% | 82.4% | 86.4%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 65 | 91.9% | 87.7% | 89.8%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 65 | 90.2% | 84.6% | 87.3%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 69 | 84.9% | 89.9% | 87.3%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 51 | 100.0% | 98.0% | 99.0%
| `session_2026-08-17_12-51-22` | Training | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 70 | 95.5% | 90.0% | 92.6%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 71 | 91.3% | 88.7% | 90.0%
| `session_2026-08-22_14-25-31` | Training | 12.0 | 51 | 58 | 90.2% | 79.3% | 84.4%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 68 | 94.0% | 92.6% | 93.3%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 92.3% | 89.6% | 90.9%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 66 | 20.7% | 18.2% | 19.4%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 63 | 89.3% | 79.4% | 84.0%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 64 | 63 | 89.1% | 90.5% | 89.8%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 66 | 90.9% | 90.9% | 90.9%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 64 | 81.5% | 68.8% | 74.6%
| `session_2026-09-04_12-47-22` | Training | 19.4 | 65 | 67 | 89.2% | 86.6% | 87.9%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **NOT_DETECTED (MISSING_CANDIDATE)** | **23** | PULL/HOOK/SLOG (8), DEFLECTION/GUIDE (6), GLANCE/FLICK (5) |
| **VERTICAL_BAT_CONFUSION** | **17** | PULL/HOOK/SLOG (16), CUT/PUNCH (1) |
| **CROSS_BAT_CONFUSION (Macro Gate)** | **11** | POWER DRIVE (11) |
| **SWEEP_CONFUSION** | **9** | POWER DRIVE (4), GLANCE/FLICK (2), DRIVE/DEFENCE (1) |
| **CROSS_BAT_CONFUSION** | **8** | DRIVE/DEFENCE (5), GLANCE/FLICK (3) |
| **SUBCLASS_CONFUSION** | **7** | DRIVE/DEFENCE (4), GLANCE/FLICK (3) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-07-20_12-42-16` | 106.04 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.86 | 106.04 | +0.00 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 375.43 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 380.12 | +4.69 | *sweep shot miss facing up* |
| `session_2026-07-20_12-42-16` | 429.95 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.85 | 429.95 | +0.00 | *flip shot edge* |
| `session_2026-07-20_12-42-16` | 459.47 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.39 | 459.47 | +0.00 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 557.88 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.88 | 557.88 | +0.00 | *straight shot good end of round* |
| `session_2026-07-20_12-42-16` | 749.59 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 753.46 | +3.87 | *slip shot okay facing up* |
| `session_2026-07-20_12-42-16` | 880.19 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.64 | 880.20 | +0.00 | *quick shot edge* |
| `session_2026-07-21_12-43-37` | 16.24 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.36 | +59.12 | *alright just getting myself organized* |
| `session_2026-07-21_12-43-37` | 19.70 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.36 | +55.66 | *cover me if my watchy* |
| `session_2026-07-21_12-43-37` | 164.58 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.66 | 164.58 | +0.00 | *on drive okay* |
| `session_2026-07-21_12-43-37` | 173.32 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.77 | 173.32 | +0.00 | *oh back defense okay* |
| `session_2026-07-21_12-43-37` | 199.60 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.77 | 199.60 | +0.00 | *foot shot good facing up* |
| `session_2026-07-21_12-43-37` | 207.58 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.71 | 207.58 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 234.02 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.70 | 234.02 | +0.00 | *on drive okay facing up* |
| `session_2026-07-21_12-43-37` | 517.26 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.71 | 517.26 | +0.00 | *foot shot okay* |
| `session_2026-07-21_12-43-37` | 524.97 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.67 | 524.98 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 572.76 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.66 | 572.76 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 581.22 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.53 | 579.83 | -1.39 | *foot shot good facing up* |
| `session_2026-07-21_12-43-37` | 617.47 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.79 | 616.70 | -0.77 | *hook shot good facing up* |
| `session_2026-07-21_12-43-37` | 641.81 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 634.70 | -7.11 | *flick shot okay facing up* |
| `session_2026-07-21_12-43-37` | 662.05 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 659.19 | -2.86 | *oh for shot edge* |
| `session_2026-07-21_12-43-37` | 921.52 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 917.37 | -4.15 | *on drive okay* |
| `session_2026-07-21_12-43-37` | 933.45 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.59 | 933.45 | +0.00 | *on drive good* |
| `session_2026-07-21_12-43-37` | 955.27 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.78 | 955.27 | +0.00 | *flip shot good* |
| `session_2026-07-21_12-43-37` | 967.40 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 965.01 | -2.40 | *switch up for* |
| `session_2026-07-21_12-43-37` | 978.28 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.72 | 978.28 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 983.21 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.77 | 983.22 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 996.05 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 992.68 | -3.37 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 1006.22 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1003.90 | -2.33 | *oh switch up edge facing* |
| `session_2026-07-21_12-43-37` | 1012.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1010.81 | -1.54 | *up push up good* |
| `session_2026-07-21_12-43-37` | 1021.57 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1018.71 | -2.86 | *pull shot okay facing up* |
| `session_2026-07-21_12-43-37` | 1036.44 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1034.53 | -1.91 | *pull shot good* |
| `session_2026-07-21_12-43-37` | 1046.11 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1043.83 | -2.27 | *push up good* |
| `session_2026-07-21_12-43-37` | 1058.52 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1053.66 | -4.86 | *pull shot good* |
| `session_2026-07-21_12-43-37` | 1079.79 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.76 | 1079.79 | +0.00 | *flick shot good facing up* |
| `session_2026-07-21_12-43-37` | 1087.13 | **DRIVE/DEFENCE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.91 | 1087.13 | +0.00 | *on drive okay* |
| `session_2026-07-21_12-43-37` | 1092.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1087.13 | -5.21 | *pull shot good end of round end of session* |
| `session_2026-07-24_12-52-29` | 91.14 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.76 | 91.14 | +0.00 | *cut shot okay facing up* |
| `session_2026-07-24_12-52-29` | 132.76 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.72 | 132.76 | +0.00 | *back foot punch four* |
| `session_2026-07-24_12-52-29` | 209.06 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 201.92 | -7.14 | *guide good* |
| `session_2026-07-24_12-52-29` | 438.09 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 435.15 | -2.94 | *guide or facing up* |
| `session_2026-07-24_12-52-29` | 445.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 442.28 | -3.03 | *guide good facing up* |
| `session_2026-07-24_12-52-29` | 521.41 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.78 | 520.20 | -1.21 | *back foot punch okay facing up* |
| `session_2026-07-24_12-52-29` | 522.74 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 520.20 | -2.54 | *guide or facing up* |
| `session_2026-07-24_12-52-29` | 554.02 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 551.65 | -2.37 | *guide good facing up* |
| `session_2026-07-24_12-52-29` | 566.91 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.94 | 566.91 | +0.00 | *back foot punch okay* |
| `session_2026-07-24_12-52-29` | 579.44 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 577.07 | -2.37 | *cut shot good facing up* |
| `session_2026-07-24_12-52-29` | 584.08 | **CUT/PUNCH** | SWEEP | `SWEEP_CONFUSION` | 0.52 | 584.08 | +0.00 | *touch shot good facing up* |
| `session_2026-07-24_12-52-29` | 935.85 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.78 | 935.20 | -0.64 | *back foot punch okay facing up* |
| `session_2026-07-25_15-16-32` | 82.82 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.85 | 82.82 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 109.58 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.45 | 109.58 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 119.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.48 | 119.11 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 186.74 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.84 | 186.74 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 203.06 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.75 | 203.06 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 226.76 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.80 | 226.76 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 236.32 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.86 | 236.32 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 711.04 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.44 | 711.04 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 719.08 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.54 | 719.08 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 721.81 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 719.08 | -2.73 | *slog good facing up* |
| `session_2026-07-25_15-16-32` | 735.36 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.79 | 735.37 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 751.12 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.66 | 751.12 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 761.25 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.84 | 761.26 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 768.77 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.52 | 768.77 | +0.00 | *power drive good* |
| `session_2026-07-25_15-16-32` | 782.31 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.89 | 782.31 | +0.00 | *power drive pull* |
| `session_2026-07-25_15-16-32` | 819.15 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.64 | 819.15 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 835.20 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.47 | 835.20 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 857.54 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.56 | 857.54 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1043.07 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.59 | 1043.07 | +0.00 | *power drive okay facing up* |
| `session_2026-07-25_15-16-32` | 1052.24 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.87 | 1052.24 | +0.00 | *flick shot okay* |
| `session_2026-07-25_15-16-32` | 1092.55 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.81 | 1092.55 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1101.77 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.80 | 1101.77 | +0.00 | *flick shot good* |
| `session_2026-07-25_15-16-32` | 1109.60 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.88 | 1109.60 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1137.55 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.50 | 1137.56 | +0.00 | *power drive terrible four facing up* |
| `session_2026-07-25_15-16-32` | 1179.12 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.94 | 1179.12 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1201.60 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.46 | 1201.60 | +0.00 | *power drive terrible facing up* |

