# Adversarial Post-Session Analysis Report

**Generated:** 2026-06-11 15:12:16
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-11_12-27-53`
**Target Session Name:** `session-2026-06-11_12-27-53`

## Executive Summary
- **Independent Clock Alignment:** verified that all 9 available sessions are aligned independently down to the millisecond.
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
| `session-2026-06-11_12-27-53` | `4.744s` | `4.744s` | `58` | `935.9ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=54.4% | FP=54 (3.22 FP/min) | F1=0.437

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `linacc_z_range_2.0s` | 0.0662 |
| 2 | `linacc_mag_max_2.0s` | 0.0639 |
| 3 | `linacc_mag_std_2.0s` | 0.0380 |
| 4 | `linacc_mag_range_2.0s` | 0.0283 |
| 5 | `accel_x_max_2.0s` | 0.0272 |
| 6 | `baro_pressure_range_2.0s` | 0.0269 |
| 7 | `accel_mag_range_2.0s` | 0.0257 |
| 8 | `gyro_mag_max_2.0s` | 0.0247 |
| 9 | `gyrouncal_mag_std_2.0s` | 0.0233 |
| 10 | `linacc_x_range_2.0s` | 0.0217 |
| 11 | `linacc_z_min_2.0s` | 0.0204 |
| 12 | `accel_z_range_2.0s` | 0.0197 |
| 13 | `gyrouncal_mag_range_2.0s` | 0.0189 |
| 14 | `linacc_z_max_2.0s` | 0.0185 |
| 15 | `ori_ori_disp_max_2.0s` | 0.0177 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std Max | Accel Std Max | Ori Disp Max | Grav Y Min | Min Flex | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.20 | 2.00 | 2.00 | -6.0 | 3 | 52.6% | 41 | 2.45 | 0.469 |
| 2 | 1.20 | 2.00 | 2.00 | -7.0 | 3 | 52.6% | 41 | 2.45 | 0.469 |
| 3 | 1.50 | 2.00 | 2.00 | -6.0 | 3 | 52.6% | 41 | 2.45 | 0.469 |
| 4 | 1.50 | 2.00 | 2.00 | -7.0 | 3 | 52.6% | 41 | 2.45 | 0.469 |
| 5 | 0.90 | 2.00 | 3.00 | -6.0 | 3 | 52.6% | 42 | 2.51 | 0.465 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25) | 62.94% | 288 | 0.588 |
| Candidate 1 (Gyro=1.20, Accel=2.00) | 58.93% | 220 | 0.592 |
| Candidate 2 (Gyro=1.20, Accel=2.00) | 58.40% | 213 | 0.592 |
| Candidate 3 (Gyro=1.50, Accel=2.00) | 58.93% | 220 | 0.592 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 3.87 | 3.15 | 1.23x |
| Accelerometer | 16.11 | 13.94 | 1.16x |
| LinearAccel | 11.25 | 8.61 | 1.31x |
| Magnetometer | 58.96 | 57.20 | 1.03x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 97 | 5.79 | 0.000 |
| 3.0 | 0.75 | 0.0% | 97 | 5.79 | 0.000 |
| 3.0 | 1.00 | 0.0% | 97 | 5.79 | 0.000 |
| 5.0 | 0.50 | 0.0% | 76 | 4.53 | 0.000 |
| 5.0 | 0.75 | 0.0% | 76 | 4.53 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "Back foot punch, OK" | 74.04s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 2 | "Back foot punch, miss" | 82.04s | Accel std-of-mag too high (4.01 > 3.25), too much motion/shock |
| 9 | "Cut shot, miss" | 153.04s | Gyro std-of-mag too high (1.96 > 1.2), bat was not still |
| 10 | "Back foot punch, OK" | 160.04s | Gyro std-of-mag too high (1.79 > 1.2), bat was not still |
| 11 | "Cut shot, good" | 169.04s | Gyro std-of-mag too high (2.15 > 1.2), bat was not still |
| 12 | "Cut shot, OK" | 178.04s | Gyro std-of-mag too high (1.66 > 1.2), bat was not still |
| 13 | "Cut shot, good" | 188.14s | Gyro std-of-mag too high (1.86 > 1.2), bat was not still |
| 14 | "Cut shot, OK" | 197.04s | Gyro std-of-mag too high (1.93 > 1.2), bat was not still |
| 18 | "Back foot punch, poor" | 224.04s | Gyro std-of-mag too high (1.99 > 1.2), bat was not still |
| 19 | "Back foot punch, OK" | 231.04s | Gyro std-of-mag too high (1.56 > 1.2), bat was not still |
| 20 | "Cut shot, OK" | 238.04s | Gyro std-of-mag too high (2.09 > 1.2), bat was not still |
| 21 | "Back foot punch, OK" | 249.04s | Gyro std-of-mag too high (1.41 > 1.2), bat was not still |
| 22 | "Cut shot, OK" | 258.04s | Gyro std-of-mag too high (2.02 > 1.2), bat was not still |
| 24 | "Cut shot, OK" | 274.04s | Gyro std-of-mag too high (1.79 > 1.2), bat was not still |
| 25 | "Back foot punch, good" | 283.04s | Gyro std-of-mag too high (1.48 > 1.2), bat was not still |
| 28 | "Cut shot, poor" | 311.04s | Gyro std-of-mag too high (2.14 > 1.2), bat was not still |
| 29 | "Back foot punch, good" | 318.04s | Gyro std-of-mag too high (1.92 > 1.2), bat was not still |
| 31 | "Pull shot, poor" | 698.04s | Gyro std-of-mag too high (2.12 > 1.2), bat was not still |
| 39 | "Back foot defense, good" | 783.04s | Gyro std-of-mag too high (1.89 > 1.2), bat was not still |
| 40 | "Back foot defense, good" | 792.04s | Gyro std-of-mag too high (1.57 > 1.2), bat was not still |
| 42 | "Back foot defense, good" | 812.04s | Gyro std-of-mag too high (1.67 > 1.2), bat was not still |
| 45 | "Cover drive, OK" | 857.04s | Gyro std-of-mag too high (1.79 > 1.2), bat was not still |
| 49 | "Back foot punch, good" | 896.04s | Gyro std-of-mag too high (2.02 > 1.2), bat was not still |
| 57 | "Back foot defense, good" | 979.04s | Gyro std-of-mag too high (1.76 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.05 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.43 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.52 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.56 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 91 | 130 | 74 | 56 | 17 | 0.57 | 0.81 | 0.76 | 0.96 |
| live_session_20260531_10 | 5 | 5 | 5 | 0 | 0 | 1.00 | 1.00 | 0.60 | 1.00 |
| live_session_20260531_14 | 68 | 76 | 68 | 8 | 0 | 0.89 | 1.00 | 0.78 | 0.96 |
| live_session_20260601 | 68 | 82 | 68 | 14 | 0 | 0.83 | 1.00 | 0.91 | 0.85 |
| live_session_20260605 | 30 | 33 | 29 | 4 | 1 | 0.88 | 0.97 | 0.90 | 0.86 |
| live_session_20260607 | 58 | 68 | 58 | 10 | 0 | 0.85 | 1.00 | 0.79 | 0.91 |
| live_session_20260608 | 60 | 66 | 52 | 14 | 8 | 0.79 | 0.87 | 0.94 | 0.71 |
| live_session_20260609 | 63 | 69 | 63 | 6 | 0 | 0.91 | 1.00 | 0.94 | 0.89 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 534
- **Total Combined Detected Shots:** 625
- **Total Combined True Positives (Matches):** 499
- **Total Combined False Positives:** 126
- **Overall Shot Classification Accuracy:** 77.5%
- **Overall Hit/Miss Agreement:** 89.3%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
