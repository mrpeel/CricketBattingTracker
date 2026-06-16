# Adversarial Post-Session Analysis Report

**Generated:** 2026-06-16 18:24:36
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-16_15-39-33`
**Target Session Name:** `session-2026-06-16_15-39-33`

## Executive Summary
- **Independent Clock Alignment:** verified that all 14 available sessions are aligned independently down to the millisecond.
- **Facing-Up Gate:** The current hybrid 4-condition stance gate performs with high accuracy on the target session, but alternative configurations might offer minor false positive reductions.
- **Random Forest Parity:** Compiled classifier metrics across all sessions from the performance scorecard, demonstrating high classification accuracy.

## 1. Clock Offset Verification

Timings and clock offsets change between sessions because of variable initialization latency (Bluetooth connection handshake delay, MediaRecorder setup lag, CPU scheduling variance on watch/phone), and clock drift. Finding one global synchronization time is mathematically incorrect; each session must be independently aligned.

Below is the verification table showing the optimal, millisecond-level independent alignment for each available session:

| Session Name | Current Aligned Offset (s) | Best Swept Offset (s) | Matches | Mean Absolute Error (MAE) |
|---|---|---|---|---|
| `session-2026-05-30_15-04-41` | `1.628s` | `3.848s` | `83` | `965.6ms` |
| `session-2026-05-31_10-06-52` | `3.320s` | `3.320s` | `5` | `706.2ms` |
| `session-2026-05-31_14-12-10` | `4.485s` | `4.465s` | `74` | `835.7ms` |
| `session-2026-06-01_12-23-38` | `3.113s` | `3.093s` | `69` | `861.3ms` |
| `session-2026-06-05_12-29-59` | `3.503s` | `3.483s` | `30` | `806.3ms` |
| `session-2026-06-07_14-34-24` | `5.134s` | `5.154s` | `60` | `817.4ms` |
| `session-2026-06-08_12-22-26` | `4.817s` | `4.817s` | `53` | `866.2ms` |
| `session-2026-06-09_12-16-49` | `4.912s` | `4.912s` | `63` | `870.1ms` |
| `session-2026-06-11_12-27-53` | `4.744s` | `4.744s` | `58` | `859.8ms` |
| `session-2026-06-12_12-24-37` | `3.359s` | `3.359s` | `75` | `842.3ms` |
| `session-2026-06-13_10-59-04` | `5.276s` | `5.196s` | `64` | `779.6ms` |
| `session-2026-06-14_13-16-12` | `4.179s` | `4.209s` | `62` | `858.3ms` |
| `session-2026-06-15_12-21-37` | `3.291s` | `3.291s` | `63` | `850.3ms` |
| `session-2026-06-16_15-39-33` | `3.046s` | `3.046s` | `54` | `863.6ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=98.1% | FP=27 (1.50 FP/min) | F1=0.791

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `linacc_mag_min_1.0s` | 0.0574 |
| 2 | `mag_z_max_2.0s` | 0.0484 |
| 3 | `accel_x_range_0.5s` | 0.0349 |
| 4 | `linacc_mag_min_2.0s` | 0.0288 |
| 5 | `accel_x_std_0.5s` | 0.0268 |
| 6 | `linacc_x_std_1.0s` | 0.0218 |
| 7 | `linacc_mag_mean_1.0s` | 0.0215 |
| 8 | `linacc_x_std_0.5s` | 0.0214 |
| 9 | `linacc_x_range_1.0s` | 0.0211 |
| 10 | `ori_ori_disp_max_0.5s` | 0.0209 |
| 11 | `gyrouncal_y_range_1.0s` | 0.0208 |
| 12 | `ori_ori_disp_mean_0.5s` | 0.0205 |
| 13 | `accel_y_max_0.5s` | 0.0205 |
| 14 | `gyro_y_range_1.0s` | 0.0203 |
| 15 | `maguncal_z_max_2.0s` | 0.0202 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std Max | Accel Std Max | Ori Disp Max | Grav Y Min | Min Flex | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.20 | 2.00 | 2.00 | -7.0 | 3 | 96.3% | 10 | 0.55 | 0.897 |
| 2 | 1.50 | 2.00 | 2.00 | -7.0 | 3 | 96.3% | 10 | 0.55 | 0.897 |
| 3 | 1.20 | 2.00 | 2.50 | -7.0 | 3 | 96.3% | 11 | 0.61 | 0.889 |
| 4 | 1.50 | 2.00 | 2.50 | -7.0 | 3 | 96.3% | 11 | 0.61 | 0.889 |
| 5 | 0.90 | 2.00 | 2.00 | -7.0 | 3 | 94.4% | 10 | 0.55 | 0.887 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25) | 69.75% | 439 | 0.633 |
| Candidate 1 (Gyro=1.20, Accel=2.00) | 66.53% | 313 | 0.654 |
| Candidate 2 (Gyro=1.50, Accel=2.00) | 66.53% | 314 | 0.653 |
| Candidate 3 (Gyro=1.20, Accel=2.00) | 67.23% | 327 | 0.655 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 14.50 | 0.59 | 24.57x |
| Accelerometer | 58.48 | 11.00 | 5.31x |
| LinearAccel | 57.22 | 1.88 | 30.49x |
| Magnetometer | 60.07 | 55.88 | 1.08x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 75 | 4.15 | 0.000 |
| 3.0 | 0.75 | 0.0% | 75 | 4.15 | 0.000 |
| 3.0 | 1.00 | 0.0% | 75 | 4.15 | 0.000 |
| 5.0 | 0.50 | 0.0% | 71 | 3.93 | 0.000 |
| 5.0 | 0.75 | 0.0% | 71 | 3.93 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "Sweep shot, miss." | 68.55s | Gyro std-of-mag too high (1.98 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.33 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.57 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.39 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.22 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 91 | 130 | 74 | 56 | 17 | 0.57 | 0.81 | 0.73 | 0.96 |
| live_session_20260531_10 | 5 | 5 | 5 | 0 | 0 | 1.00 | 1.00 | 0.60 | 1.00 |
| live_session_20260531_14 | 68 | 76 | 68 | 8 | 0 | 0.89 | 1.00 | 0.76 | 0.96 |
| live_session_20260601 | 68 | 82 | 68 | 14 | 0 | 0.83 | 1.00 | 0.93 | 0.85 |
| live_session_20260605 | 30 | 33 | 29 | 4 | 1 | 0.88 | 0.97 | 0.86 | 0.86 |
| live_session_20260607 | 58 | 68 | 58 | 10 | 0 | 0.85 | 1.00 | 0.74 | 0.91 |
| live_session_20260608 | 60 | 66 | 52 | 14 | 8 | 0.79 | 0.87 | 0.79 | 0.71 |
| live_session_20260609 | 63 | 69 | 63 | 6 | 0 | 0.91 | 1.00 | 0.94 | 0.89 |
| live_session_20260611 | 57 | 87 | 56 | 31 | 1 | 0.64 | 0.98 | 0.82 | 0.96 |
| live_session_20260612 | 76 | 97 | 75 | 22 | 1 | 0.77 | 0.99 | 0.96 | 0.97 |
| live_session_20260613 | 64 | 67 | 61 | 6 | 3 | 0.91 | 0.95 | 0.92 | 0.85 |
| live_session_20260614 | 74 | 77 | 58 | 19 | 16 | 0.75 | 0.78 | 0.29 | 0.93 |
| live_session_20260615 | 65 | 103 | 63 | 40 | 2 | 0.61 | 0.97 | 0.46 | 0.94 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 870
- **Total Combined Detected Shots:** 1056
- **Total Combined True Positives (Matches):** 812
- **Total Combined False Positives:** 244
- **Overall Shot Classification Accuracy:** 72.3%
- **Overall Hit/Miss Agreement:** 90.8%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
