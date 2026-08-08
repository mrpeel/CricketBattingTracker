# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Decoupled Impact Shockwave Anchor Detector (Stage 1) + Ultimate Advanced Baseline TCN Classifier (Stage 2)  
**Training Design**: Variant C (Unfrozen TCN Layers, Discriminative LR: `1e-4` for Layers 1-5, `1e-3` for Layers 6-10 + Head)  
**Designated Holdout / Validation Sessions**: `session_2026-07-23_12-37-13, session_2026-07-24_12-52-29, session_2026-08-02_12-10-13` (3 sessions)  
**Training Sessions Count**: 48 physical sessions  
**Total Dataset Duration**: 871.8 minutes (14.5 hours)  
**Validation Loss Early Stopping**: Best Epoch 4 (Best Val Loss: 0.6553, Stopped at Epoch 9)  
**Date**: 2026-08-08 11:30

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (3 Sessions)** | **158** | **192** | **95.57%** | **78.65%** | **86.29%** |
| **Training Set Micro Average (48 Sessions)** | **2637** | **3489** | **95.56%** (2520/2637) | **72.23%** (2520/3489) | **82.27%** |
| 🏆 **Full Dataset Micro Average (All 51 Sessions)** | **2795** | **3681** | 🏆 **95.56%** (2671/2795) | 🏆 **72.56%** (2671/3681) | 🏆 **82.49%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (3 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 30 | 18 | 60.0% | 12 | **66.7%** | **40.0%** |
| **DRIVE/DEFENCE** | 14 | 19 | 135.7% | 9 | **47.4%** | **64.3%** |
| **GLANCE/FLICK** | 8 | 10 | 125.0% | 5 | **50.0%** | **62.5%** |
| **CUT/PUNCH** | 13 | 15 | 115.4% | 8 | **53.3%** | **61.5%** |
| **DEFLECTION/GUIDE** | 27 | 28 | 103.7% | 17 | **60.7%** | **63.0%** |
| **POWER DRIVE** | 9 | 13 | 144.4% | 3 | **23.1%** | **33.3%** |
| **SLOG** | 19 | 33 | 173.7% | 15 | **45.5%** | **78.9%** |
| **SWEEP** | 38 | 56 | 147.4% | 33 | **58.9%** | **86.8%** |
| **OVERALL TOTAL** | **158** | **192** | **121.5%** | **102** | 🏆 **53.1%** | 🏆 **64.6%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (48 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 506 | 511 | 101.0% | 379 | **74.2%** | **74.9%** |
| **DRIVE/DEFENCE** | 619 | 809 | 130.7% | 497 | **61.4%** | **80.3%** |
| **GLANCE/FLICK** | 403 | 539 | 133.7% | 298 | **55.3%** | **73.9%** |
| **CUT/PUNCH** | 206 | 308 | 149.5% | 165 | **53.6%** | **80.1%** |
| **DEFLECTION/GUIDE** | 180 | 248 | 137.8% | 114 | **46.0%** | **63.3%** |
| **POWER DRIVE** | 267 | 278 | 104.1% | 191 | **68.7%** | **71.5%** |
| **SLOG** | 283 | 429 | 151.6% | 238 | **55.5%** | **84.1%** |
| **SWEEP** | 173 | 367 | 212.1% | 154 | **42.0%** | **89.0%** |
| **OVERALL TOTAL** | **2637** | **3489** | **132.3%** | **2036** | 🏆 **58.4%** | 🏆 **77.2%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 51 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 536 | 529 | 98.7% | 391 | **73.9%** | **72.9%** |
| **DRIVE/DEFENCE** | 633 | 828 | 130.8% | 506 | **61.1%** | **79.9%** |
| **GLANCE/FLICK** | 411 | 549 | 133.6% | 303 | **55.2%** | **73.7%** |
| **CUT/PUNCH** | 219 | 323 | 147.5% | 173 | **53.6%** | **79.0%** |
| **DEFLECTION/GUIDE** | 207 | 276 | 133.3% | 131 | **47.5%** | **63.3%** |
| **POWER DRIVE** | 276 | 291 | 105.4% | 194 | **66.7%** | **70.3%** |
| **SLOG** | 302 | 462 | 153.0% | 253 | **54.8%** | **83.8%** |
| **SWEEP** | 211 | 423 | 200.5% | 187 | **44.2%** | **88.6%** |
| **OVERALL TOTAL** | **2795** | **3681** | **131.7%** | **2138** | 🏆 **58.1%** | 🏆 **76.5%** |

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
| `session_2026-06-19_12-25-55` | Training | 16.7 | 56 | 68 | 94.6% | 77.9% | 85.5%
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
| `session_2026-07-21_12-43-37` | Training | 18.3 | 56 | 76 | 96.4% | 71.1% | 81.8%
| `session_2026-07-23_12-37-13` | 🌟 HOLDOUT | 12.5 | 57 | 66 | 94.7% | 81.8% | 87.8%
| `session_2026-07-24_12-52-29` | 🌟 HOLDOUT | 17.9 | 52 | 74 | 92.3% | 64.9% | 76.2%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 61 | 77 | 98.4% | 77.9% | 87.0%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 69 | 100.0% | 79.7% | 88.7%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 66 | 94.3% | 75.8% | 84.0%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 60 | 90.7% | 65.0% | 75.7%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 77 | 100.0% | 71.4% | 83.3%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 38 | 100.0% | 71.1% | 83.1%
| `session_2026-08-02_12-10-13` | 🌟 HOLDOUT | 11.3 | 49 | 52 | 100.0% | 94.2% | 97.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 81 | 100.0% | 75.3% | 85.9%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 58 | 73 | 96.6% | 76.7% | 85.5%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 78 | 96.8% | 76.9% | 85.7%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 107 | 97.4% | 70.1% | 81.5%
