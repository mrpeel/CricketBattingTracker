# Full Dataset Training & Holdout Scorecard Report

**System Architecture**: Hierarchical Multi-Tier Stance-Gated TCN Pipeline (Stage 1 Facing Up Stance Detector + Stage 2 Bat-Plane 3-Family Multi-Scale TCN)  
**Training Design**: Dynamic Shuffling & Staged Slow-Rate Fine-Tuning (Phase 1: Epochs 1-8 Joint Warmup; Phase 2: Epochs 9-35 Discriminative LR L1-7 (3e-5) + Upper CosineAnnealingLR (5e-4 to 1e-6) + 2.0x Head 2A Weight on POWER DRIVE, Label Smoothing = 0.1)  
**Designated Holdout / Validation Sessions**: `session_2026-07-20_12-42-16, session_2026-07-21_12-43-37, session_2026-07-24_12-52-29, session_2026-07-25_15-16-32` (4 sessions)  
**Training Sessions Count**: 58 physical sessions  
**Total Dataset Duration**: 1078.4 minutes (18.0 hours)  
**Holdout Macro-F1 Checkpointing**: Best Epoch 13 (Best Macro-F1: 0.7182, Candidate Acc: 70.87%, Val Loss: 1.1012, Stopped at Epoch 31)  
**Date**: 2026-08-27 22:22

---

## 📊 Summary Scorecard Metrics

| Dataset Partition | Physical Ground-Truth Shots | Total Detections | **Physical Shot Recall** | **Precision** | **F1 Score** |
|---|:---:|:---:|:---:|:---:|:---:|
| 🌟 **Holdout Set (4 Sessions)** | **206** | **241** | **96.12%** (198/206) | **82.16%** (198/241) | **88.59%** |
| **Training Set Micro Average (58 Sessions)** | **3276** | **3190** | **78.39%** (2568/3276) | **80.50%** (2568/3190) | **79.43%** |
| 🏆 **Full Dataset Micro Average (All 62 Sessions)** | **3482** | **3431** | 🏆 **79.44%** (2766/3482) | 🏆 **80.62%** (2766/3431) | 🏆 **80.02%** |

---

## 🎯 Per-Shot Class Classification Accuracy Breakdown

### 🌟 Holdout Set Per-Shot Accuracy (4 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 57 | 55 | 96.5% | 34 | **61.8%** | **59.6%** |
| **DRIVE/DEFENCE** | 30 | 29 | 96.7% | 22 | **75.9%** | **73.3%** |
| **GLANCE/FLICK** | 27 | 26 | 96.3% | 18 | **69.2%** | **66.7%** |
| **CUT/PUNCH** | 13 | 12 | 92.3% | 11 | **91.7%** | **84.6%** |
| **DEFLECTION/GUIDE** | 28 | 26 | 92.9% | 26 | **100.0%** | **92.9%** |
| **POWER DRIVE** | 20 | 19 | 95.0% | 7 | **36.8%** | **35.0%** |
| **SWEEP** | 31 | 31 | 100.0% | 31 | **100.0%** | **100.0%** |
| **OVERALL TOTAL** | **206** | **198** | **96.1%** | **149** | 🏆 **75.3%** | 🏆 **72.3%** |

### 🏋️ Training Set Per-Shot Accuracy Breakdown (58 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 939 | 717 | 76.4% | 649 | **90.5%** | **69.1%** |
| **DRIVE/DEFENCE** | 847 | 660 | 77.9% | 606 | **91.8%** | **71.5%** |
| **GLANCE/FLICK** | 519 | 402 | 77.5% | 356 | **88.6%** | **68.6%** |
| **CUT/PUNCH** | 289 | 253 | 87.5% | 234 | **92.5%** | **81.0%** |
| **DEFLECTION/GUIDE** | 213 | 169 | 79.3% | 167 | **98.8%** | **78.4%** |
| **POWER DRIVE** | 257 | 184 | 71.6% | 170 | **92.4%** | **66.1%** |
| **SWEEP** | 212 | 183 | 86.3% | 168 | **91.8%** | **79.2%** |
| **OVERALL TOTAL** | **3276** | **2568** | **78.4%** | **2350** | 🏆 **91.5%** | 🏆 **71.7%** |

