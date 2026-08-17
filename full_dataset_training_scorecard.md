# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 AdvancedTCN Classifier)  
**Training Design**: Variant C (Unfrozen TCN Layers, Discriminative LR: `1e-4` for Layers 1-5, `1e-3` for Layers 6-10 + Head, Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `session_2026-07-23_12-37-13, session_2026-08-02_12-10-13, session_2026-08-14_12-24-45` (3 sessions)  
**Training Sessions Count**: 53 physical sessions  
**Total Dataset Duration**: 965.6 minutes (16.1 hours)  
**Validation Loss Early Stopping**: Best Epoch 4 (Best Val Loss: 0.6679, Stopped at Epoch 9)  
**Date**: 2026-08-17 18:12

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (3 Sessions)** | **167** | **166** | **86.23%** (144/167) | **86.75%** (144/166) | **86.49%** |
| **Training Set Micro Average (53 Sessions)** | **2939** | **2769** | **76.73%** (2255/2939) | **81.44%** (2255/2769) | **79.01%** |
| 🏆 **Full Dataset Micro Average (All 56 Sessions)** | **3106** | **2935** | 🏆 **77.24%** (2399/3106) | 🏆 **81.74%** (2399/2935) | 🏆 **79.42%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (3 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 30 | 27 | 90.0% | 18 | **66.7%** | **60.0%** |
| **DRIVE/DEFENCE** | 51 | 46 | 90.2% | 45 | **97.8%** | **88.2%** |
| **GLANCE/FLICK** | 8 | 8 | 100.0% | 4 | **50.0%** | **50.0%** |
| **CUT/PUNCH** | 12 | 8 | 66.7% | 6 | **75.0%** | **50.0%** |
| **DEFLECTION/GUIDE** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **POWER DRIVE** | 9 | 9 | 100.0% | 1 | **11.1%** | **11.1%** |
| **SLOG** | 19 | 18 | 94.7% | 15 | **83.3%** | **78.9%** |
| **SWEEP** | 38 | 28 | 73.7% | 24 | **85.7%** | **63.2%** |
| **OVERALL TOTAL** | **167** | **144** | **86.2%** | **113** | 🏆 **78.5%** | 🏆 **67.7%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (53 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 528 | 418 | 79.2% | 335 | **80.1%** | **63.4%** |
| **DRIVE/DEFENCE** | 722 | 549 | 76.0% | 445 | **81.1%** | **61.6%** |
| **GLANCE/FLICK** | 465 | 373 | 80.2% | 317 | **85.0%** | **68.2%** |
| **CUT/PUNCH** | 261 | 231 | 88.5% | 211 | **91.3%** | **80.8%** |
| **DEFLECTION/GUIDE** | 207 | 162 | 78.3% | 159 | **98.1%** | **76.8%** |
| **POWER DRIVE** | 268 | 192 | 71.6% | 138 | **71.9%** | **51.5%** |
| **SLOG** | 283 | 208 | 73.5% | 186 | **89.4%** | **65.7%** |
| **SWEEP** | 205 | 122 | 59.5% | 93 | **76.2%** | **45.4%** |
| **OVERALL TOTAL** | **2939** | **2255** | **76.7%** | **1884** | 🏆 **83.5%** | 🏆 **64.1%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 56 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 558 | 445 | 79.7% | 353 | **79.3%** | **63.3%** |
| **DRIVE/DEFENCE** | 773 | 595 | 77.0% | 490 | **82.4%** | **63.4%** |
| **GLANCE/FLICK** | 473 | 381 | 80.5% | 321 | **84.3%** | **67.9%** |
| **CUT/PUNCH** | 273 | 239 | 87.5% | 217 | **90.8%** | **79.5%** |
| **DEFLECTION/GUIDE** | 207 | 162 | 78.3% | 159 | **98.1%** | **76.8%** |
| **POWER DRIVE** | 277 | 201 | 72.6% | 139 | **69.2%** | **50.2%** |
| **SLOG** | 302 | 226 | 74.8% | 201 | **88.9%** | **66.6%** |
| **SWEEP** | 243 | 150 | 61.7% | 117 | **78.0%** | **48.1%** |
| **OVERALL TOTAL** | **3106** | **2399** | **77.2%** | **1997** | 🏆 **83.2%** | 🏆 **64.3%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.5 | 94 | 14 | 9.6% | 64.3% | 16.7%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 5 | 0.0% | 0.0% | 0.0%
| `session_2026-05-31_14-12-10` | Training | 13.0 | 41 | 10 | 2.4% | 10.0% | 3.9%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 62 | 91.8% | 90.3% | 91.1%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 92.9% | 92.9% | 92.9%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 39 | 62.7% | 82.1% | 71.1%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 15 | 15.6% | 46.7% | 23.3%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 93.1% | 91.5% | 92.3%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 92.2% | 88.7% | 90.4%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 70 | 70 | 94.3% | 94.3% | 94.3%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 88.7% | 91.7% | 90.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 88.4% | 95.3% | 91.7%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 37 | 67.3% | 94.6% | 78.7%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-19_12-25-55` | Training | 16.7 | 56 | 59 | 98.2% | 93.2% | 95.7%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 69 | 96.4% | 76.8% | 85.5%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 61 | 94.7% | 88.5% | 91.5%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 55 | 89.5% | 92.7% | 91.1%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 69 | 93.8% | 88.4% | 91.0%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 62 | 93.2% | 88.7% | 90.9%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 51 | 39 | 72.5% | 94.9% | 82.2%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 41 | 69.2% | 87.8% | 77.4%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 66 | 62.1% | 54.5% | 58.1%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 59 | 60 | 98.3% | 96.7% | 97.5%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 63 | 83.7% | 65.1% | 73.2%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 58 | 50.9% | 50.0% | 50.4%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 55 | 89.7% | 94.5% | 92.0%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 61 | 92.3% | 78.7% | 85.0%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 68 | 98.3% | 83.8% | 90.5%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 63 | 100.0% | 81.0% | 89.5%
| `session_2026-07-11_12-51-39` | Training | 17.1 | 55 | 16 | 25.5% | 87.5% | 39.4%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 4 | 3.6% | 50.0% | 6.7%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 74 | 96.7% | 78.4% | 86.6%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 7 | 10.5% | 85.7% | 18.7%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 57 | 40.9% | 47.4% | 43.9%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 37 | 51 | 100.0% | 72.5% | 84.1%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 56 | 63 | 94.6% | 84.1% | 89.1%
| `session_2026-07-23_12-37-13` | 🌟 HOLDOUT | 12.5 | 57 | 58 | 91.2% | 89.7% | 90.4%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 52 | 58 | 96.2% | 86.2% | 90.9%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 61 | 69 | 95.1% | 84.1% | 89.2%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 60 | 98.2% | 90.0% | 93.9%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 62 | 97.7% | 67.7% | 80.0%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 70.9% | 60.9% | 65.5%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 77.8% | 72.4% | 75.0%
| `session_2026-08-02_12-10-13` | 🌟 HOLDOUT | 11.3 | 49 | 43 | 81.6% | 93.0% | 87.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 59 | 91.8% | 94.9% | 93.3%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 59 | 60 | 79.7% | 78.3% | 79.0%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 19.4% | 20.0% | 19.7%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 84 | 93.5% | 85.7% | 89.4%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 65 | 90.3% | 86.2% | 88.2%
| `session_2026-08-14_12-24-45` | 🌟 HOLDOUT | 20.9 | 61 | 65 | 85.2% | 80.0% | 82.5%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 69 | 79.5% | 84.1% | 81.7%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 46 | 88.0% | 95.7% | 91.7%
| `session_2026-08-17_12-51-22` | Training | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
