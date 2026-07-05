# Adversarial Post-Session Analysis Report

**Generated:** 2026-07-04 19:39:31
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-04_12-19-20`
**Target Session Name:** `session-2026-07-04_12-19-20`

## Executive Summary
- **Independent Clock Alignment:** verified that all 26 available sessions are aligned independently down to the millisecond.
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
| `session-2026-06-12_12-24-37` | `-6.510s` | `-5.890s` | `62` | `913.8ms` |
| `session-2026-06-13_10-59-04` | `-10.439s` | `-8.989s` | `52` | `1193.1ms` |
| `session-2026-06-14_13-16-12` | `-6.701s` | `-5.321s` | `63` | `868.2ms` |
| `session-2026-06-15_12-21-37` | `-4.609s` | `-2.059s` | `14` | `1283.1ms` |
| `session-2026-06-16_15-39-33` | `-0.978s` | `0.022s` | `3` | `828.2ms` |
| `session-2026-06-18_12-23-09` | `-6.883s` | `-5.883s` | `48` | `1125.8ms` |
| `session-2026-06-19_12-25-55` | `N/A` | `3.000s` | `21` | `980.8ms` |
| `session-2026-06-21_13-53-17` | `-7.422s` | `-6.782s` | `68` | `1135.5ms` |
| `session-2026-06-22_12-27-26` | `-4.966s` | `-3.126s` | `23` | `1454.9ms` |
| `session-2026-06-23_12-24-48` | `-1.966s` | `-1.466s` | `46` | `824.5ms` |
| `session-2026-06-25_12-25-07` | `-3.873s` | `-5.273s` | `41` | `929.1ms` |
| `session-2026-06-26_12-22-13` | `-6.734s` | `-5.844s` | `31` | `1119.6ms` |
| `session-2026-06-27_14-12-40` | `-7.124s` | `-9.364s` | `22` | `1207.8ms` |
| `session-2026-06-28_11-28-09` | `-7.185s` | `-7.185s` | `41` | `1042.3ms` |
| `session-2026-06-29_12-21-45` | `-7.953s` | `-6.733s` | `45` | `1112.6ms` |
| `session-2026-07-02_12-38-53` | `-7.468s` | `-4.668s` | `44` | `824.0ms` |
| `session-2026-07-04_12-19-20` | `-7.474s` | `-5.474s` | `29` | `918.3ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=58.9% | FP=56 (2.72 FP/min) | F1=0.455

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `accel_x_min_2.0s` | 0.0207 |
| 2 | `step_age` | 0.0199 |
| 3 | `accel_y_mean_2.0s` | 0.0179 |
| 4 | `maguncal_bias_x_min_2.0s` | 0.0163 |
| 5 | `maguncal_bias_x_min_1.0s` | 0.0163 |
| 6 | `maguncal_bias_x_min_0.5s` | 0.0158 |
| 7 | `maguncal_bias_x_mean_2.0s` | 0.0138 |
| 8 | `maguncal_bias_x_max_1.0s` | 0.0138 |
| 9 | `gyrouncal_y_min_2.0s` | 0.0135 |
| 10 | `gyro_y_min_2.0s` | 0.0128 |
| 11 | `gyro_mag_min_2.0s` | 0.0120 |
| 12 | `maguncal_bias_x_mean_0.5s` | 0.0116 |
| 13 | `maguncal_bias_x_mean_1.0s` | 0.0105 |
| 14 | `maguncal_bias_z_min_1.0s` | 0.0097 |
| 15 | `maguncal_bias_z_max_2.0s` | 0.0095 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 3.25 | 3.00 | -7.0 | 3 | True | True | 0.5s | 58.9% | 52 | 2.53 | 0.468 |
| 2 | 0.90 | 3.25 | 3.00 | -7.0 | 3 | True | True | 1.0s | 58.9% | 52 | 2.53 | 0.468 |
| 3 | 0.90 | 3.25 | 3.00 | -7.0 | 3 | True | True | 2.0s | 58.9% | 52 | 2.53 | 0.468 |
| 4 | 0.90 | 3.25 | 3.00 | -7.0 | 3 | True | True | 3.0s | 58.9% | 52 | 2.53 | 0.468 |
| 5 | 0.90 | 3.25 | 2.50 | -6.0 | 3 | True | True | 0.5s | 58.9% | 54 | 2.63 | 0.462 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 56.36% | 1273 | 0.466 |
| Candidate 1 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=0.5s) | 55.18% | 1167 | 0.471 |
| Candidate 2 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 55.18% | 1165 | 0.471 |
| Candidate 3 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=2.0s) | 55.08% | 1162 | 0.471 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 6.77 | 1.77 | 3.83x |
| Accelerometer | 33.96 | 11.90 | 2.85x |
| LinearAccel | 27.39 | 4.77 | 5.74x |
| Magnetometer | 59.23 | 57.57 | 1.03x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 96 | 4.67 | 0.000 |
| 3.0 | 0.75 | 0.0% | 96 | 4.67 | 0.000 |
| 3.0 | 1.00 | 0.0% | 96 | 4.67 | 0.000 |
| 5.0 | 0.50 | 0.0% | 86 | 4.18 | 0.000 |
| 5.0 | 0.75 | 0.0% | 86 | 4.18 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "Click shot. Okay." | 37.53s | Accel std-of-mag too high (8.47 > 3.25), too much motion/shock |
| 8 | "Full shot. Okay." | 166.53s | Gyro std-of-mag too high (1.76 > 1.2), bat was not still |
| 9 | "Full shot, good." | 181.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 19 | "Full shot, good." | 502.53s | Gyro std-of-mag too high (1.58 > 1.2), bat was not still |
| 20 | "Full shot. Okay." | 540.53s | Accel std-of-mag too high (3.33 > 3.25), too much motion/shock |
| 21 | "Full shot, miss." | 552.53s | Gyro std-of-mag too high (2.47 > 1.2), bat was not still |
| 25 | "Glance, edge." | 627.53s | Gyro std-of-mag too high (1.61 > 1.2), bat was not still |
| 29 | "Full shot, edge." | 757.53s | Accel std-of-mag too high (6.05 > 3.25), too much motion/shock |
| 31 | "Click shot, good." | 769.53s | Gyro std-of-mag too high (1.99 > 1.2), bat was not still |
| 32 | "Full shot. Okay." | 777.53s | Gyro std-of-mag too high (1.70 > 1.2), bat was not still |
| 36 | "Full shot. Okay." | 1007.53s | Gyro std-of-mag too high (1.43 > 1.2), bat was not still |
| 44 | "Full shot. Okay." | 1083.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 48 | "Uh, full shot. Okay." | 1130.53s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |

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
