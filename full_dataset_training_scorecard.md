# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Session**: `session_2026-07-18_13-44-09`  
**Training Sessions Count**: 44 physical sessions  
**Total Dataset Duration**: 896.1 minutes (14.9 hours)  
**Date**: 2026-07-31 15:36

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Session (`session_2026-07-18_13-44-09`)** | **114** | **98** | **53.51%** | **60.20%** | **56.66%** |
| **Training Set Micro Average (44 Sessions)** | **2650** | **2606** | **87.06%** (2307/2650) | **88.45%** (2305/2606) | **87.75%** |
| 🏆 **Full Dataset Micro Average (All 45 Sessions)** | **2764** | **2704** | 🏆 **85.67%** (2368/2764) | 🏆 **87.43%** (2364/2704) | 🏆 **86.54%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Session Per-Shot Accuracy (session_2026-07-18_13-44-09)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pull** | 16 | 13 | 81.2% | 6 | **46.2%** | **37.5%** |
| **Defence** | 11 | 3 | 27.3% | 2 | **66.7%** | **18.2%** |
| **Flick** | 54 | 29 | 53.7% | 3 | **10.3%** | **5.6%** |
| **Drive** | 14 | 7 | 50.0% | 6 | **85.7%** | **42.9%** |
| **Glance** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **Sweep** | 13 | 6 | 46.2% | 4 | **66.7%** | **30.8%** |
| **Cut** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **Slog** | 6 | 3 | 50.0% | 1 | **33.3%** | **16.7%** |
| **OVERALL TOTAL** | **114** | **61** | **53.5%** | **22** | 🏆 **36.1%** | 🏆 **19.3%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (44 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pull** | 531 | 508 | 95.7% | 385 | **75.8%** | **72.5%** |
| **Defence** | 278 | 215 | 77.3% | 190 | **88.4%** | **68.3%** |
| **Flick** | 1018 | 806 | 79.2% | 249 | **30.9%** | **24.5%** |
| **Drive** | 252 | 241 | 95.6% | 152 | **63.1%** | **60.3%** |
| **Glance** | 79 | 61 | 77.2% | 28 | **45.9%** | **35.4%** |
| **Sweep** | 183 | 172 | 94.0% | 163 | **94.8%** | **89.1%** |
| **Cut** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **Slog** | 309 | 304 | 98.4% | 299 | **98.4%** | **96.8%** |
| **OVERALL TOTAL** | **2650** | **2307** | **87.1%** | **1466** | 🏆 **63.5%** | 🏆 **55.3%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 45 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pull** | 547 | 521 | 95.2% | 391 | **75.0%** | **71.5%** |
| **Defence** | 289 | 218 | 75.4% | 192 | **88.1%** | **66.4%** |
| **Flick** | 1072 | 835 | 77.9% | 252 | **30.2%** | **23.5%** |
| **Drive** | 266 | 248 | 93.2% | 158 | **63.7%** | **59.4%** |
| **Glance** | 79 | 61 | 77.2% | 28 | **45.9%** | **35.4%** |
| **Sweep** | 196 | 178 | 90.8% | 167 | **93.8%** | **85.2%** |
| **Cut** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **Slog** | 315 | 307 | 97.5% | 300 | **97.7%** | **95.2%** |
| **OVERALL TOTAL** | **2764** | **2368** | **85.7%** | **1488** | 🏆 **62.8%** | 🏆 **53.8%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.8 | 119 | 102 | 71.4% | 82.4% | 76.5%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 5 | 2 | 20.0% | 50.0% | 28.6%
| `session_2026-05-31_14-12-10` | Training | 13.1 | 68 | 62 | 80.9% | 88.7% | 84.6%
| `session_2026-06-01_12-23-38` | Training | 18.0 | 65 | 64 | 84.6% | 85.9% | 85.3%
| `session_2026-06-05_12-29-59` | Training | 5.5 | 29 | 29 | 93.1% | 93.1% | 93.1%
| `session_2026-06-07_14-34-24` | Training | 12.2 | 57 | 55 | 82.5% | 85.5% | 83.9%
| `session_2026-06-08_12-22-26` | Training | 12.3 | 53 | 60 | 83.0% | 71.7% | 76.9%
| `session_2026-06-09_12-16-49` | Training | 12.7 | 60 | 59 | 91.7% | 91.5% | 91.6%
| `session_2026-06-11_12-27-53` | Training | 16.8 | 54 | 60 | 100.0% | 90.0% | 94.7%
| `session_2026-06-12_12-24-37` | Training | 21.1 | 72 | 74 | 97.2% | 94.6% | 95.9%
| `session_2026-06-13_10-59-04` | Training | 13.1 | 63 | 56 | 82.5% | 92.9% | 87.4%
| `session_2026-06-14_13-16-12` | Training | 15.9 | 73 | 72 | 90.4% | 91.7% | 91.0%
| `session_2026-06-15_12-21-37` | Training | 21.5 | 63 | 65 | 95.2% | 92.3% | 93.8%
| `session_2026-06-16_15-39-33` | Training | 18.1 | 54 | 59 | 94.4% | 86.4% | 90.3%
| `session_2026-06-18_12-23-09` | Training | 19.2 | 67 | 69 | 92.5% | 89.9% | 91.2%
| `session_2026-06-19_12-25-55` | Training | 17.0 | 61 | 51 | 75.4% | 90.2% | 82.1%
| `session_2026-06-21_13-53-17` | Training | 20.5 | 62 | 55 | 77.4% | 87.3% | 82.1%
| `session_2026-06-22_12-27-26` | Training | 20.4 | 63 | 62 | 90.5% | 91.9% | 91.2%
| `session_2026-06-23_12-24-48` | Training | 18.6 | 62 | 60 | 69.4% | 71.7% | 70.5%
| `session_2026-06-25_12-25-07` | Training | 21.6 | 67 | 60 | 82.1% | 91.7% | 86.6%
| `session_2026-06-26_12-22-13` | Training | 19.1 | 61 | 65 | 95.1% | 89.2% | 92.1%
| `session_2026-06-27_14-12-40` | Training | 18.1 | 56 | 55 | 92.9% | 94.5% | 93.7%
| `session_2026-06-28_11-28-09` | Training | 20.2 | 55 | 55 | 92.7% | 94.5% | 93.6%
| `session_2026-06-29_12-21-45` | Training | 18.6 | 62 | 67 | 100.0% | 92.5% | 96.1%
| `session_2026-07-02_12-38-53` | Training | 21.2 | 62 | 69 | 93.5% | 84.1% | 88.5%
| `session_2026-07-04_12-19-20` | Training | 20.6 | 55 | 58 | 92.7% | 87.9% | 90.3%
| `session_2026-07-05_16-27-16` | Training | 18.9 | 59 | 61 | 88.1% | 85.2% | 86.7%
| `session_2026-07-06_12-25-05` | Training | 18.4 | 61 | 63 | 98.4% | 95.2% | 96.8%
| `session_2026-07-07_15-10-50` | Training | 22.4 | 55 | 16 | 16.4% | 56.2% | 25.4%
| `session_2026-07-09_12-19-05` | Training | 19.8 | 61 | 64 | 96.7% | 92.2% | 94.4%
| `session_2026-07-10_12-30-15` | Training | 19.2 | 60 | 46 | 70.0% | 91.3% | 79.2%
| `session_2026-07-11_12-51-39` | Training | 17.6 | 63 | 66 | 96.8% | 92.4% | 94.6%
| `session_2026-07-12_11-23-59` | Training | 15.1 | 60 | 67 | 100.0% | 89.6% | 94.5%
| `session_2026-07-13_12-17-57` | Training | 22.0 | 69 | 61 | 81.2% | 91.8% | 86.2%
| `session_2026-07-17_12-30-41` | Training | 128.6 | 66 | 64 | 92.4% | 95.3% | 93.8%
| `session_2026-07-18_13-44-09` | 🌟 HOLDOUT | 21.6 | 114 | 98 | 53.5% | 60.2% | 56.7%
| `session_2026-07-20_12-42-16` | Training | 16.0 | 42 | 55 | 95.2% | 72.7% | 82.5%
| `session_2026-07-21_12-43-37` | Training | 18.9 | 63 | 68 | 92.1% | 85.3% | 88.5%
| `session_2026-07-23_12-37-13` | Training | 13.0 | 63 | 65 | 96.8% | 93.8% | 95.3%
| `session_2026-07-24_12-52-29` | Training | 18.6 | 63 | 47 | 68.3% | 91.5% | 78.2%
| `session_2026-07-25_15-16-32` | Training | 21.3 | 64 | 69 | 96.9% | 89.9% | 93.2%
| `session_2026-07-26_11-44-54` | Training | 15.5 | 62 | 63 | 95.2% | 93.7% | 94.4%
| `session_2026-07-27_12-47-20` | Training | 18.9 | 59 | 61 | 96.6% | 93.4% | 95.0%
| `session_2026-07-28_12-43-23` | Training | 17.0 | 52 | 56 | 82.7% | 76.8% | 79.6%
| `session_2026-07-31_12-44-46` | Training | 18.0 | 60 | 69 | 98.3% | 85.5% | 91.5%
