# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 AdvancedTCN Classifier)  
**Training Design**: Variant C (Harmonized LR: `3e-4` for Layers 1-5, `1e-3` for Layers 6-10 + Head, 3-Epoch Warmup, Holdout Macro-F1 Checkpointing, Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Training Sessions Count**: 54 physical sessions  
**Total Dataset Duration**: 1005.5 minutes (16.8 hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch 12 (Best Macro-F1: 0.6423, Shot Acc: 66.02%, Val Loss: 0.6276, Stopped at Epoch 22)  
**Date**: 2026-08-21 20:03

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (4 Sessions)** | **206** | **230** | **92.23%** (190/206) | **82.61%** (190/230) | **87.16%** |
| **Training Set Micro Average (54 Sessions)** | **3035** | **2832** | **75.88%** (2303/3035) | **81.32%** (2303/2832) | **78.51%** |
| 🏆 **Full Dataset Micro Average (All 58 Sessions)** | **3241** | **3062** | 🏆 **76.92%** (2493/3241) | 🏆 **81.42%** (2493/3062) | 🏆 **79.11%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (4 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 25 | 23 | 92.0% | 9 | **39.1%** | **36.0%** |
| **DRIVE/DEFENCE** | 30 | 29 | 96.7% | 22 | **75.9%** | **73.3%** |
| **GLANCE/FLICK** | 27 | 26 | 96.3% | 19 | **73.1%** | **70.4%** |
| **CUT/PUNCH** | 13 | 12 | 92.3% | 10 | **83.3%** | **76.9%** |
| **DEFLECTION/GUIDE** | 28 | 26 | 92.9% | 26 | **100.0%** | **92.9%** |
| **POWER DRIVE** | 20 | 17 | 85.0% | 6 | **35.3%** | **30.0%** |
| **SLOG** | 32 | 32 | 100.0% | 12 | **37.5%** | **37.5%** |
| **SWEEP** | 31 | 25 | 80.6% | 22 | **88.0%** | **71.0%** |
| **OVERALL TOTAL** | **206** | **190** | **92.2%** | **126** | 🏆 **66.3%** | 🏆 **61.2%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (54 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 584 | 448 | 76.7% | 382 | **85.3%** | **65.4%** |
| **DRIVE/DEFENCE** | 785 | 599 | 76.3% | 486 | **81.1%** | **61.9%** |
| **GLANCE/FLICK** | 455 | 363 | 79.8% | 312 | **86.0%** | **68.6%** |
| **CUT/PUNCH** | 269 | 236 | 87.7% | 219 | **92.8%** | **81.4%** |
| **DEFLECTION/GUIDE** | 203 | 159 | 78.3% | 158 | **99.4%** | **77.8%** |
| **POWER DRIVE** | 257 | 184 | 71.6% | 163 | **88.6%** | **63.4%** |
| **SLOG** | 270 | 194 | 71.9% | 159 | **82.0%** | **58.9%** |
| **SWEEP** | 212 | 120 | 56.6% | 102 | **85.0%** | **48.1%** |
| **OVERALL TOTAL** | **3035** | **2303** | **75.9%** | **1981** | 🏆 **86.0%** | 🏆 **65.3%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 58 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK** | 609 | 471 | 77.3% | 391 | **83.0%** | **64.2%** |
| **DRIVE/DEFENCE** | 815 | 628 | 77.1% | 508 | **80.9%** | **62.3%** |
| **GLANCE/FLICK** | 482 | 389 | 80.7% | 331 | **85.1%** | **68.7%** |
| **CUT/PUNCH** | 282 | 248 | 87.9% | 229 | **92.3%** | **81.2%** |
| **DEFLECTION/GUIDE** | 231 | 185 | 80.1% | 184 | **99.5%** | **79.7%** |
| **POWER DRIVE** | 277 | 201 | 72.6% | 169 | **84.1%** | **61.0%** |
| **SLOG** | 302 | 226 | 74.8% | 171 | **75.7%** | **56.6%** |
| **SWEEP** | 243 | 145 | 59.7% | 124 | **85.5%** | **51.0%** |
| **OVERALL TOTAL** | **3241** | **2493** | **76.9%** | **2107** | 🏆 **84.5%** | 🏆 **65.0%** |

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
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 8 | 8.9% | 50.0% | 15.1%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 93.1% | 91.5% | 92.3%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 92.2% | 88.7% | 90.4%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 70 | 70 | 94.3% | 94.3% | 94.3%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 88.7% | 91.7% | 90.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 88.4% | 95.3% | 91.7%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 29 | 50.0% | 89.7% | 64.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-19_12-25-55` | Training | 16.7 | 56 | 60 | 98.2% | 91.7% | 94.8%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 69 | 96.4% | 76.8% | 85.5%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 61 | 94.7% | 88.5% | 91.5%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 55 | 89.5% | 92.7% | 91.1%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 69 | 93.8% | 88.4% | 91.0%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 61 | 91.5% | 88.5% | 90.0%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 51 | 46 | 88.2% | 97.8% | 92.8%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 45 | 78.8% | 91.1% | 84.5%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 65 | 62.1% | 55.4% | 58.5%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 59 | 60 | 98.3% | 96.7% | 97.5%
| `session_2026-07-04_12-19-20` | Training | 20.1 | 49 | 63 | 83.7% | 65.1% | 73.2%
| `session_2026-07-05_16-27-16` | Training | 18.5 | 57 | 58 | 50.9% | 50.0% | 50.4%
| `session_2026-07-06_12-25-05` | Training | 17.8 | 58 | 55 | 89.7% | 94.5% | 92.0%
| `session_2026-07-07_15-10-50` | Training | 21.9 | 52 | 60 | 92.3% | 80.0% | 85.7%
| `session_2026-07-09_12-19-05` | Training | 19.4 | 58 | 68 | 98.3% | 83.8% | 90.5%
| `session_2026-07-10_12-30-15` | Training | 18.7 | 51 | 63 | 100.0% | 81.0% | 89.5%
| `session_2026-07-11_12-51-39` | Training | 17.1 | 55 | 16 | 25.5% | 87.5% | 39.4%
| `session_2026-07-12_11-23-59` | Training | 13.1 | 56 | 4 | 3.6% | 50.0% | 6.7%
| `session_2026-07-13_12-17-57` | Training | 21.5 | 60 | 71 | 96.7% | 81.7% | 88.5%
| `session_2026-07-17_12-30-41` | Training | 19.4 | 57 | 7 | 10.5% | 85.7% | 18.7%
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 58 | 42.4% | 48.3% | 45.2%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT | 15.3 | 37 | 43 | 83.8% | 72.1% | 77.5%
| `session_2026-07-21_12-43-37` | 🌟 HOLDOUT | 18.3 | 56 | 63 | 94.6% | 84.1% | 89.1%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 94.7% | 90.0% | 92.3%
| `session_2026-07-24_12-52-29` | 🌟 HOLDOUT | 17.9 | 52 | 58 | 96.2% | 86.2% | 90.9%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT | 20.6 | 61 | 66 | 91.8% | 84.8% | 88.2%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 61 | 98.2% | 88.5% | 93.1%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 61 | 97.7% | 68.9% | 80.8%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 70.9% | 60.9% | 65.5%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 77.8% | 72.4% | 75.0%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 51 | 98.0% | 94.1% | 96.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 62 | 95.1% | 93.5% | 94.3%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 59 | 61 | 79.7% | 77.0% | 78.3%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 19.4% | 20.0% | 19.7%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 85 | 93.5% | 84.7% | 88.9%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 64 | 90.3% | 87.5% | 88.9%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 65 | 85.2% | 80.0% | 82.5%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 69 | 79.5% | 84.1% | 81.7%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 37 | 74.0% | 100.0% | 85.1%
| `session_2026-08-17_12-51-22` | Training | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 70 | 53.0% | 50.0% | 51.5%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 71 | 88.4% | 85.9% | 87.1%
