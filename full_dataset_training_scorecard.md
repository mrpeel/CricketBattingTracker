# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Session**: `session_2026-07-18_13-44-09`  
**Training Sessions Count**: 44 physical sessions  
**Total Dataset Duration**: 896.1 minutes (14.9 hours)  
**Date**: 2026-07-31 18:55

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Session (`session_2026-07-18_13-44-09`)** | **114** | **118** | **59.65%** | **56.78%** | **58.18%** |
| **Training Set Micro Average (44 Sessions)** | **2650** | **3217** | **94.04%** (2492/2650) | **77.84%** (2504/3217) | **85.17%** |
| 🏆 **Full Dataset Micro Average (All 45 Sessions)** | **2764** | **3335** | 🏆 **92.62%** (2560/2764) | 🏆 **77.09%** (2571/3335) | 🏆 **84.15%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Session Per-Shot Accuracy (session_2026-07-18_13-44-09)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pull** | 16 | 14 | 87.5% | 5 | **35.7%** | **31.2%** |
| **Defence** | 40 | 23 | 57.5% | 14 | **60.9%** | **35.0%** |
| **Flick** | 14 | 4 | 28.6% | 2 | **50.0%** | **14.3%** |
| **Drive** | 14 | 7 | 50.0% | 6 | **85.7%** | **42.9%** |
| **Glance** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **Sweep** | 13 | 6 | 46.2% | 3 | **50.0%** | **23.1%** |
| **Cut** | 11 | 9 | 81.8% | 2 | **22.2%** | **18.2%** |
| **Slog** | 6 | 5 | 83.3% | 4 | **80.0%** | **66.7%** |
| **OVERALL TOTAL** | **114** | **68** | **59.6%** | **36** | 🏆 **52.9%** | 🏆 **31.6%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (44 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pull** | 531 | 514 | 96.8% | 433 | **84.2%** | **81.5%** |
| **Defence** | 629 | 536 | 85.2% | 472 | **88.1%** | **75.0%** |
| **Flick** | 364 | 352 | 96.7% | 263 | **74.7%** | **72.3%** |
| **Drive** | 318 | 309 | 97.2% | 189 | **61.2%** | **59.4%** |
| **Glance** | 79 | 71 | 89.9% | 41 | **57.7%** | **51.9%** |
| **Sweep** | 183 | 174 | 95.1% | 158 | **90.8%** | **86.3%** |
| **Cut** | 237 | 231 | 97.5% | 172 | **74.5%** | **72.6%** |
| **Slog** | 309 | 305 | 98.7% | 297 | **97.4%** | **96.1%** |
| **OVERALL TOTAL** | **2650** | **2492** | **94.0%** | **2025** | 🏆 **81.3%** | 🏆 **76.4%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 45 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pull** | 547 | 528 | 96.5% | 438 | **83.0%** | **80.1%** |
| **Defence** | 669 | 559 | 83.6% | 486 | **86.9%** | **72.6%** |
| **Flick** | 378 | 356 | 94.2% | 265 | **74.4%** | **70.1%** |
| **Drive** | 332 | 316 | 95.2% | 195 | **61.7%** | **58.7%** |
| **Glance** | 79 | 71 | 89.9% | 41 | **57.7%** | **51.9%** |
| **Sweep** | 196 | 180 | 91.8% | 161 | **89.4%** | **82.1%** |
| **Cut** | 248 | 240 | 96.8% | 174 | **72.5%** | **70.2%** |
| **Slog** | 315 | 310 | 98.4% | 301 | **97.1%** | **95.6%** |
| **OVERALL TOTAL** | **2764** | **2560** | **92.6%** | **2061** | 🏆 **80.5%** | 🏆 **74.6%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.8 | 119 | 124 | 83.2% | 79.0% | 81.1%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 5 | 2 | 20.0% | 50.0% | 28.6%
| `session_2026-05-31_14-12-10` | Training | 13.1 | 68 | 73 | 85.3% | 80.8% | 83.0%
| `session_2026-06-01_12-23-38` | Training | 18.0 | 65 | 81 | 95.4% | 76.5% | 84.9%
| `session_2026-06-05_12-29-59` | Training | 5.5 | 29 | 34 | 100.0% | 85.3% | 92.1%
| `session_2026-06-07_14-34-24` | Training | 12.2 | 57 | 62 | 91.2% | 83.9% | 87.4%
| `session_2026-06-08_12-22-26` | Training | 12.3 | 53 | 66 | 83.0% | 65.2% | 73.0%
| `session_2026-06-09_12-16-49` | Training | 12.7 | 60 | 66 | 96.7% | 87.9% | 92.1%
| `session_2026-06-11_12-27-53` | Training | 16.8 | 54 | 72 | 100.0% | 75.0% | 85.7%
| `session_2026-06-12_12-24-37` | Training | 21.1 | 72 | 89 | 100.0% | 80.9% | 89.4%
| `session_2026-06-13_10-59-04` | Training | 13.1 | 63 | 72 | 93.7% | 81.9% | 87.4%
| `session_2026-06-14_13-16-12` | Training | 15.9 | 73 | 74 | 90.4% | 90.5% | 90.5%
| `session_2026-06-15_12-21-37` | Training | 21.5 | 63 | 74 | 96.8% | 82.4% | 89.1%
| `session_2026-06-16_15-39-33` | Training | 18.1 | 54 | 77 | 96.3% | 67.5% | 79.4%
| `session_2026-06-18_12-23-09` | Training | 19.2 | 67 | 83 | 97.0% | 79.5% | 87.4%
| `session_2026-06-19_12-25-55` | Training | 17.0 | 61 | 71 | 95.1% | 81.7% | 87.9%
| `session_2026-06-21_13-53-17` | Training | 20.5 | 62 | 89 | 96.8% | 69.7% | 81.0%
| `session_2026-06-22_12-27-26` | Training | 20.4 | 63 | 78 | 96.8% | 78.2% | 86.5%
| `session_2026-06-23_12-24-48` | Training | 18.6 | 62 | 71 | 75.8% | 67.6% | 71.5%
| `session_2026-06-25_12-25-07` | Training | 21.6 | 67 | 76 | 92.5% | 81.6% | 86.7%
| `session_2026-06-26_12-22-13` | Training | 19.1 | 61 | 77 | 98.4% | 77.9% | 87.0%
| `session_2026-06-27_14-12-40` | Training | 18.1 | 56 | 65 | 98.2% | 84.6% | 90.9%
| `session_2026-06-28_11-28-09` | Training | 20.2 | 55 | 69 | 96.4% | 78.3% | 86.4%
| `session_2026-06-29_12-21-45` | Training | 18.6 | 62 | 83 | 100.0% | 74.7% | 85.5%
| `session_2026-07-02_12-38-53` | Training | 21.2 | 62 | 83 | 95.2% | 71.1% | 81.4%
| `session_2026-07-04_12-19-20` | Training | 20.6 | 55 | 78 | 96.4% | 69.2% | 80.6%
| `session_2026-07-05_16-27-16` | Training | 18.9 | 59 | 79 | 93.2% | 70.9% | 80.5%
| `session_2026-07-06_12-25-05` | Training | 18.4 | 61 | 74 | 98.4% | 82.4% | 89.7%
| `session_2026-07-07_15-10-50` | Training | 22.4 | 55 | 74 | 80.0% | 59.5% | 68.2%
| `session_2026-07-09_12-19-05` | Training | 19.8 | 61 | 74 | 98.4% | 81.1% | 88.9%
| `session_2026-07-10_12-30-15` | Training | 19.2 | 60 | 73 | 90.0% | 74.0% | 81.2%
| `session_2026-07-11_12-51-39` | Training | 17.6 | 63 | 74 | 96.8% | 83.8% | 89.8%
| `session_2026-07-12_11-23-59` | Training | 15.1 | 60 | 71 | 100.0% | 84.5% | 91.6%
| `session_2026-07-13_12-17-57` | Training | 22.0 | 69 | 85 | 95.7% | 78.8% | 86.4%
| `session_2026-07-17_12-30-41` | Training | 128.6 | 66 | 78 | 98.5% | 83.3% | 90.3%
| `session_2026-07-18_13-44-09` | 🌟 HOLDOUT | 21.6 | 114 | 118 | 59.6% | 56.8% | 58.2%
| `session_2026-07-20_12-42-16` | Training | 16.0 | 42 | 62 | 95.2% | 64.5% | 76.9%
| `session_2026-07-21_12-43-37` | Training | 18.9 | 63 | 77 | 96.8% | 79.2% | 87.1%
| `session_2026-07-23_12-37-13` | Training | 13.0 | 63 | 67 | 96.8% | 91.0% | 93.8%
| `session_2026-07-24_12-52-29` | Training | 18.6 | 63 | 75 | 92.1% | 80.0% | 85.6%
| `session_2026-07-25_15-16-32` | Training | 21.3 | 64 | 78 | 96.9% | 79.5% | 87.3%
| `session_2026-07-26_11-44-54` | Training | 15.5 | 62 | 69 | 95.2% | 85.5% | 90.1%
| `session_2026-07-27_12-47-20` | Training | 18.9 | 59 | 72 | 100.0% | 81.9% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 17.0 | 52 | 65 | 88.5% | 70.8% | 78.6%
| `session_2026-07-31_12-44-46` | Training | 18.0 | 60 | 81 | 98.3% | 72.8% | 83.7%
