# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN)  
**Training Design**: Unified Continuous Discriminative Training (Backbone L1-7: 3e-5, L8-10+Heads: 5e-4, 3-Epoch Warmup, 32-Epoch CosineAnnealingLR to 1e-6, Head 2A Weight [1.0, 2.0, 1.0, 1.0], Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Training Sessions Count**: 62 physical sessions  
**Total Dataset Duration**: 1159.0 minutes (19.3 hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch 18 (Best Macro-F1: 0.6019, Candidate Acc: 60.68%, Val Loss: 1.2202, Stopped at Epoch 35)  
**Execution Log File**: `/Users/neilkloot/Code/CricketBattingTracker/pipelines/training_logs/master_retraining_2026-09-01_15-33-28.log`  
**Date**: 2026-09-01 16:50

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (4 Sessions)** | **206** | **241** | **63.59%** (131/206) | **54.36%** (131/241) | **58.61%** |
| **Training Set Micro Average (62 Sessions)** | **3515** | **3447** | **76.10%** (2675/3515) | **77.60%** (2675/3447) | **76.85%** |
| 🏆 **Full Dataset Micro Average (All 66 Sessions)** | **3721** | **3688** | 🏆 **75.41%** (2806/3721) | 🏆 **76.08%** (2806/3688) | 🏆 **75.75%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (4 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 57 | 32 | 56.1% | 21 | **65.6%** | **36.8%** |
| **DRIVE/DEFENCE** | 30 | 15 | 50.0% | 9 | **60.0%** | **30.0%** |
| **GLANCE/FLICK** | 27 | 9 | 33.3% | 3 | **33.3%** | **11.1%** |
| **CUT/PUNCH** | 13 | 12 | 92.3% | 8 | **66.7%** | **61.5%** |
| **DEFLECTION/GUIDE** | 28 | 26 | 92.9% | 24 | **92.3%** | **85.7%** |
| **POWER DRIVE** | 20 | 6 | 30.0% | 2 | **33.3%** | **10.0%** |
| **SWEEP** | 31 | 31 | 100.0% | 29 | **93.5%** | **93.5%** |
| **OVERALL TOTAL** | **206** | **131** | **63.6%** | **96** | 🏆 **73.3%** | 🏆 **46.6%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (62 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 951 | 688 | 72.3% | 623 | **90.6%** | **65.5%** |
| **DRIVE/DEFENCE** | 914 | 693 | 75.8% | 646 | **93.2%** | **70.7%** |
| **GLANCE/FLICK** | 590 | 420 | 71.2% | 364 | **86.7%** | **61.7%** |
| **CUT/PUNCH** | 372 | 323 | 86.8% | 290 | **89.8%** | **78.0%** |
| **DEFLECTION/GUIDE** | 220 | 175 | 79.5% | 171 | **97.7%** | **77.7%** |
| **POWER DRIVE** | 256 | 193 | 75.4% | 164 | **85.0%** | **64.1%** |
| **SWEEP** | 212 | 183 | 86.3% | 165 | **90.2%** | **77.8%** |
| **OVERALL TOTAL** | **3515** | **2675** | **76.1%** | **2423** | 🏆 **90.6%** | 🏆 **68.9%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 66 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 1008 | 720 | 71.4% | 644 | **89.4%** | **63.9%** |
| **DRIVE/DEFENCE** | 944 | 708 | 75.0% | 655 | **92.5%** | **69.4%** |
| **GLANCE/FLICK** | 617 | 429 | 69.5% | 367 | **85.5%** | **59.5%** |
| **CUT/PUNCH** | 385 | 335 | 87.0% | 298 | **89.0%** | **77.4%** |
| **DEFLECTION/GUIDE** | 248 | 201 | 81.0% | 195 | **97.0%** | **78.6%** |
| **POWER DRIVE** | 276 | 199 | 72.1% | 166 | **83.4%** | **60.1%** |
| **SWEEP** | 243 | 214 | 88.1% | 194 | **90.7%** | **79.8%** |
| **OVERALL TOTAL** | **3721** | **2806** | **75.4%** | **2519** | 🏆 **89.8%** | 🏆 **67.7%** |

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
| `session_2026-07-11_12-51-39` | Training | 17.1 | 55 | 16 | 5.5% | 18.8% | 8.5%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 4 | 3.6% | 50.0% | 6.7%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 74 | 38.3% | 31.1% | 34.3%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 7 | 3.5% | 28.6% | 6.2%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 60 | 37.9% | 41.7% | 39.7%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT | 15.3 | 37 | 51 | 100.0% | 72.5% | 84.1%
| `session_2026-07-21_12-43-37` | 🌟 HOLDOUT | 18.3 | 56 | 63 | 19.6% | 17.5% | 18.5%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 57.9% | 55.0% | 56.4%
| `session_2026-07-24_12-52-29` | 🌟 HOLDOUT | 17.9 | 52 | 58 | 96.2% | 86.2% | 90.9%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT | 20.6 | 61 | 69 | 54.1% | 47.8% | 50.8%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 62 | 98.2% | 87.1% | 92.3%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 62 | 97.7% | 67.7% | 80.0%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 65.5% | 56.2% | 60.5%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 70.4% | 65.5% | 67.9%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 52 | 100.0% | 94.2% | 97.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 62 | 88.5% | 87.1% | 87.8%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 58 | 61 | 84.5% | 80.3% | 82.4%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 21.0% | 21.7% | 21.3%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 85 | 93.5% | 84.7% | 88.9%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 65 | 90.3% | 86.2% | 88.2%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 65 | 82.0% | 76.9% | 79.4%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 69 | 79.5% | 84.1% | 81.7%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 51 | 98.0% | 96.1% | 97.0%
| `session_2026-08-17_12-51-22` | Training | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 70 | 53.0% | 50.0% | 51.5%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 71 | 88.4% | 85.9% | 87.1%
| `session_2026-08-22_14-25-31` | Training | 12.0 | 51 | 59 | 92.2% | 79.7% | 85.5%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 68 | 94.0% | 92.6% | 93.3%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 90.8% | 88.1% | 89.4%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 66 | 24.1% | 21.2% | 22.6%
| `session_2026-08-28_12-50-32` | Training | 19.2 | 56 | 63 | 87.5% | 77.8% | 82.4%
| `session_2026-08-30_11-05-11` | Training | 21.1 | 64 | 63 | 35.9% | 36.5% | 36.2%
| `session_2026-08-31_12-52-47` | Training | 20.6 | 66 | 66 | 89.4% | 89.4% | 89.4%
| `session_2026-09-01_12-50-20` | Training | 19.7 | 54 | 64 | 81.5% | 68.8% | 74.6%
