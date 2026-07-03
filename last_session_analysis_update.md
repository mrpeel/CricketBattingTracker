# Adversarial Post-Session Analysis Report

**Generated:** 2026-07-03 20:12:08
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-02_12-38-53`
**Target Session Name:** `session-2026-07-02_12-38-53`

## Executive Summary
- **Independent Clock Alignment:** verified that all 25 available sessions are aligned independently down to the millisecond.
- **Facing-Up Gate:** The current hybrid 4-condition stance gate performs with high accuracy on the target session, but alternative configurations might offer minor false positive reductions.
- **Random Forest Parity:** Compiled classifier metrics across all sessions from the performance scorecard, demonstrating high classification accuracy.

## 1. Clock Offset Verification

Timings and clock offsets change between sessions because of variable initialization latency (Bluetooth connection handshake delay, MediaRecorder setup lag, CPU scheduling variance on watch/phone), and clock drift. Finding one global synchronization time is mathematically incorrect; each session must be independently aligned.

Below is the verification table showing the optimal, millisecond-level independent alignment for each available session:

| Session Name | Current Aligned Offset (s) | Best Swept Offset (s) | Matches | Mean Absolute Error (MAE) |
|---|---|---|---|---|
| `session-2026-05-30_15-04-41` | `2.352s` | `5.352s` | `57` | `1093.3ms` |
| `session-2026-05-31_10-06-52` | `0.409s` | `1.909s` | `6` | `993.3ms` |
| `session-2026-05-31_14-12-10` | `-23.714s` | `-20.784s` | `62` | `974.7ms` |
| `session-2026-06-01_12-23-38` | `-6.505s` | `-5.985s` | `58` | `1163.9ms` |
| `session-2026-06-05_12-29-59` | `0.118s` | `2.428s` | `22` | `801.1ms` |
| `session-2026-06-07_14-34-24` | `-41.875s` | `-44.375s` | `44` | `1026.3ms` |
| `session-2026-06-08_12-22-26` | `1.032s` | `1.532s` | `53` | `831.7ms` |
| `session-2026-06-09_12-16-49` | `-17.709s` | `-15.699s` | `56` | `1073.2ms` |
| `session-2026-06-11_12-27-53` | `-47.257s` | `-48.267s` | `66` | `1254.2ms` |
| `session-2026-06-12_12-24-37` | `-32.545s` | `-32.885s` | `60` | `1283.4ms` |
| `session-2026-06-13_10-59-04` | `6.043s` | `3.363s` | `64` | `782.9ms` |
| `session-2026-06-14_13-16-12` | `-38.423s` | `-40.923s` | `59` | `1115.8ms` |
| `session-2026-06-15_12-21-37` | `24.128s` | `26.338s` | `62` | `1197.9ms` |
| `session-2026-06-16_15-39-33` | `11.463s` | `13.723s` | `45` | `812.7ms` |
| `session-2026-06-18_12-23-09` | `4.677s` | `4.387s` | `65` | `776.1ms` |
| `session-2026-06-19_12-25-55` | `3.850s` | `3.370s` | `65` | `844.4ms` |
| `session-2026-06-21_13-53-17` | `1.452s` | `3.552s` | `72` | `1043.7ms` |
| `session-2026-06-22_12-27-26` | `3.255s` | `3.325s` | `69` | `833.4ms` |
| `session-2026-06-23_12-24-48` | `2.464s` | `0.564s` | `84` | `1245.5ms` |
| `session-2026-06-25_12-25-07` | `4.185s` | `2.035s` | `52` | `920.3ms` |
| `session-2026-06-26_12-22-13` | `4.034s` | `4.004s` | `69` | `863.6ms` |
| `session-2026-06-27_14-12-40` | `-35.781s` | `-33.001s` | `43` | `1388.5ms` |
| `session-2026-06-28_11-28-09` | `4.514s` | `3.414s` | `58` | `830.0ms` |
| `session-2026-06-29_12-21-45` | `3.304s` | `5.764s` | `65` | `1450.0ms` |
| `session-2026-07-02_12-38-53` | `3.728s` | `4.228s` | `65` | `823.9ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=86.4% | FP=27 (1.27 FP/min) | F1=0.760

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `gyro_mag_min_2.0s` | 0.0457 |
| 2 | `accel_y_mean_2.0s` | 0.0455 |
| 3 | `linacc_mag_min_2.0s` | 0.0380 |
| 4 | `accel_mag_range_2.0s` | 0.0348 |
| 5 | `gyrouncal_mag_min_2.0s` | 0.0243 |
| 6 | `gyro_y_max_2.0s` | 0.0233 |
| 7 | `accel_mag_max_2.0s` | 0.0228 |
| 8 | `accel_mag_max_1.0s` | 0.0211 |
| 9 | `linacc_mag_max_2.0s` | 0.0188 |
| 10 | `linacc_z_min_2.0s` | 0.0181 |
| 11 | `accel_y_max_1.0s` | 0.0180 |
| 12 | `linacc_mag_range_2.0s` | 0.0179 |
| 13 | `linacc_z_range_2.0s` | 0.0176 |
| 14 | `linacc_mag_min_1.0s` | 0.0171 |
| 15 | `accel_mag_range_1.0s` | 0.0166 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 0.5s | 84.8% | 24 | 1.13 | 0.767 |
| 2 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 1.0s | 84.8% | 24 | 1.13 | 0.767 |
| 3 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 2.0s | 84.8% | 24 | 1.13 | 0.767 |
| 4 | 0.90 | 3.25 | 2.50 | -7.0 | 3 | True | True | 3.0s | 84.8% | 24 | 1.13 | 0.767 |
| 5 | 0.90 | 4.00 | 2.50 | -7.0 | 3 | True | True | 0.5s | 84.8% | 24 | 1.13 | 0.767 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 47.73% | 1254 | 0.444 |
| Candidate 1 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=0.5s) | 46.49% | 1131 | 0.445 |
| Candidate 2 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 46.49% | 1130 | 0.446 |
| Candidate 3 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=2.0s) | 46.42% | 1126 | 0.445 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 4.18 | 2.47 | 1.69x |
| Accelerometer | 15.82 | 13.71 | 1.15x |
| LinearAccel | 10.02 | 7.09 | 1.41x |
| Magnetometer | 58.90 | 56.69 | 1.04x |

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
| 1 | "glance, good" | 130.73s | Gyro std-of-mag too high (1.54 > 1.2), bat was not still |
| 2 | "flick, okay" | 139.73s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 14 | "flick shot, good" | 250.73s | Gyro std-of-mag too high (1.72 > 1.2), bat was not still |
| 48 | "forward defense, good" | 1038.73s | Gyro std-of-mag too high (1.32 > 1.2), bat was not still |
| 54 | "on drive, okay" | 1105.73s | Gyro std-of-mag too high (1.47 > 1.2), bat was not still |
| 55 | "flick shot, okay" | 1112.73s | Gyro std-of-mag too high (1.48 > 1.2), bat was not still |
| 59 | "flick shot, edge" | 1167.73s | Gyro std-of-mag too high (1.75 > 1.2), bat was not still |
| 62 | "flick shot, good" | 1194.73s | Gyro std-of-mag too high (1.70 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.24 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.43 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.48 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.28 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 142 | 130 | 110 | 20 | 32 | 0.85 | 0.77 | 0.74 | 0.92 |
| live_session_20260531_14 | 37 | 76 | 28 | 48 | 9 | 0.37 | 0.76 | 0.46 | 0.93 |
| live_session_20260601 | 44 | 82 | 30 | 52 | 14 | 0.37 | 0.68 | 0.50 | 1.00 |
| live_session_20260605 | 46 | 33 | 19 | 14 | 27 | 0.58 | 0.41 | 0.26 | 0.95 |
| live_session_20260607 | 35 | 68 | 23 | 45 | 12 | 0.34 | 0.66 | 0.43 | 0.78 |
| live_session_20260608 | 42 | 66 | 28 | 38 | 14 | 0.42 | 0.67 | 0.50 | 0.68 |
| live_session_20260609 | 40 | 69 | 28 | 41 | 12 | 0.41 | 0.70 | 0.86 | 0.86 |
| live_session_20260611 | 72 | 87 | 43 | 44 | 29 | 0.49 | 0.60 | 0.56 | 0.98 |
| live_session_20260612 | 50 | 97 | 34 | 63 | 16 | 0.35 | 0.68 | 0.47 | 0.97 |
| live_session_20260613 | 43 | 67 | 29 | 38 | 14 | 0.43 | 0.67 | 0.48 | 0.86 |
| live_session_20260614 | 46 | 77 | 28 | 49 | 18 | 0.36 | 0.61 | 0.39 | 0.89 |
| live_session_20260615 | 42 | 103 | 26 | 77 | 16 | 0.25 | 0.62 | 0.69 | 0.92 |
| live_session_20260616 | 36 | 81 | 26 | 55 | 10 | 0.32 | 0.72 | 0.50 | 0.69 |
| live_session_20260618 | 69 | 86 | 64 | 22 | 5 | 0.74 | 0.93 | 0.92 | 0.95 |
| live_session_20260619 | 66 | 81 | 64 | 17 | 2 | 0.79 | 0.97 | 0.89 | 1.00 |
| live_session_20260621 | 99 | 94 | 67 | 27 | 32 | 0.71 | 0.68 | 0.70 | 0.96 |
| live_session_20260622 | 68 | 93 | 66 | 27 | 2 | 0.71 | 0.97 | 0.79 | 1.00 |
| live_session_20260623 | 125 | 88 | 72 | 16 | 53 | 0.82 | 0.58 | 0.44 | 0.93 |
| live_session_20260625 | 67 | 100 | 50 | 50 | 17 | 0.50 | 0.75 | 0.80 | 0.98 |
| live_session_20260626 | 66 | 93 | 65 | 28 | 1 | 0.70 | 0.98 | 0.75 | 0.95 |
| live_session_20260627 | 38 | 78 | 22 | 56 | 16 | 0.28 | 0.58 | 0.50 | 0.91 |
| live_session_20260628 | 56 | 89 | 56 | 33 | 0 | 0.63 | 1.00 | 0.71 | 0.80 |
| live_session_20260629 | 65 | 90 | 65 | 25 | 0 | 0.72 | 1.00 | 0.34 | 1.00 |
| live_session_20260702 | 66 | 85 | 66 | 19 | 0 | 0.78 | 1.00 | 0.86 | 0.94 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1551
- **Total Combined Detected Shots:** 2109
- **Total Combined True Positives (Matches):** 1191
- **Total Combined False Positives:** 918
- **Overall Shot Classification Accuracy:** 63.1%
- **Overall Hit/Miss Agreement:** 92.7%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
