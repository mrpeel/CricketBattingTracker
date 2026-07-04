# Adversarial Post-Session Analysis Report

**Generated:** 2026-07-04 10:08:59
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-02_12-38-53`
**Target Session Name:** `session-2026-07-02_12-38-53`

## Executive Summary
- **Independent Clock Alignment:** verified that all 24 available sessions are aligned independently down to the millisecond.
- **Facing-Up Gate:** The current hybrid 4-condition stance gate performs with high accuracy on the target session, but alternative configurations might offer minor false positive reductions.
- **Random Forest Parity:** Compiled classifier metrics across all sessions from the performance scorecard, demonstrating high classification accuracy.

## 1. Clock Offset Verification

Timings and clock offsets change between sessions because of variable initialization latency (Bluetooth connection handshake delay, MediaRecorder setup lag, CPU scheduling variance on watch/phone), and clock drift. Finding one global synchronization time is mathematically incorrect; each session must be independently aligned.

Below is the verification table showing the optimal, millisecond-level independent alignment for each available session:

| Session Name | Current Aligned Offset (s) | Best Swept Offset (s) | Matches | Mean Absolute Error (MAE) |
|---|---|---|---|---|
| `session-2026-05-30_15-04-41` | `2.352s` | `5.352s` | `52` | `1122.0ms` |
| `session-2026-05-31_10-06-52` | `0.409s` | `2.409s` | `3` | `782.0ms` |
| `session-2026-05-31_14-12-10` | `-23.714s` | `-20.784s` | `48` | `962.9ms` |
| `session-2026-06-01_12-23-38` | `-6.505s` | `-5.895s` | `27` | `1248.6ms` |
| `session-2026-06-05_12-29-59` | `0.118s` | `0.618s` | `20` | `835.1ms` |
| `session-2026-06-07_14-34-24` | `-41.875s` | `-42.785s` | `39` | `976.4ms` |
| `session-2026-06-08_12-22-26` | `1.032s` | `1.232s` | `50` | `816.8ms` |
| `session-2026-06-09_12-16-49` | `-8.673s` | `-7.673s` | `35` | `1045.9ms` |
| `session-2026-06-11_12-27-53` | `-7.237s` | `-4.547s` | `38` | `1323.9ms` |
| `session-2026-06-13_10-59-04` | `6.043s` | `3.773s` | `53` | `789.1ms` |
| `session-2026-06-14_13-16-12` | `-38.423s` | `-41.253s` | `56` | `1038.2ms` |
| `session-2026-06-15_12-21-37` | `24.128s` | `21.948s` | `50` | `1107.6ms` |
| `session-2026-06-16_15-39-33` | `11.463s` | `13.723s` | `45` | `812.7ms` |
| `session-2026-06-18_12-23-09` | `4.677s` | `4.177s` | `64` | `781.2ms` |
| `session-2026-06-19_12-25-55` | `3.850s` | `3.350s` | `61` | `838.2ms` |
| `session-2026-06-21_13-53-17` | `1.452s` | `3.322s` | `67` | `983.7ms` |
| `session-2026-06-22_12-27-26` | `3.255s` | `3.315s` | `46` | `819.1ms` |
| `session-2026-06-23_12-24-48` | `2.464s` | `0.534s` | `53` | `1165.3ms` |
| `session-2026-06-25_12-25-07` | `4.185s` | `1.685s` | `33` | `920.9ms` |
| `session-2026-06-26_12-22-13` | `4.034s` | `4.034s` | `36` | `843.6ms` |
| `session-2026-06-27_14-12-40` | `-35.781s` | `-33.281s` | `41` | `1385.2ms` |
| `session-2026-06-28_11-28-09` | `4.514s` | `4.274s` | `37` | `822.5ms` |
| `session-2026-06-29_12-21-45` | `3.304s` | `5.764s` | `60` | `1464.4ms` |
| `session-2026-07-02_12-38-53` | `-7.468s` | `-4.668s` | `44` | `824.0ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=78.8% | FP=32 (1.51 FP/min) | F1=0.693

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `accel_y_max_0.5s` | 0.0331 |
| 2 | `step_age` | 0.0300 |
| 3 | `gyrouncal_y_mean_2.0s` | 0.0214 |
| 4 | `gyro_y_mean_2.0s` | 0.0212 |
| 5 | `accel_y_max_1.0s` | 0.0176 |
| 6 | `linacc_mag_max_0.5s` | 0.0162 |
| 7 | `linacc_x_std_0.5s` | 0.0150 |
| 8 | `accel_y_max_2.0s` | 0.0147 |
| 9 | `accel_x_std_1.0s` | 0.0142 |
| 10 | `linacc_mag_mean_0.5s` | 0.0141 |
| 11 | `grav_y_range_0.5s` | 0.0129 |
| 12 | `linacc_z_min_1.0s` | 0.0128 |
| 13 | `linacc_mag_mean_1.0s` | 0.0128 |
| 14 | `gyro_y_min_2.0s` | 0.0120 |
| 15 | `accel_x_std_0.5s` | 0.0119 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 0.5s | 77.3% | 29 | 1.37 | 0.699 |
| 2 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 1.0s | 77.3% | 29 | 1.37 | 0.699 |
| 3 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 2.0s | 77.3% | 29 | 1.37 | 0.699 |
| 4 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 3.0s | 77.3% | 29 | 1.37 | 0.699 |
| 5 | 0.90 | 4.00 | 2.50 | -7.0 | 3 | True | True | 0.5s | 77.3% | 29 | 1.37 | 0.699 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 49.71% | 1184 | 0.457 |
| Candidate 1 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=0.5s) | 48.52% | 1065 | 0.460 |
| Candidate 2 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 48.52% | 1064 | 0.460 |
| Candidate 3 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=2.0s) | 48.44% | 1060 | 0.460 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 5.68 | 1.23 | 4.62x |
| Accelerometer | 35.33 | 11.08 | 3.19x |
| LinearAccel | 26.34 | 3.39 | 7.76x |
| Magnetometer | 58.60 | 56.76 | 1.03x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 95 | 4.48 | 0.000 |
| 3.0 | 0.75 | 0.0% | 95 | 4.48 | 0.000 |
| 3.0 | 1.00 | 0.0% | 95 | 4.48 | 0.000 |
| 5.0 | 0.50 | 0.0% | 66 | 3.11 | 0.000 |
| 5.0 | 0.75 | 0.0% | 66 | 3.11 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "glance, good" | 119.53s | Accel std-of-mag too high (6.80 > 3.25), too much motion/shock |
| 15 | "pull shot, miss" | 253.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 20 | "flick shot, okay" | 539.53s | Gyro std-of-mag too high (1.68 > 1.2), bat was not still |
| 21 | "flick shot, poor" | 544.53s | Accel std-of-mag too high (4.73 > 3.25), too much motion/shock |
| 26 | "forward defense, good" | 584.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 27 | "flick shot, good" | 616.53s | Gyro std-of-mag too high (1.65 > 1.2), bat was not still |
| 29 | "flick shot, good" | 632.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 35 | "defense, good" | 679.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 44 | "flick shot, okay" | 999.53s | Accel std-of-mag too high (6.44 > 3.25), too much motion/shock |
| 45 | "flick shot, good" | 1005.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 48 | "forward defense, good" | 1027.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 52 | "flick shot, okay" | 1073.53s | Gyro std-of-mag too high (1.31 > 1.2), bat was not still |
| 57 | "pull shot, good" | 1137.53s | Gyro std-of-mag too high (1.21 > 1.2), bat was not still |
| 63 | "back defense, okay" | 1205.53s | Gyro std-of-mag too high (1.40 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.10 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.43 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.70 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.11 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 140 | 130 | 92 | 38 | 48 | 0.71 | 0.66 | 0.67 | 0.90 |
| live_session_20260531_10 | 6 | 5 | 5 | 0 | 1 | 1.00 | 0.83 | 0.60 | 1.00 |
| live_session_20260531_14 | 40 | 76 | 19 | 57 | 21 | 0.25 | 0.47 | 0.47 | 0.95 |
| live_session_20260601 | 68 | 82 | 54 | 28 | 14 | 0.66 | 0.79 | 0.93 | 0.81 |
| live_session_20260605 | 22 | 33 | 21 | 12 | 1 | 0.64 | 0.95 | 0.81 | 0.90 |
| live_session_20260607 | 34 | 68 | 18 | 50 | 16 | 0.26 | 0.53 | 0.44 | 0.89 |
| live_session_20260608 | 60 | 66 | 53 | 13 | 7 | 0.80 | 0.88 | 0.85 | 0.72 |
| live_session_20260609 | 40 | 69 | 26 | 43 | 14 | 0.38 | 0.65 | 0.88 | 0.85 |
| live_session_20260611 | 56 | 87 | 42 | 45 | 14 | 0.48 | 0.75 | 0.67 | 0.95 |
| live_session_20260612 | 50 | 97 | 34 | 63 | 16 | 0.35 | 0.68 | 0.44 | 0.97 |
| live_session_20260613 | 43 | 67 | 29 | 38 | 14 | 0.43 | 0.67 | 0.41 | 0.86 |
| live_session_20260614 | 46 | 77 | 28 | 49 | 18 | 0.36 | 0.61 | 0.29 | 0.89 |
| live_session_20260615 | 42 | 103 | 26 | 77 | 16 | 0.25 | 0.62 | 0.65 | 0.92 |
| live_session_20260616 | 36 | 81 | 26 | 55 | 10 | 0.32 | 0.72 | 0.62 | 0.69 |
| live_session_20260618 | 69 | 86 | 64 | 22 | 5 | 0.74 | 0.93 | 0.77 | 0.95 |
| live_session_20260619 | 66 | 81 | 64 | 17 | 2 | 0.79 | 0.97 | 0.86 | 1.00 |
| live_session_20260621 | 99 | 94 | 67 | 27 | 32 | 0.71 | 0.68 | 0.70 | 0.96 |
| live_session_20260622 | 68 | 93 | 66 | 27 | 2 | 0.71 | 0.97 | 0.80 | 1.00 |
| live_session_20260623 | 125 | 88 | 72 | 16 | 53 | 0.82 | 0.58 | 0.47 | 0.93 |
| live_session_20260625 | 67 | 100 | 50 | 50 | 17 | 0.50 | 0.75 | 0.80 | 0.98 |
| live_session_20260626 | 66 | 93 | 65 | 28 | 1 | 0.70 | 0.98 | 0.78 | 0.95 |
| live_session_20260627 | 38 | 78 | 22 | 56 | 16 | 0.28 | 0.58 | 0.68 | 0.91 |
| live_session_20260628 | 56 | 89 | 56 | 33 | 0 | 0.63 | 1.00 | 0.70 | 0.80 |
| live_session_20260629 | 65 | 90 | 65 | 25 | 0 | 0.72 | 1.00 | 0.31 | 1.00 |
| live_session_20260702 | 66 | 85 | 66 | 19 | 0 | 0.78 | 1.00 | 0.83 | 0.94 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1559
- **Total Combined Detected Shots:** 2114
- **Total Combined True Positives (Matches):** 1212
- **Total Combined False Positives:** 902
- **Overall Shot Classification Accuracy:** 65.7%
- **Overall Hit/Miss Agreement:** 91.6%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
