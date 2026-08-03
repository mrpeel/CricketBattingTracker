# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Sessions**: `session_2026-07-18_13-44-09, session_2026-08-01_10-18-20` (2 sessions)  
**Training Sessions Count**: 46 physical sessions  
**Total Dataset Duration**: 803.5 minutes (13.4 hours)  
**Date**: 2026-08-04 06:49

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (2 Sessions)** | **142** | **154** | **65.49%** | **60.39%** | **62.84%** |
| **Training Set Micro Average (46 Sessions)** | **2764** | **3269** | **93.05%** (2572/2764) | **78.68%** (2572/3269) | **85.26%** |
| 🏆 **Full Dataset Micro Average (All 48 Sessions)** | **2906** | **3423** | 🏆 **91.71%** (2665/2906) | 🏆 **77.86%** (2665/3423) | 🏆 **84.22%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (2 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 17 | 6 | 35.3% | 2 | **33.3%** | **11.8%** |
| **DRIVE/DEFENCE** | 35 | 31 | 88.6% | 14 | **45.2%** | **40.0%** |
| **GLANCE/FLICK** | 14 | 15 | 107.1% | 3 | **20.0%** | **21.4%** |
| **CUT/PUNCH** | 11 | 15 | 136.4% | 5 | **33.3%** | **45.5%** |
| **DEFLECTION/GUIDE** | 20 | 14 | 70.0% | 4 | **28.6%** | **20.0%** |
| **POWER DRIVE** | 19 | 23 | 121.1% | 14 | **60.9%** | **73.7%** |
| **SLOG** | 13 | 13 | 100.0% | 1 | **7.7%** | **7.7%** |
| **SWEEP** | 13 | 37 | 284.6% | 6 | **16.2%** | **46.2%** |
| **OVERALL TOTAL** | **142** | **154** | **108.5%** | **49** | 🏆 **31.8%** | 🏆 **34.5%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (46 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 545 | 490 | 89.9% | 388 | **79.2%** | **71.2%** |
| **DRIVE/DEFENCE** | 652 | 687 | 105.4% | 523 | **76.1%** | **80.2%** |
| **GLANCE/FLICK** | 452 | 532 | 117.7% | 340 | **63.9%** | **75.2%** |
| **CUT/PUNCH** | 237 | 345 | 145.6% | 201 | **58.3%** | **84.8%** |
| **DEFLECTION/GUIDE** | 231 | 289 | 125.1% | 141 | **48.8%** | **61.0%** |
| **POWER DRIVE** | 114 | 75 | 65.8% | 52 | **69.3%** | **45.6%** |
| **SLOG** | 310 | 506 | 163.2% | 287 | **56.7%** | **92.6%** |
| **SWEEP** | 223 | 345 | 154.7% | 197 | **57.1%** | **88.3%** |
| **OVERALL TOTAL** | **2764** | **3269** | **118.3%** | **2129** | 🏆 **65.1%** | 🏆 **77.0%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 48 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 562 | 496 | 88.3% | 390 | **78.6%** | **69.4%** |
| **DRIVE/DEFENCE** | 687 | 718 | 104.5% | 537 | **74.8%** | **78.2%** |
| **GLANCE/FLICK** | 466 | 547 | 117.4% | 343 | **62.7%** | **73.6%** |
| **CUT/PUNCH** | 248 | 360 | 145.2% | 206 | **57.2%** | **83.1%** |
| **DEFLECTION/GUIDE** | 251 | 303 | 120.7% | 145 | **47.9%** | **57.8%** |
| **POWER DRIVE** | 133 | 98 | 73.7% | 66 | **67.3%** | **49.6%** |
| **SLOG** | 323 | 519 | 160.7% | 288 | **55.5%** | **89.2%** |
| **SWEEP** | 236 | 382 | 161.9% | 203 | **53.1%** | **86.0%** |
| **OVERALL TOTAL** | **2906** | **3423** | **117.8%** | **2178** | 🏆 **63.6%** | 🏆 **74.9%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.5 | 119 | 124 | 82.4% | 79.0% | 80.7%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 5 | 1 | 20.0% | 100.0% | 33.3%
| `session_2026-05-31_14-12-10` | Training | 13.0 | 68 | 73 | 85.3% | 79.5% | 82.3%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 65 | 78 | 95.4% | 79.5% | 86.7%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 29 | 34 | 100.0% | 85.3% | 92.1%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 57 | 61 | 89.5% | 83.6% | 86.4%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 53 | 65 | 81.1% | 66.2% | 72.9%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 60 | 65 | 96.7% | 89.2% | 92.8%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 54 | 70 | 100.0% | 77.1% | 87.1%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 72 | 88 | 100.0% | 81.8% | 90.0%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 63 | 66 | 84.1% | 80.3% | 82.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 73 | 74 | 90.4% | 89.2% | 89.8%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 63 | 74 | 96.8% | 82.4% | 89.1%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 54 | 70 | 96.3% | 74.3% | 83.9%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 67 | 77 | 91.0% | 79.2% | 84.7%
| `session_2026-06-19_12-25-55` | Training | 16.6 | 61 | 68 | 95.1% | 85.3% | 89.9%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 62 | 83 | 95.2% | 71.1% | 81.4%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 63 | 76 | 95.2% | 78.9% | 86.3%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 62 | 70 | 74.2% | 65.7% | 69.7%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 67 | 76 | 92.5% | 81.6% | 86.7%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 61 | 76 | 98.4% | 78.9% | 87.6%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 56 | 65 | 98.2% | 84.6% | 90.9%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 55 | 68 | 96.4% | 77.9% | 86.2%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 62 | 82 | 100.0% | 75.6% | 86.1%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 62 | 82 | 95.2% | 72.0% | 81.9%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 55 | 74 | 92.7% | 68.9% | 79.1%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 59 | 79 | 93.2% | 69.6% | 79.7%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 61 | 73 | 96.7% | 80.8% | 88.1%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 55 | 74 | 80.0% | 59.5% | 68.2%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 61 | 74 | 98.4% | 81.1% | 88.9%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 60 | 72 | 90.0% | 75.0% | 81.8%
| `session_2026-07-11_12-51-39` | Training | 17.1 | 63 | 68 | 88.9% | 82.4% | 85.5%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 60 | 70 | 100.0% | 85.7% | 92.3%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 69 | 85 | 95.7% | 77.6% | 85.7%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 66 | 76 | 98.5% | 85.5% | 91.5%
| `session_2026-07-18_13-44-09` | 🌟 HOLDOUT | 21.3 | 114 | 116 | 57.0% | 56.0% | 56.5%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 42 | 60 | 95.2% | 66.7% | 78.4%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 63 | 76 | 95.2% | 78.9% | 86.3%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 63 | 66 | 95.2% | 90.9% | 93.0%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 63 | 74 | 92.1% | 78.4% | 84.7%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 64 | 77 | 96.9% | 80.5% | 87.9%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 62 | 69 | 95.2% | 85.5% | 90.1%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 59 | 66 | 94.9% | 84.8% | 89.6%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 52 | 60 | 80.8% | 70.0% | 75.0%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 60 | 77 | 98.3% | 76.6% | 86.1%
| `session_2026-08-01_10-18-20` | 🌟 HOLDOUT | 8.9 | 28 | 38 | 100.0% | 73.7% | 84.8%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 51 | 52 | 98.0% | 96.2% | 97.1%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 63 | 81 | 100.0% | 77.8% | 87.5%
