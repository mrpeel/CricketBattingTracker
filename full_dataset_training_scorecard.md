# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Designated Holdout Sessions**: `session_2026-07-21_12-43-37, session_2026-07-25_15-16-32` (2 sessions)  
**Training Sessions Count**: 46 physical sessions  
**Total Dataset Duration**: 803.5 minutes (13.4 hours)  
**Date**: 2026-08-04 20:45

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (2 Sessions)** | **117** | **153** | **97.44%** | **74.51%** | **84.44%** |
| **Training Set Micro Average (46 Sessions)** | **2481** | **3270** | **95.36%** (2366/2481) | **72.35%** (2366/3270) | **82.28%** |
| 🏆 **Full Dataset Micro Average (All 48 Sessions)** | **2598** | **3423** | 🏆 **95.46%** (2480/2598) | 🏆 **72.45%** (2480/3423) | 🏆 **82.38%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (2 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 25 | 25 | 100.0% | 9 | **36.0%** | **36.0%** |
| **DRIVE/DEFENCE** | 17 | 34 | 200.0% | 15 | **44.1%** | **88.2%** |
| **GLANCE/FLICK** | 22 | 35 | 159.1% | 17 | **48.6%** | **77.3%** |
| **CUT/PUNCH** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **DEFLECTION/GUIDE** | 1 | 6 | 600.0% | 0 | **0.0%** | **0.0%** |
| **POWER DRIVE** | 20 | 6 | 30.0% | 2 | **33.3%** | **10.0%** |
| **SLOG** | 32 | 40 | 125.0% | 19 | **47.5%** | **59.4%** |
| **SWEEP** | 0 | 7 | 0.0% | 0 | **0.0%** | **0.0%** |
| **OVERALL TOTAL** | **117** | **153** | **130.8%** | **62** | 🏆 **40.5%** | 🏆 **53.0%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (46 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 492 | 514 | 104.5% | 379 | **73.7%** | **77.0%** |
| **DRIVE/DEFENCE** | 610 | 816 | 133.8% | 530 | **65.0%** | **86.9%** |
| **GLANCE/FLICK** | 384 | 490 | 127.6% | 275 | **56.1%** | **71.6%** |
| **CUT/PUNCH** | 219 | 291 | 132.9% | 177 | **60.8%** | **80.8%** |
| **DEFLECTION/GUIDE** | 184 | 276 | 150.0% | 126 | **45.7%** | **68.5%** |
| **POWER DRIVE** | 115 | 122 | 106.1% | 84 | **68.9%** | **73.0%** |
| **SLOG** | 266 | 390 | 146.6% | 238 | **61.0%** | **89.5%** |
| **SWEEP** | 211 | 371 | 175.8% | 197 | **53.1%** | **93.4%** |
| **OVERALL TOTAL** | **2481** | **3270** | **131.8%** | **2006** | 🏆 **61.3%** | 🏆 **80.9%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 48 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 517 | 539 | 104.3% | 388 | **72.0%** | **75.0%** |
| **DRIVE/DEFENCE** | 627 | 850 | 135.6% | 545 | **64.1%** | **86.9%** |
| **GLANCE/FLICK** | 406 | 525 | 129.3% | 292 | **55.6%** | **71.9%** |
| **CUT/PUNCH** | 219 | 291 | 132.9% | 177 | **60.8%** | **80.8%** |
| **DEFLECTION/GUIDE** | 185 | 282 | 152.4% | 126 | **44.7%** | **68.1%** |
| **POWER DRIVE** | 135 | 128 | 94.8% | 86 | **67.2%** | **63.7%** |
| **SLOG** | 298 | 430 | 144.3% | 257 | **59.8%** | **86.2%** |
| **SWEEP** | 211 | 378 | 179.1% | 197 | **52.1%** | **93.4%** |
| **OVERALL TOTAL** | **2598** | **3423** | **131.8%** | **2068** | 🏆 **60.4%** | 🏆 **79.6%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.5 | 94 | 124 | 94.7% | 71.8% | 81.7%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 1 | 25.0% | 100.0% | 40.0%
| `session_2026-05-31_14-12-10` | Training | 13.0 | 41 | 73 | 95.1% | 53.4% | 68.4%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 78 | 95.1% | 74.4% | 83.5%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 34 | 100.0% | 82.4% | 90.3%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 61 | 100.0% | 83.6% | 91.1%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 65 | 95.6% | 66.2% | 78.2%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 65 | 98.3% | 87.7% | 92.7%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 70 | 100.0% | 72.9% | 84.3%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 70 | 88 | 100.0% | 79.5% | 88.6%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 66 | 88.7% | 83.3% | 85.9%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 74 | 94.2% | 87.8% | 90.9%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 74 | 100.0% | 77.0% | 87.0%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 70 | 100.0% | 74.3% | 85.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 77 | 93.4% | 74.0% | 82.6%
| `session_2026-06-19_12-25-55` | Training | 16.6 | 56 | 68 | 94.6% | 77.9% | 85.5%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 83 | 96.4% | 63.9% | 76.8%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 76 | 96.5% | 72.4% | 82.7%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 70 | 73.7% | 60.0% | 66.1%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 76 | 92.3% | 78.9% | 85.1%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 76 | 98.3% | 76.3% | 85.9%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 51 | 65 | 100.0% | 78.5% | 87.9%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 68 | 96.2% | 73.5% | 83.3%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 82 | 100.0% | 70.7% | 82.9%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 59 | 82 | 96.6% | 69.5% | 80.9%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 74 | 93.9% | 62.2% | 74.8%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 79 | 94.7% | 68.4% | 79.4%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 73 | 96.6% | 76.7% | 85.5%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 74 | 78.8% | 55.4% | 65.1%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 74 | 98.3% | 77.0% | 86.4%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 72 | 92.2% | 65.3% | 76.4%
| `session_2026-07-11_12-51-39` | Training | 17.1 | 55 | 68 | 89.1% | 72.1% | 79.7%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 70 | 100.0% | 80.0% | 88.9%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 85 | 96.7% | 68.2% | 80.0%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 76 | 98.2% | 73.7% | 84.2%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 116 | 92.4% | 52.6% | 67.0%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 37 | 60 | 100.0% | 61.7% | 76.3%
| `session_2026-07-21_12-43-37` | 🌟 HOLDOUT | 18.3 | 56 | 76 | 96.4% | 71.1% | 81.8%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 66 | 94.7% | 81.8% | 87.8%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 52 | 74 | 92.3% | 64.9% | 76.2%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT | 20.6 | 61 | 77 | 98.4% | 77.9% | 87.0%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 69 | 100.0% | 79.7% | 88.7%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 66 | 94.3% | 75.8% | 84.0%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 60 | 90.7% | 65.0% | 75.7%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 77 | 100.0% | 71.4% | 83.3%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 38 | 100.0% | 71.1% | 83.1%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 52 | 100.0% | 94.2% | 97.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 81 | 100.0% | 75.3% | 85.9%
