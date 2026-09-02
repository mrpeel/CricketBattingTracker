# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN)  
**Training Design**: Unified Continuous Discriminative Training (Backbone L1-7: 3e-5, L8-10+Heads: 5e-4, 3-Epoch Warmup, 32-Epoch CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.0, 1.0, 1.0], Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Training Sessions Count**: 62 physical sessions  
**Total Dataset Duration**: 1159.0 minutes (19.3 hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch 25 (Reloaded Checkpoint) (Best Macro-F1: 0.6356, Candidate Acc: 63.59%, Val Loss: 1.1914, Stopped at Epoch 35)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-09-03_07-44-37.log`  
**Date**: 2026-09-03 07:45

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (4 Sessions)** | **206** | **241** | **83.01%** (171/206) | **70.95%** (171/241) | **76.51%** |
| **Training Set Micro Average (62 Sessions)** | **3515** | **3447** | **78.83%** (2771/3515) | **80.39%** (2771/3447) | **79.60%** |
| 🏆 **Full Dataset Micro Average (All 66 Sessions)** | **3721** | **3688** | 🏆 **79.06%** (2942/3721) | 🏆 **79.77%** (2942/3688) | 🏆 **79.42%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (4 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 57 | 49 | 86.0% | 22 | **44.9%** | **38.6%** |
| **DRIVE/DEFENCE** | 30 | 24 | 80.0% | 18 | **75.0%** | **60.0%** |
| **GLANCE/FLICK** | 27 | 22 | 81.5% | 14 | **63.6%** | **51.9%** |
| **CUT/PUNCH** | 13 | 11 | 84.6% | 8 | **72.7%** | **61.5%** |
| **DEFLECTION/GUIDE** | 28 | 15 | 53.6% | 14 | **93.3%** | **50.0%** |
| **POWER DRIVE** | 20 | 20 | 100.0% | 10 | **50.0%** | **50.0%** |
| **SWEEP** | 31 | 30 | 96.8% | 27 | **90.0%** | **87.1%** |
| **OVERALL TOTAL** | **206** | **171** | **83.0%** | **113** | 🏆 **66.1%** | 🏆 **54.9%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (62 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 951 | 739 | 77.7% | 651 | **88.1%** | **68.5%** |
| **DRIVE/DEFENCE** | 914 | 729 | 79.8% | 678 | **93.0%** | **74.2%** |
| **GLANCE/FLICK** | 590 | 454 | 76.9% | 404 | **89.0%** | **68.5%** |
| **CUT/PUNCH** | 372 | 324 | 87.1% | 290 | **89.5%** | **78.0%** |
| **DEFLECTION/GUIDE** | 220 | 173 | 78.6% | 170 | **98.3%** | **77.3%** |
| **POWER DRIVE** | 256 | 179 | 69.9% | 171 | **95.5%** | **66.8%** |
| **SWEEP** | 212 | 173 | 81.6% | 159 | **91.9%** | **75.0%** |
| **OVERALL TOTAL** | **3515** | **2771** | **78.8%** | **2523** | 🏆 **91.1%** | 🏆 **71.8%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 66 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1008 | 788 | 78.2% | 673 | **85.4%** | **66.8%** |
| **DRIVE/DEFENCE** | 944 | 753 | 79.8% | 696 | **92.4%** | **73.7%** |
| **GLANCE/FLICK** | 617 | 476 | 77.1% | 418 | **87.8%** | **67.7%** |
| **CUT/PUNCH** | 385 | 335 | 87.0% | 298 | **89.0%** | **77.4%** |
| **DEFLECTION/GUIDE** | 248 | 188 | 75.8% | 184 | **97.9%** | **74.2%** |
| **POWER DRIVE** | 276 | 199 | 72.1% | 181 | **91.0%** | **65.6%** |
| **SWEEP** | 243 | 203 | 83.5% | 186 | **91.6%** | **76.5%** |
| **OVERALL TOTAL** | **3721** | **2942** | **79.1%** | **2636** | 🏆 **89.6%** | 🏆 **70.8%** |

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
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 74 | 88.3% | 71.6% | 79.1%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 7 | 10.5% | 85.7% | 18.7%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 60 | 43.9% | 48.3% | 46.0%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT | 15.3 | 37 | 51 | 94.6% | 68.6% | 79.5%
| `session_2026-07-21_12-43-37` | 🌟 HOLDOUT | 18.3 | 56 | 63 | 73.2% | 65.1% | 68.9%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 96.5% | 91.7% | 94.0%
| `session_2026-07-24_12-52-29` | 🌟 HOLDOUT | 17.9 | 52 | 58 | 67.3% | 60.3% | 63.6%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT | 20.6 | 61 | 69 | 98.4% | 87.0% | 92.3%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 62 | 89.1% | 79.0% | 83.8%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 86.8% | 79.3% | 82.9%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 62 | 83.7% | 58.1% | 68.6%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 72.7% | 62.5% | 67.2%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 85.2% | 79.3% | 82.1%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 52 | 77.6% | 73.1% | 75.2%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 62 | 70.5% | 69.4% | 69.9%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 58 | 61 | 72.4% | 68.9% | 70.6%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 24.2% | 25.0% | 24.6%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 85 | 87.0% | 78.8% | 82.7%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 65 | 88.7% | 84.6% | 86.6%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 65 | 90.2% | 84.6% | 87.3%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 69 | 84.9% | 89.9% | 87.3%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 51 | 98.0% | 96.1% | 97.0%
| `session_2026-08-17_12-51-22` | Training | 19.2 | 64 | 65 | 90.6% | 89.2% | 89.9%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 70 | 95.5% | 90.0% | 92.6%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 71 | 91.3% | 88.7% | 90.0%
| `session_2026-08-22_14-25-31` | Training | 12.0 | 51 | 59 | 90.2% | 78.0% | 83.6%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 68 | 94.0% | 92.6% | 93.3%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 92.3% | 89.6% | 90.9%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 66 | 22.4% | 19.7% | 21.0%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 63 | 89.3% | 79.4% | 84.0%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 64 | 63 | 89.1% | 90.5% | 89.8%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 66 | 90.9% | 90.9% | 90.9%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 64 | 81.5% | 68.8% | 74.6%

---

## 🔍 Holdout Misclassification & Detection Error Analysis

### 📊 Holdout Error Categories Summary

| Error Category | Count | Primary Impacted Shots |
|---|:---:|---|
| **NOT_DETECTED (MISSING_CANDIDATE)** | **34** | DEFLECTION/GUIDE (13), PULL/HOOK/SLOG (8), GLANCE/FLICK (5) |
| **VERTICAL_BAT_CONFUSION** | **29** | PULL/HOOK/SLOG (26), CUT/PUNCH (3) |
| **SWEEP_CONFUSION** | **10** | SWEEP (3), GLANCE/FLICK (3), POWER DRIVE (2) |
| **CROSS_BAT_CONFUSION (Macro Gate)** | **8** | POWER DRIVE (8) |
| **SUBCLASS_CONFUSION** | **7** | GLANCE/FLICK (4), DRIVE/DEFENCE (2), DEFLECTION/GUIDE (1) |
| **CROSS_BAT_CONFUSION** | **4** | DRIVE/DEFENCE (3), GLANCE/FLICK (1) |


### 📋 Itemized Holdout Error Audit

| Session | Impact Time (s) | Ground Truth Class | Status / Predicted | Error Category | Prob | Cand Time (s) | Delta (s) | Narrated Speech Text |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| `session_2026-07-20_12-42-16` | 62.99 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.87 | 62.99 | +0.00 | *sweep shot okay* |
| `session_2026-07-20_12-42-16` | 78.12 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.77 | 78.12 | +0.00 | *sweep shot miss* |
| `session_2026-07-20_12-42-16` | 106.04 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.97 | 106.04 | +0.00 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 375.43 | **SWEEP** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 380.12 | +4.69 | *sweep shot miss facing up* |
| `session_2026-07-20_12-42-16` | 429.95 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.92 | 429.95 | +0.00 | *flip shot edge* |
| `session_2026-07-20_12-42-16` | 459.47 | **GLANCE/FLICK** | SWEEP | `SWEEP_CONFUSION` | 0.96 | 459.47 | +0.00 | *flip shot okay* |
| `session_2026-07-20_12-42-16` | 513.73 | **SWEEP** | PULL/HOOK/SLOG | `SWEEP_CONFUSION` | 0.79 | 513.73 | +0.00 | *swipe shot okay* |
| `session_2026-07-20_12-42-16` | 557.88 | **DRIVE/DEFENCE** | SWEEP | `SWEEP_CONFUSION` | 0.92 | 557.88 | +0.00 | *straight shot good end of round* |
| `session_2026-07-20_12-42-16` | 749.59 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 753.46 | +3.87 | *slip shot okay facing up* |
| `session_2026-07-20_12-42-16` | 880.19 | **GLANCE/FLICK** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.90 | 880.20 | +0.00 | *quick shot edge* |
| `session_2026-07-21_12-43-37` | 16.24 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.36 | +59.12 | *alright just getting myself organized* |
| `session_2026-07-21_12-43-37` | 19.70 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 75.36 | +55.66 | *cover me if my watchy* |
| `session_2026-07-21_12-43-37` | 173.32 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.87 | 173.32 | +0.00 | *oh back defense okay* |
| `session_2026-07-21_12-43-37` | 199.60 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.85 | 199.60 | +0.00 | *foot shot good facing up* |
| `session_2026-07-21_12-43-37` | 207.58 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.87 | 207.58 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 517.26 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.85 | 517.26 | +0.00 | *foot shot okay* |
| `session_2026-07-21_12-43-37` | 524.97 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.88 | 524.98 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 572.76 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.86 | 572.76 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 581.22 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.82 | 579.83 | -1.39 | *foot shot good facing up* |
| `session_2026-07-21_12-43-37` | 617.47 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.88 | 616.70 | -0.77 | *hook shot good facing up* |
| `session_2026-07-21_12-43-37` | 641.81 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 634.70 | -7.11 | *flick shot okay facing up* |
| `session_2026-07-21_12-43-37` | 662.05 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 659.19 | -2.86 | *oh for shot edge* |
| `session_2026-07-21_12-43-37` | 921.52 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 917.37 | -4.15 | *on drive okay* |
| `session_2026-07-21_12-43-37` | 933.45 | **DRIVE/DEFENCE** | GLANCE/FLICK | `SUBCLASS_CONFUSION` | 0.72 | 933.45 | +0.00 | *on drive good* |
| `session_2026-07-21_12-43-37` | 955.27 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.86 | 955.27 | +0.00 | *flip shot good* |
| `session_2026-07-21_12-43-37` | 967.40 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 965.01 | -2.40 | *switch up for* |
| `session_2026-07-21_12-43-37` | 978.28 | **PULL/HOOK/SLOG** | GLANCE/FLICK | `VERTICAL_BAT_CONFUSION` | 0.89 | 978.28 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 983.21 | **PULL/HOOK/SLOG** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.88 | 983.22 | +0.00 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 996.05 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 992.68 | -3.37 | *foot shot good* |
| `session_2026-07-21_12-43-37` | 1006.22 | **GLANCE/FLICK** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1003.90 | -2.33 | *oh switch up edge facing* |
| `session_2026-07-21_12-43-37` | 1012.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1010.81 | -1.54 | *up push up good* |
| `session_2026-07-21_12-43-37` | 1021.57 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1018.71 | -2.86 | *pull shot okay facing up* |
| `session_2026-07-21_12-43-37` | 1036.44 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1034.53 | -1.91 | *pull shot good* |
| `session_2026-07-21_12-43-37` | 1046.11 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1043.83 | -2.27 | *push up good* |
| `session_2026-07-21_12-43-37` | 1058.52 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1053.66 | -4.86 | *pull shot good* |
| `session_2026-07-21_12-43-37` | 1079.79 | **GLANCE/FLICK** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.85 | 1079.79 | +0.00 | *flick shot good facing up* |
| `session_2026-07-21_12-43-37` | 1087.13 | **DRIVE/DEFENCE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION` | 0.90 | 1087.13 | +0.00 | *on drive okay* |
| `session_2026-07-21_12-43-37` | 1092.35 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1087.13 | -5.21 | *pull shot good end of round end of session* |
| `session_2026-07-24_12-52-29` | 89.25 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 91.14 | +1.89 | *guide or facing up* |
| `session_2026-07-24_12-52-29` | 91.14 | **CUT/PUNCH** | DEFLECTION/GUIDE | `VERTICAL_BAT_CONFUSION` | 0.81 | 91.14 | +0.00 | *cut shot okay facing up* |
| `session_2026-07-24_12-52-29` | 103.43 | **DEFLECTION/GUIDE** | DRIVE/DEFENCE | `SUBCLASS_CONFUSION` | 0.49 | 103.43 | +0.00 | *guide okay* |
| `session_2026-07-24_12-52-29` | 152.92 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.87 | 152.92 | +0.00 | *cut shot okay* |
| `session_2026-07-24_12-52-29` | 162.85 | **CUT/PUNCH** | DRIVE/DEFENCE | `VERTICAL_BAT_CONFUSION` | 0.89 | 162.85 | +0.00 | *cut shot okay* |
| `session_2026-07-24_12-52-29` | 209.06 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 201.92 | -7.14 | *guide good* |
| `session_2026-07-24_12-52-29` | 438.09 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 435.15 | -2.94 | *guide or facing up* |
| `session_2026-07-24_12-52-29` | 445.31 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 442.28 | -3.03 | *guide good facing up* |
| `session_2026-07-24_12-52-29` | 474.82 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 476.79 | +1.97 | *cut shot four facing up guide good* |
| `session_2026-07-24_12-52-29` | 496.43 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 498.54 | +2.11 | *guide good facing up guide good* |
| `session_2026-07-24_12-52-29` | 508.73 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 510.90 | +2.17 | *guide okay facing up* |
| `session_2026-07-24_12-52-29` | 518.71 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.71 | 520.20 | +1.49 | *back foot punch okay facing up* |
| `session_2026-07-24_12-52-29` | 522.74 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 520.20 | -2.54 | *guide or facing up* |
| `session_2026-07-24_12-52-29` | 535.35 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 537.07 | +1.72 | *k foot punch okay facing up* |
| `session_2026-07-24_12-52-29` | 544.40 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 546.52 | +2.11 | *guide good facing up* |
| `session_2026-07-24_12-52-29` | 554.02 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 551.65 | -2.37 | *guide good facing up* |
| `session_2026-07-24_12-52-29` | 566.91 | **DRIVE/DEFENCE** | CUT/PUNCH | `CROSS_BAT_CONFUSION` | 0.88 | 566.91 | +0.00 | *back foot punch okay* |
| `session_2026-07-24_12-52-29` | 575.10 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 577.07 | +1.97 | *cover drive okay facing up* |
| `session_2026-07-24_12-52-29` | 579.44 | **CUT/PUNCH** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 577.07 | -2.37 | *cut shot good facing up* |
| `session_2026-07-24_12-52-29` | 899.30 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 901.60 | +2.29 | *glide good facing up* |
| `session_2026-07-24_12-52-29` | 933.15 | **DRIVE/DEFENCE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 935.20 | +2.05 | *back foot punch okay facing up* |
| `session_2026-07-24_12-52-29` | 1009.08 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1011.41 | +2.33 | *guide four facing up* |
| `session_2026-07-24_12-52-29` | 1018.50 | **DEFLECTION/GUIDE** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 1020.86 | +2.36 | *guide good facing up* |
| `session_2026-07-25_15-16-32` | 82.82 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.94 | 82.82 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 109.58 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.92 | 109.58 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 119.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.94 | 119.11 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 142.49 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.87 | 142.49 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 150.11 | **PULL/HOOK/SLOG** | SWEEP | `SWEEP_CONFUSION` | 0.93 | 150.11 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 158.84 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.86 | 158.84 | +0.00 | *slog edge* |
| `session_2026-07-25_15-16-32` | 178.15 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.63 | 178.15 | +0.00 | *slog four* |
| `session_2026-07-25_15-16-32` | 186.74 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.60 | 186.74 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 226.76 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.71 | 226.76 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 236.32 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.70 | 236.32 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 690.11 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.65 | 690.11 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 711.04 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.87 | 711.04 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 721.81 | **PULL/HOOK/SLOG** | ⚠️ NONE | `NOT_DETECTED (MISSING_CANDIDATE)` | 0.00 | 719.08 | -2.73 | *slog good facing up* |
| `session_2026-07-25_15-16-32` | 735.36 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.84 | 735.37 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 744.79 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.83 | 744.79 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 761.25 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.82 | 761.26 | +0.00 | *power drive 4* |
| `session_2026-07-25_15-16-32` | 782.31 | **POWER DRIVE** | SWEEP | `SWEEP_CONFUSION` | 0.96 | 782.31 | +0.00 | *power drive pull* |
| `session_2026-07-25_15-16-32` | 819.15 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.87 | 819.15 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 835.20 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.88 | 835.20 | +0.00 | *power drive okay* |
| `session_2026-07-25_15-16-32` | 844.40 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.85 | 844.40 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 857.54 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.63 | 857.54 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1052.24 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.78 | 1052.24 | +0.00 | *flick shot okay* |
| `session_2026-07-25_15-16-32` | 1061.78 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.78 | 1061.78 | +0.00 | *slog okay facing up* |
| `session_2026-07-25_15-16-32` | 1092.55 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.90 | 1092.55 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1101.77 | **GLANCE/FLICK** | POWER DRIVE | `SUBCLASS_CONFUSION` | 0.72 | 1101.77 | +0.00 | *flick shot good* |
| `session_2026-07-25_15-16-32` | 1109.60 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.67 | 1109.60 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1137.55 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.85 | 1137.56 | +0.00 | *power drive terrible four facing up* |
| `session_2026-07-25_15-16-32` | 1151.34 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.75 | 1151.34 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1162.31 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.83 | 1162.31 | +0.00 | *slog okay* |
| `session_2026-07-25_15-16-32` | 1179.12 | **PULL/HOOK/SLOG** | POWER DRIVE | `VERTICAL_BAT_CONFUSION` | 0.92 | 1179.12 | +0.00 | *slog good* |
| `session_2026-07-25_15-16-32` | 1201.60 | **POWER DRIVE** | PULL/HOOK/SLOG | `CROSS_BAT_CONFUSION (Macro Gate)` | 0.71 | 1201.60 | +0.00 | *power drive terrible facing up* |

