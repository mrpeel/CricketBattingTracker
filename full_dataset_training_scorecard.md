# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Sessions**: `session_2026-07-18_13-44-09, session_2026-08-01_10-18-20` (2 sessions)  
**Training Sessions Count**: 45 physical sessions  
**Total Dataset Duration**: 785.3 minutes (13.1 hours)  
**Date**: 2026-08-03 07:04

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (2 Sessions)** | **142** | **154** | **66.90%** | **61.04%** | **63.84%** |
| **Training Set Micro Average (45 Sessions)** | **2701** | **3188** | **93.00%** (2512/2701) | **79.17%** (2524/3188) | **85.53%** |
| 🏆 **Full Dataset Micro Average (All 47 Sessions)** | **2843** | **3342** | 🏆 **91.70%** (2607/2843) | 🏆 **78.34%** (2618/3342) | 🏆 **84.49%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (2 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 17 | 15 | 88.2% | 0 | **0.0%** | **0.0%** |
| **DRIVE/DEFENCE** | 35 | 21 | 60.0% | 14 | **66.7%** | **40.0%** |
| **GLANCE/FLICK** | 14 | 4 | 28.6% | 3 | **75.0%** | **21.4%** |
| **CUT/PUNCH** | 11 | 9 | 81.8% | 9 | **100.0%** | **81.8%** |
| **DEFLECTION/GUIDE** | 20 | 9 | 45.0% | 4 | **44.4%** | **20.0%** |
| **POWER DRIVE** | 19 | 19 | 100.0% | 8 | **42.1%** | **42.1%** |
| **SLOG** | 13 | 12 | 92.3% | 6 | **50.0%** | **46.2%** |
| **SWEEP** | 13 | 6 | 46.2% | 6 | **100.0%** | **46.2%** |
| **OVERALL TOTAL** | **142** | **95** | **66.9%** | **50** | 🏆 **52.6%** | 🏆 **35.2%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (45 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 532 | 491 | 92.3% | 328 | **66.8%** | **61.7%** |
| **DRIVE/DEFENCE** | 652 | 621 | 95.2% | 544 | **87.6%** | **83.4%** |
| **GLANCE/FLICK** | 451 | 430 | 95.3% | 333 | **77.4%** | **73.8%** |
| **CUT/PUNCH** | 237 | 229 | 96.6% | 214 | **93.4%** | **90.3%** |
| **DEFLECTION/GUIDE** | 231 | 159 | 68.8% | 144 | **90.6%** | **62.3%** |
| **POWER DRIVE** | 66 | 64 | 97.0% | 41 | **64.1%** | **62.1%** |
| **SLOG** | 309 | 304 | 98.4% | 266 | **87.5%** | **86.1%** |
| **SWEEP** | 223 | 214 | 96.0% | 191 | **89.3%** | **85.7%** |
| **OVERALL TOTAL** | **2701** | **2512** | **93.0%** | **2061** | 🏆 **82.0%** | 🏆 **76.3%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 47 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 549 | 506 | 92.2% | 328 | **64.8%** | **59.7%** |
| **DRIVE/DEFENCE** | 687 | 642 | 93.4% | 558 | **86.9%** | **81.2%** |
| **GLANCE/FLICK** | 465 | 434 | 93.3% | 336 | **77.4%** | **72.3%** |
| **CUT/PUNCH** | 248 | 238 | 96.0% | 223 | **93.7%** | **89.9%** |
| **DEFLECTION/GUIDE** | 251 | 168 | 66.9% | 148 | **88.1%** | **59.0%** |
| **POWER DRIVE** | 85 | 83 | 97.6% | 49 | **59.0%** | **57.6%** |
| **SLOG** | 322 | 316 | 98.1% | 272 | **86.1%** | **84.5%** |
| **SWEEP** | 236 | 220 | 93.2% | 197 | **89.5%** | **83.5%** |
| **OVERALL TOTAL** | **2843** | **2607** | **91.7%** | **2111** | 🏆 **81.0%** | 🏆 **74.3%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.5 | 119 | 124 | 83.2% | 79.0% | 81.1%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 5 | 1 | 20.0% | 100.0% | 33.3%
| `session_2026-05-31_14-12-10` | Training | 13.0 | 68 | 73 | 85.3% | 80.8% | 83.0%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 65 | 78 | 95.4% | 79.5% | 86.7%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 29 | 34 | 100.0% | 85.3% | 92.1%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 57 | 61 | 89.5% | 83.6% | 86.4%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 53 | 65 | 83.0% | 66.2% | 73.6%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 60 | 65 | 96.7% | 89.2% | 92.8%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 54 | 70 | 100.0% | 77.1% | 87.1%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 72 | 88 | 100.0% | 81.8% | 90.0%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 63 | 66 | 84.1% | 80.3% | 82.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 73 | 74 | 90.4% | 90.5% | 90.5%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 63 | 74 | 96.8% | 82.4% | 89.1%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 54 | 70 | 96.3% | 74.3% | 83.9%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 67 | 77 | 91.0% | 80.5% | 85.5%
| `session_2026-06-19_12-25-55` | Training | 16.6 | 61 | 68 | 95.1% | 85.3% | 89.9%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 62 | 83 | 95.2% | 73.5% | 82.9%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 63 | 76 | 95.2% | 78.9% | 86.3%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 62 | 70 | 75.8% | 68.6% | 72.0%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 67 | 76 | 92.5% | 81.6% | 86.7%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 61 | 76 | 98.4% | 78.9% | 87.6%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 56 | 65 | 98.2% | 84.6% | 90.9%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 55 | 68 | 96.4% | 79.4% | 87.1%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 62 | 82 | 100.0% | 75.6% | 86.1%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 62 | 82 | 95.2% | 72.0% | 81.9%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 55 | 74 | 92.7% | 70.3% | 80.0%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 59 | 79 | 93.2% | 70.9% | 80.5%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 61 | 73 | 96.7% | 82.2% | 88.9%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 55 | 74 | 80.0% | 59.5% | 68.2%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 61 | 74 | 98.4% | 81.1% | 88.9%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 60 | 72 | 90.0% | 75.0% | 81.8%
| `session_2026-07-11_12-51-39` | Training | 17.1 | 63 | 68 | 88.9% | 83.8% | 86.3%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 60 | 70 | 100.0% | 85.7% | 92.3%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 69 | 85 | 95.7% | 78.8% | 86.4%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 66 | 76 | 98.5% | 85.5% | 91.5%
| `session_2026-07-18_13-44-09` | 🌟 HOLDOUT | 21.3 | 114 | 116 | 58.8% | 56.9% | 57.8%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 42 | 60 | 95.2% | 66.7% | 78.4%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 63 | 76 | 95.2% | 78.9% | 86.3%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 63 | 66 | 95.2% | 90.9% | 93.0%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 63 | 74 | 92.1% | 81.1% | 86.2%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 64 | 77 | 96.9% | 80.5% | 87.9%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 62 | 69 | 95.2% | 85.5% | 90.1%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 59 | 66 | 94.9% | 84.8% | 89.6%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 52 | 60 | 80.8% | 70.0% | 75.0%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 60 | 77 | 98.3% | 76.6% | 86.1%
| `session_2026-08-01_10-18-20` | 🌟 HOLDOUT | 8.9 | 28 | 38 | 100.0% | 73.7% | 84.8%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 51 | 52 | 98.0% | 96.2% | 97.1%
