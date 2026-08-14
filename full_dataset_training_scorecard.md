# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 AdvancedTCN Classifier)  
**Training Design**: Variant C (Unfrozen TCN Layers, Discriminative LR: `1e-4` for Layers 1-5, `1e-3` for Layers 6-10 + Head, Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `session_2026-07-23_12-37-13, session_2026-08-02_12-10-13, session_2026-08-14_12-24-45` (3 sessions)  
**Training Sessions Count**: 50 physical sessions  
**Total Dataset Duration**: 912.5 minutes (15.2 hours)  
**Validation Loss Early Stopping**: Best Epoch 5 (Best Val Loss: 0.6675, Stopped at Epoch 10)  
**Date**: 2026-08-14 15:25

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (3 Sessions)** | **167** | **167** | **88.02%** (147/167) | **88.02%** (147/167) | **88.02%** |
| **Training Set Micro Average (50 Sessions)** | **2752** | **2562** | **75.22%** (2070/2752) | **80.80%** (2070/2562) | **77.91%** |
| 🏆 **Full Dataset Micro Average (All 53 Sessions)** | **2919** | **2729** | 🏆 **75.95%** (2217/2919) | 🏆 **81.24%** (2217/2729) | 🏆 **78.51%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (3 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 30 | 29 | 96.7% | 17 | **58.6%** | **56.7%** |
| **DRIVE/DEFENCE** | 51 | 46 | 90.2% | 44 | **95.7%** | **86.3%** |
| **GLANCE/FLICK** | 8 | 8 | 100.0% | 3 | **37.5%** | **37.5%** |
| **CUT/PUNCH** | 12 | 8 | 66.7% | 6 | **75.0%** | **50.0%** |
| **DEFLECTION/GUIDE** | 0 | 0 | 0.0% | 0 | **0.0%** | **0.0%** |
| **POWER DRIVE** | 9 | 9 | 100.0% | 5 | **55.6%** | **55.6%** |
| **SLOG** | 19 | 18 | 94.7% | 8 | **44.4%** | **42.1%** |
| **SWEEP** | 38 | 29 | 76.3% | 10 | **34.5%** | **26.3%** |
| **OVERALL TOTAL** | **167** | **147** | **88.0%** | **93** | 🏆 **63.3%** | 🏆 **55.7%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (50 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 506 | 397 | 78.5% | 327 | **82.4%** | **64.6%** |
| **DRIVE/DEFENCE** | 651 | 495 | 76.0% | 383 | **77.4%** | **58.8%** |
| **GLANCE/FLICK** | 403 | 309 | 76.7% | 261 | **84.5%** | **64.8%** |
| **CUT/PUNCH** | 261 | 231 | 88.5% | 212 | **91.8%** | **81.2%** |
| **DEFLECTION/GUIDE** | 207 | 162 | 78.3% | 161 | **99.4%** | **77.8%** |
| **POWER DRIVE** | 268 | 194 | 72.4% | 155 | **79.9%** | **57.8%** |
| **SLOG** | 283 | 208 | 73.5% | 181 | **87.0%** | **64.0%** |
| **SWEEP** | 173 | 74 | 42.8% | 50 | **67.6%** | **28.9%** |
| **OVERALL TOTAL** | **2752** | **2070** | **75.2%** | **1730** | 🏆 **83.6%** | 🏆 **62.9%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 53 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 536 | 426 | 79.5% | 344 | **80.8%** | **64.2%** |
| **DRIVE/DEFENCE** | 702 | 541 | 77.1% | 427 | **78.9%** | **60.8%** |
| **GLANCE/FLICK** | 411 | 317 | 77.1% | 264 | **83.3%** | **64.2%** |
| **CUT/PUNCH** | 273 | 239 | 87.5% | 218 | **91.2%** | **79.9%** |
| **DEFLECTION/GUIDE** | 207 | 162 | 78.3% | 161 | **99.4%** | **77.8%** |
| **POWER DRIVE** | 277 | 203 | 73.3% | 160 | **78.8%** | **57.8%** |
| **SLOG** | 302 | 226 | 74.8% | 189 | **83.6%** | **62.6%** |
| **SWEEP** | 211 | 103 | 48.8% | 60 | **58.3%** | **28.4%** |
| **OVERALL TOTAL** | **2919** | **2217** | **76.0%** | **1823** | 🏆 **82.2%** | 🏆 **62.5%** |

---

## 📋 Session-by-Session Full Dataset Table

| Session Directory | Partition | Duration (min) | Ground-Truth Shots | Total Detections | Recall (%) | Precision (%) | F1 Score (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `session_2026-05-30_15-04-41` | Training | 18.5 | 94 | 15 | 9.6% | 60.0% | 16.5%
| `session_2026-05-31_10-06-52` | Training | 1.1 | 4 | 5 | 0.0% | 0.0% | 0.0%
| `session_2026-05-31_14-12-10` | Training | 13.0 | 41 | 10 | 2.4% | 10.0% | 3.9%
| `session_2026-06-01_12-23-38` | Training | 17.8 | 61 | 62 | 91.8% | 90.3% | 91.1%
| `session_2026-06-05_12-29-59` | Training | 5.3 | 28 | 28 | 92.9% | 92.9% | 92.9%
| `session_2026-06-07_14-34-24` | Training | 11.8 | 51 | 39 | 62.7% | 82.1% | 71.1%
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 14 | 15.6% | 50.0% | 23.7%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 93.1% | 91.5% | 92.3%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 92.2% | 88.7% | 90.4%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 70 | 70 | 94.3% | 94.3% | 94.3%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 88.7% | 91.7% | 90.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 88.4% | 95.3% | 91.7%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 32 | 59.6% | 96.9% | 73.8%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-19_12-25-55` | Training | 16.7 | 56 | 60 | 98.2% | 91.7% | 94.8%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 68 | 96.4% | 77.9% | 86.2%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 61 | 94.7% | 88.5% | 91.5%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 55 | 89.5% | 92.7% | 91.1%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 69 | 93.8% | 88.4% | 91.0%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 62 | 93.2% | 88.7% | 90.9%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 51 | 23 | 43.1% | 95.7% | 59.5%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 33 | 55.8% | 87.9% | 68.2%
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
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 73 | 96.7% | 79.5% | 87.2%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 7 | 10.5% | 85.7% | 18.7%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 59 | 42.4% | 47.5% | 44.8%
| `session_2026-07-20_12-42-16` | Training | 15.3 | 37 | 49 | 97.3% | 73.5% | 83.7%
| `session_2026-07-21_12-43-37` | Training | 18.3 | 56 | 62 | 94.6% | 85.5% | 89.8%
| `session_2026-07-23_12-37-13` | 🌟 HOLDOUT | 12.5 | 57 | 60 | 94.7% | 90.0% | 92.3%
| `session_2026-07-24_12-52-29` | Training | 17.9 | 52 | 57 | 96.2% | 87.7% | 91.7%
| `session_2026-07-25_15-16-32` | Training | 20.6 | 61 | 69 | 95.1% | 84.1% | 89.2%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 62 | 98.2% | 87.1% | 92.3%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 60 | 97.7% | 70.0% | 81.6%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 70.9% | 60.9% | 65.5%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 77.8% | 72.4% | 75.0%
| `session_2026-08-02_12-10-13` | 🌟 HOLDOUT | 11.3 | 49 | 42 | 83.7% | 97.6% | 90.1%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 62 | 95.1% | 93.5% | 94.3%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 59 | 61 | 79.7% | 77.0% | 78.3%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 19.4% | 20.0% | 19.7%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 85 | 93.5% | 84.7% | 88.9%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 65 | 90.3% | 86.2% | 88.2%
| `session_2026-08-14_12-24-45` | 🌟 HOLDOUT | 20.9 | 61 | 65 | 85.2% | 80.0% | 82.5%
