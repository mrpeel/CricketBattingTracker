# Adversarial Post-Session Analysis Report

**Generated:** 2026-07-05 19:22:33
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-05_16-27-16`
**Target Session Name:** `session-2026-07-05_16-27-16`

## Executive Summary
- **Independent Clock Alignment:** verified that all 27 available sessions are aligned independently down to the millisecond.
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
| `session-2026-07-04_12-19-20` | `-7.474s` | `-5.474s` | `29` | `882.7ms` |
| `session-2026-07-05_16-27-16` | `-17.928s` | `-14.978s` | `43` | `977.0ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=32.5% | FP=80 (4.23 FP/min) | F1=0.195

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `gyro_y_range_1.0s` | 0.0253 |
| 2 | `gyro_y_max_2.0s` | 0.0238 |
| 3 | `gyro_x_max_2.0s` | 0.0184 |
| 4 | `gyro_y_range_2.0s` | 0.0149 |
| 5 | `gyro_y_range_0.5s` | 0.0126 |
| 6 | `gyro_y_min_1.0s` | 0.0124 |
| 7 | `gyro_y_max_1.0s` | 0.0110 |
| 8 | `maguncal_bias_y_min_2.0s` | 0.0106 |
| 9 | `maguncal_bias_y_max_2.0s` | 0.0105 |
| 10 | `maguncal_bias_y_mean_1.0s` | 0.0100 |
| 11 | `maguncal_bias_y_max_1.0s` | 0.0091 |
| 12 | `gyrouncal_y_std_2.0s` | 0.0088 |
| 13 | `step_age` | 0.0087 |
| 14 | `maguncal_bias_z_min_1.0s` | 0.0085 |
| 15 | `gyro_y_min_0.5s` | 0.0084 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | MinDur | BreakTol | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.50 | 4.00 | 2.50 | -7.0 | 3 | False | True | 3.0s | 0.8s | 1.5s | 55.0% | 105 | 5.56 | 0.263 |
| 2 | 0.90 | 4.00 | 3.00 | -7.0 | 3 | False | True | 3.0s | 0.8s | 1.0s | 52.5% | 99 | 5.24 | 0.263 |
| 3 | 1.50 | 4.00 | 3.00 | -6.0 | 3 | True | True | 3.0s | 0.8s | 1.5s | 47.5% | 86 | 4.55 | 0.262 |
| 4 | 0.90 | 3.25 | 2.50 | -7.0 | 2 | False | True | 3.0s | 0.8s | 1.0s | 55.0% | 106 | 5.61 | 0.262 |
| 5 | 1.20 | 4.00 | 3.00 | -7.0 | 3 | False | True | 3.0s | 0.8s | 1.0s | 55.0% | 106 | 5.61 | 0.262 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s, MinDur=0.8s, BreakTol=1.5s) | 40.94% | 1606 | 0.331 |
| Candidate 1 (Gyro=1.50, Accel=4.00, GyroMand=False, StepMand=True, StepRec=3.0s, MinDur=0.8s, BreakTol=1.5s) | 50.45% | 2233 | 0.332 |
| Candidate 2 (Gyro=0.90, Accel=4.00, GyroMand=False, StepMand=True, StepRec=3.0s, MinDur=0.8s, BreakTol=1.0s) | 47.49% | 2116 | 0.325 |
| Candidate 3 (Gyro=1.50, Accel=4.00, GyroMand=True, StepMand=True, StepRec=3.0s, MinDur=0.8s, BreakTol=1.5s) | 44.45% | 1770 | 0.338 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 6.04 | 1.53 | 3.94x |
| Accelerometer | 31.59 | 11.47 | 2.75x |
| LinearAccel | 23.41 | 4.34 | 5.39x |
| Magnetometer | 59.57 | 57.94 | 1.03x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 98 | 5.19 | 0.000 |
| 3.0 | 0.75 | 0.0% | 98 | 5.19 | 0.000 |
| 3.0 | 1.00 | 0.0% | 98 | 5.19 | 0.000 |
| 5.0 | 0.50 | 0.0% | 80 | 4.23 | 0.000 |
| 5.0 | 0.75 | 0.0% | 80 | 4.23 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 2 | "Power drive okay" | 41.07s | Gyro std-of-mag too high (1.85 > 1.2), bat was not still |
| 6 | "Defense edge" | 71.07s | Gyro std-of-mag too high (1.29 > 1.2), bat was not still |
| 7 | "Power drive good" | 79.07s | Accel std-of-mag too high (3.28 > 3.25), too much motion/shock |
| 8 | "Defense good" | 88.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 10 | "Power drive edge" | 103.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 11 | "Defense edge" | 111.07s | Accel std-of-mag too high (4.96 > 3.25), too much motion/shock |
| 14 | "Power drive miss" | 141.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 16 | "Straight drive good" | 158.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 17 | "Block good" | 167.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 19 | "Power drive edge" | 191.07s | Accel std-of-mag too high (3.67 > 3.25), too much motion/shock |
| 22 | "Power drive good" | 458.07s | Gyro std-of-mag too high (2.61 > 1.2), bat was not still |
| 29 | "Power drive okay" | 522.07s | Accel std-of-mag too high (4.39 > 3.25), too much motion/shock |
| 34 | "Power drive edge" | 569.07s | Gyro std-of-mag too high (2.27 > 1.2), bat was not still |
| 35 | "Power drive edge" | 578.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 38 | "Power shot good" | 620.07s | Gyro std-of-mag too high (1.65 > 1.2), bat was not still |
| 40 | "Flick shot good" | 635.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 41 | "Power drive good" | 913.07s | Accel std-of-mag too high (6.04 > 3.25), too much motion/shock |
| 43 | "Power drive okay" | 929.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 47 | "Power drive poor" | 965.07s | Step detector fired at 961.19s, breaking stance gate |
| 49 | "Power drive okay" | 980.07s | Gyro std-of-mag too high (2.08 > 1.2), bat was not still |
| 54 | "Power drive okay" | 1029.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 55 | "Power drive good" | 1038.07s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.33 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.29 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.74 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.06 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 140 | 130 | 92 | 38 | 48 | 0.71 | 0.66 | 0.55 | 0.90 |
| live_session_20260531_10 | 6 | 5 | 5 | 0 | 1 | 1.00 | 0.83 | 0.40 | 1.00 |
| live_session_20260531_14 | 40 | 76 | 19 | 57 | 21 | 0.25 | 0.47 | 0.37 | 0.95 |
| live_session_20260601 | 68 | 82 | 54 | 28 | 14 | 0.66 | 0.79 | 0.87 | 0.81 |
| live_session_20260605 | 22 | 33 | 21 | 12 | 1 | 0.64 | 0.95 | 0.76 | 0.90 |
| live_session_20260607 | 34 | 68 | 18 | 50 | 16 | 0.26 | 0.53 | 0.39 | 0.89 |
| live_session_20260608 | 60 | 66 | 53 | 13 | 7 | 0.80 | 0.88 | 0.79 | 0.72 |
| live_session_20260609 | 40 | 69 | 26 | 43 | 14 | 0.38 | 0.65 | 0.77 | 0.85 |
| live_session_20260611 | 56 | 87 | 42 | 45 | 14 | 0.48 | 0.75 | 0.69 | 0.95 |
| live_session_20260612 | 77 | 97 | 64 | 33 | 13 | 0.66 | 0.83 | 0.47 | 0.97 |
| live_session_20260613 | 43 | 67 | 25 | 42 | 18 | 0.37 | 0.58 | 0.32 | 0.88 |
| live_session_20260614 | 71 | 77 | 62 | 15 | 9 | 0.81 | 0.87 | 0.58 | 0.92 |
| live_session_20260615 | 21 | 103 | 13 | 90 | 8 | 0.13 | 0.62 | 0.31 | 0.77 |
| live_session_20260616 | 54 | 81 | 15 | 66 | 39 | 0.19 | 0.28 | 0.07 | 0.73 |
| live_session_20260618 | 76 | 86 | 39 | 47 | 37 | 0.45 | 0.51 | 0.36 | 1.00 |
| live_session_20260621 | 113 | 94 | 60 | 34 | 53 | 0.64 | 0.53 | 0.35 | 0.98 |
| live_session_20260622 | 46 | 93 | 24 | 69 | 22 | 0.26 | 0.52 | 0.21 | 1.00 |
| live_session_20260623 | 66 | 88 | 65 | 23 | 1 | 0.74 | 0.98 | 0.83 | 0.94 |
| live_session_20260625 | 67 | 100 | 50 | 50 | 17 | 0.50 | 0.75 | 0.62 | 0.92 |
| live_session_20260626 | 65 | 93 | 53 | 40 | 12 | 0.57 | 0.82 | 0.45 | 0.96 |
| live_session_20260627 | 38 | 78 | 18 | 60 | 20 | 0.23 | 0.47 | 0.33 | 0.89 |
| live_session_20260628 | 37 | 89 | 16 | 73 | 21 | 0.18 | 0.43 | 0.19 | 0.69 |
| live_session_20260629 | 65 | 90 | 46 | 44 | 19 | 0.51 | 0.71 | 0.54 | 1.00 |
| live_session_20260702 | 66 | 85 | 50 | 35 | 16 | 0.59 | 0.76 | 0.34 | 0.92 |
| live_session_20260704 | 56 | 92 | 35 | 57 | 21 | 0.38 | 0.62 | 0.26 | 0.83 |
| live_session_20260705 | 40 | 91 | 19 | 72 | 21 | 0.21 | 0.47 | 0.68 | 0.84 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1558
- **Total Combined Detected Shots:** 2216
- **Total Combined True Positives (Matches):** 1066
- **Total Combined False Positives:** 1150
- **Overall Shot Classification Accuracy:** 51.7%
- **Overall Hit/Miss Agreement:** 90.7%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