### 🏆 Full Dataset Per-Shot Accuracy Breakdown (All 62 Sessions)
| Shot Class | Physical GT Shots | Shots Detected | **Detection Recall (%)** | **Correctly Classified Shots** | **Classification Accuracy (%)** | **Total Coverage Rate (%)** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 996 | 772 | 77.5% | 683 | **88.5%** | **68.6%** |
| **DRIVE/DEFENCE** | 877 | 689 | 78.6% | 628 | **91.1%** | **71.6%** |
| **GLANCE/FLICK** | 546 | 428 | 78.4% | 374 | **87.4%** | **68.5%** |
| **CUT/PUNCH** | 302 | 265 | 87.7% | 245 | **92.5%** | **81.1%** |
| **DEFLECTION/GUIDE** | 241 | 195 | 80.9% | 193 | **99.0%** | **80.1%** |
| **POWER DRIVE** | 277 | 203 | 73.3% | 177 | **87.2%** | **63.9%** |
| **SWEEP** | 243 | 214 | 88.1% | 199 | **93.0%** | **81.9%** |
| **OVERALL TOTAL** | **3482** | **2766** | **79.4%** | **2499** | 🏆 **90.3%** | 🏆 **71.8%** |

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
| `session_2026-06-08_12-22-26` | Training | 11.9 | 45 | 37 | 55.6% | 67.6% | 61.0%
| `session_2026-06-09_12-16-49` | Training | 12.5 | 58 | 59 | 93.1% | 91.5% | 92.3%
| `session_2026-06-11_12-27-53` | Training | 16.4 | 51 | 53 | 92.2% | 88.7% | 90.4%
| `session_2026-06-12_12-24-37` | Training | 20.9 | 70 | 70 | 94.3% | 94.3% | 94.3%
| `session_2026-06-13_10-59-04` | Training | 12.9 | 62 | 60 | 88.7% | 91.7% | 90.2%
| `session_2026-06-14_13-16-12` | Training | 15.6 | 69 | 64 | 88.4% | 95.3% | 91.7%
| `session_2026-06-15_12-21-37` | Training | 21.2 | 57 | 62 | 100.0% | 91.9% | 95.8%
| `session_2026-06-16_15-39-33` | Training | 16.5 | 52 | 54 | 98.1% | 94.4% | 96.2%
| `session_2026-06-18_12-23-09` | Training | 18.7 | 61 | 62 | 98.4% | 96.8% | 97.6%
| `session_2026-06-19_12-25-55` | Training | 16.7 | 56 | 60 | 98.2% | 91.7% | 94.8%
| `session_2026-06-21_13-53-17` | Training | 20.2 | 55 | 69 | 96.4% | 76.8% | 85.5%
| `session_2026-06-22_12-27-26` | Training | 20.1 | 57 | 61 | 94.7% | 88.5% | 91.5%
| `session_2026-06-23_12-24-48` | Training | 18.2 | 57 | 55 | 89.5% | 92.7% | 91.1%
| `session_2026-06-25_12-25-07` | Training | 21.2 | 65 | 69 | 93.8% | 88.4% | 91.0%
| `session_2026-06-26_12-22-13` | Training | 18.7 | 59 | 62 | 93.2% | 88.7% | 90.9%
| `session_2026-06-27_14-12-40` | Training | 17.6 | 51 | 53 | 100.0% | 96.2% | 98.1%
| `session_2026-06-28_11-28-09` | Training | 19.8 | 52 | 56 | 96.2% | 89.3% | 92.6%
| `session_2026-06-29_12-21-45` | Training | 18.1 | 58 | 66 | 62.1% | 54.5% | 58.1%
| `session_2026-07-02_12-38-53` | Training | 20.9 | 59 | 59 | 98.3% | 98.3% | 98.3%
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
| `session_2026-07-18_13-44-09` | Training | 21.3 | 66 | 60 | 43.9% | 48.3% | 46.0%
| `session_2026-07-20_12-42-16` | 🌟 HOLDOUT | 15.3 | 37 | 51 | 100.0% | 72.5% | 84.1%
| `session_2026-07-21_12-43-37` | 🌟 HOLDOUT | 18.3 | 56 | 63 | 94.6% | 84.1% | 89.1%
| `session_2026-07-23_12-37-13` | Training | 12.5 | 57 | 60 | 94.7% | 90.0% | 92.3%
| `session_2026-07-24_12-52-29` | 🌟 HOLDOUT | 17.9 | 52 | 58 | 96.2% | 86.2% | 90.9%
| `session_2026-07-25_15-16-32` | 🌟 HOLDOUT | 20.6 | 61 | 69 | 95.1% | 84.1% | 89.2%
| `session_2026-07-26_11-44-54` | Training | 15.1 | 55 | 62 | 98.2% | 87.1% | 92.3%
| `session_2026-07-27_12-47-20` | Training | 18.1 | 53 | 58 | 94.3% | 86.2% | 90.1%
| `session_2026-07-28_12-43-23` | Training | 16.0 | 43 | 62 | 97.7% | 67.7% | 80.0%
| `session_2026-07-31_12-44-46` | Training | 17.2 | 55 | 64 | 70.9% | 60.9% | 65.5%
| `session_2026-08-01_10-18-20` | Training | 8.9 | 27 | 29 | 77.8% | 72.4% | 75.0%
| `session_2026-08-02_12-10-13` | Training | 11.3 | 49 | 52 | 100.0% | 94.2% | 97.0%
| `session_2026-08-03_12-47-55` | Training | 18.3 | 61 | 62 | 95.1% | 93.5% | 94.3%
| `session_2026-08-06_12-51-06` | Training | 17.0 | 59 | 61 | 79.7% | 77.0% | 78.3%
| `session_2026-08-07_12-47-38` | Training | 21.4 | 62 | 60 | 19.4% | 20.0% | 19.7%
| `session_2026-08-08_10-43-42` | Training | 29.8 | 77 | 85 | 93.5% | 84.7% | 88.9%
| `session_2026-08-11_12-49-31` | Training | 19.8 | 62 | 65 | 90.3% | 86.2% | 88.2%
| `session_2026-08-14_12-24-45` | Training | 20.9 | 61 | 65 | 85.2% | 80.0% | 82.5%
| `session_2026-08-15_11-00-15` | Training | 22.1 | 73 | 69 | 79.5% | 84.1% | 81.7%
| `session_2026-08-16_14-10-23` | Training | 11.8 | 50 | 51 | 98.0% | 96.1% | 97.0%
| `session_2026-08-17_12-51-22` | Training | 19.2 | 64 | 65 | 92.2% | 90.8% | 91.5%
| `session_2026-08-20_12-57-09` | Training | 18.9 | 66 | 70 | 53.0% | 50.0% | 51.5%
| `session_2026-08-21_12-50-53` | Training | 21.0 | 69 | 71 | 88.4% | 85.9% | 87.1%
| `session_2026-08-22_14-25-31` | Training | 12.0 | 51 | 59 | 92.2% | 79.7% | 85.5%
| `session_2026-08-24_12-41-37` | Training | 19.7 | 67 | 68 | 94.0% | 92.6% | 93.3%
| `session_2026-08-26_12-46-51` | Training | 21.8 | 65 | 67 | 90.8% | 88.1% | 89.4%
| `session_2026-08-27_12-52-32` | Training | 19.4 | 58 | 66 | 34.5% | 30.3% | 32.3%
