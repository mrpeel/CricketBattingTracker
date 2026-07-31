# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Session**: `session_2026-07-18_13-44-09`  
**Training Sessions Count**: 44 physical sessions  
**Total Dataset Duration**: 896.1 minutes (14.9 hours)  
**Date**: 2026-08-01 09:14

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Session (`session_2026-07-18_13-44-09`)** | **114** | **116** | **58.77%** | **56.90%** | **57.82%** |
| **Training Set Micro Average (44 Sessions)** | **2650** | **3150** | **92.91%** (2462/2650) | **78.54%** (2474/3150) | **85.12%** |
| 🏆 **Full Dataset Micro Average (All 45 Sessions)** | **2764** | **3266** | 🏆 **91.50%** (2529/2764) | 🏆 **77.77%** (2540/3266) | 🏆 **84.08%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Session Per-Shot Accuracy (session_2026-07-18_13-44-09)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 16 | 14 | 87.5% | 8 | **57.1%** | **50.0%** |
| **DRIVE/DEFENCE** | 34 | 20 | 58.8% | 16 | **80.0%** | **47.1%** |
| **GLANCE/FLICK** | 14 | 4 | 28.6% | 2 | **50.0%** | **14.3%** |
| **CUT/PUNCH** | 11 | 9 | 81.8% | 8 | **88.9%** | **72.7%** |
| **DEFLECTION/GUIDE** | 20 | 9 | 45.0% | 5 | **55.6%** | **25.0%** |
| **POWER DRIVE** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **SLOG** | 6 | 5 | 83.3% | 2 | **40.0%** | **33.3%** |
| **SWEEP** | 13 | 6 | 46.2% | 3 | **50.0%** | **23.1%** |
| **OVERALL TOTAL** | **114** | **67** | **58.8%** | **44** | 🏆 **65.7%** | 🏆 **38.6%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (44 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 531 | 490 | 92.3% | 381 | **77.8%** | **71.8%** |
| **DRIVE/DEFENCE** | 650 | 620 | 95.4% | 562 | **90.6%** | **86.5%** |
| **GLANCE/FLICK** | 443 | 422 | 95.3% | 352 | **83.4%** | **79.5%** |
| **CUT/PUNCH** | 237 | 229 | 96.6% | 202 | **88.2%** | **85.2%** |
| **DEFLECTION/GUIDE** | 231 | 159 | 68.8% | 149 | **93.7%** | **64.5%** |
| **POWER DRIVE** | 66 | 64 | 97.0% | 27 | **42.2%** | **40.9%** |
| **SLOG** | 309 | 304 | 98.4% | 293 | **96.4%** | **94.8%** |
| **SWEEP** | 183 | 174 | 95.1% | 147 | **84.5%** | **80.3%** |
| **OVERALL TOTAL** | **2650** | **2462** | **92.9%** | **2113** | 🏆 **85.8%** | 🏆 **79.7%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 45 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 547 | 504 | 92.1% | 389 | **77.2%** | **71.1%** |
| **DRIVE/DEFENCE** | 684 | 640 | 93.6% | 578 | **90.3%** | **84.5%** |
| **GLANCE/FLICK** | 457 | 426 | 93.2% | 354 | **83.1%** | **77.5%** |
| **CUT/PUNCH** | 248 | 238 | 96.0% | 210 | **88.2%** | **84.7%** |
| **DEFLECTION/GUIDE** | 251 | 168 | 66.9% | 154 | **91.7%** | **61.4%** |
| **POWER DRIVE** | 66 | 64 | 97.0% | 27 | **42.2%** | **40.9%** |
| **SLOG** | 315 | 309 | 98.1% | 295 | **95.5%** | **93.7%** |
| **SWEEP** | 196 | 180 | 91.8% | 150 | **83.3%** | **76.5%** |
| **OVERALL TOTAL** | **2764** | **2529** | **91.5%** | **2157** | 🏆 **85.3%** | 🏆 **78.0%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.8 | 119 | 124 | 83.2% | 79.0% | 81.1%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 5 | 1 | 20.0% | 100.0% | 33.3%
| `session_2026-05-31_14-12-10` | Training | 13.1 | 68 | 73 | 85.3% | 80.8% | 83.0%
| `session_2026-06-01_12-23-38` | Training | 18.0 | 65 | 79 | 95.4% | 78.5% | 86.1%
| `session_2026-06-05_12-29-59` | Training | 5.5 | 29 | 34 | 100.0% | 85.3% | 92.1%
| `session_2026-06-07_14-34-24` | Training | 12.2 | 57 | 61 | 89.5% | 83.6% | 86.4%
| `session_2026-06-08_12-22-26` | Training | 12.3 | 53 | 65 | 83.0% | 66.2% | 73.6%
| `session_2026-06-09_12-16-49` | Training | 12.7 | 60 | 65 | 96.7% | 89.2% | 92.8%
| `session_2026-06-11_12-27-53` | Training | 16.8 | 54 | 70 | 100.0% | 77.1% | 87.1%
| `session_2026-06-12_12-24-37` | Training | 21.1 | 72 | 88 | 100.0% | 81.8% | 90.0%
| `session_2026-06-13_10-59-04` | Training | 13.1 | 63 | 66 | 84.1% | 80.3% | 82.2%
| `session_2026-06-14_13-16-12` | Training | 15.9 | 73 | 74 | 90.4% | 90.5% | 90.5%
| `session_2026-06-15_12-21-37` | Training | 21.5 | 63 | 74 | 96.8% | 82.4% | 89.1%
| `session_2026-06-16_15-39-33` | Training | 18.1 | 54 | 76 | 96.3% | 68.4% | 80.0%
| `session_2026-06-18_12-23-09` | Training | 19.2 | 67 | 77 | 91.0% | 80.5% | 85.5%
| `session_2026-06-19_12-25-55` | Training | 17.0 | 61 | 69 | 95.1% | 84.1% | 89.2%
| `session_2026-06-21_13-53-17` | Training | 20.5 | 62 | 84 | 95.2% | 72.6% | 82.4%
| `session_2026-06-22_12-27-26` | Training | 20.4 | 63 | 76 | 95.2% | 78.9% | 86.3%
| `session_2026-06-23_12-24-48` | Training | 18.6 | 62 | 70 | 75.8% | 68.6% | 72.0%
| `session_2026-06-25_12-25-07` | Training | 21.6 | 67 | 76 | 92.5% | 81.6% | 86.7%
| `session_2026-06-26_12-22-13` | Training | 19.1 | 61 | 76 | 98.4% | 78.9% | 87.6%
| `session_2026-06-27_14-12-40` | Training | 18.1 | 56 | 65 | 98.2% | 84.6% | 90.9%
| `session_2026-06-28_11-28-09` | Training | 20.2 | 55 | 68 | 96.4% | 79.4% | 87.1%
| `session_2026-06-29_12-21-45` | Training | 18.6 | 62 | 83 | 100.0% | 74.7% | 85.5%
| `session_2026-07-02_12-38-53` | Training | 21.2 | 62 | 82 | 95.2% | 72.0% | 81.9%
| `session_2026-07-04_12-19-20` | Training | 20.6 | 55 | 74 | 92.7% | 70.3% | 80.0%
| `session_2026-07-05_16-27-16` | Training | 18.9 | 59 | 79 | 93.2% | 70.9% | 80.5%
| `session_2026-07-06_12-25-05` | Training | 18.4 | 61 | 73 | 96.7% | 82.2% | 88.9%
| `session_2026-07-07_15-10-50` | Training | 22.4 | 55 | 74 | 80.0% | 59.5% | 68.2%
| `session_2026-07-09_12-19-05` | Training | 19.8 | 61 | 74 | 98.4% | 81.1% | 88.9%
| `session_2026-07-10_12-30-15` | Training | 19.2 | 60 | 72 | 90.0% | 75.0% | 81.8%
| `session_2026-07-11_12-51-39` | Training | 17.6 | 63 | 68 | 88.9% | 83.8% | 86.3%
| `session_2026-07-12_11-23-59` | Training | 15.1 | 60 | 70 | 100.0% | 85.7% | 92.3%
| `session_2026-07-13_12-17-57` | Training | 22.0 | 69 | 85 | 95.7% | 78.8% | 86.4%
| `session_2026-07-17_12-30-41` | Training | 128.6 | 66 | 76 | 98.5% | 85.5% | 91.5%
| `session_2026-07-18_13-44-09` | 🌟 HOLDOUT | 21.6 | 114 | 116 | 58.8% | 56.9% | 57.8%
| `session_2026-07-20_12-42-16` | Training | 16.0 | 42 | 61 | 95.2% | 65.6% | 77.7%
| `session_2026-07-21_12-43-37` | Training | 18.9 | 63 | 76 | 95.2% | 78.9% | 86.3%
| `session_2026-07-23_12-37-13` | Training | 13.0 | 63 | 66 | 95.2% | 90.9% | 93.0%
| `session_2026-07-24_12-52-29` | Training | 18.6 | 63 | 74 | 92.1% | 81.1% | 86.2%
| `session_2026-07-25_15-16-32` | Training | 21.3 | 64 | 78 | 96.9% | 79.5% | 87.3%
| `session_2026-07-26_11-44-54` | Training | 15.5 | 62 | 69 | 95.2% | 85.5% | 90.1%
| `session_2026-07-27_12-47-20` | Training | 18.9 | 59 | 66 | 94.9% | 84.8% | 89.6%
| `session_2026-07-28_12-43-23` | Training | 17.0 | 52 | 61 | 80.8% | 68.9% | 74.3%
| `session_2026-07-31_12-44-46` | Training | 18.0 | 60 | 78 | 98.3% | 75.6% | 85.5%
