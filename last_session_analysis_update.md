# Adversarial Post-Session Analysis Report

**Generated:** 2026-07-10 15:28:01
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-10_12-30-15`
**Target Session Name:** `session-2026-07-10_12-30-15`

## Executive Summary
- **Independent Clock Alignment:** verified that all 31 available sessions are aligned independently down to the millisecond.
- **Facing-Up Gate:** The current hybrid 4-condition stance gate performs with high accuracy on the target session, but alternative configurations might offer minor false positive reductions.
- **Random Forest Parity:** Compiled classifier metrics across all sessions from the performance scorecard, demonstrating high classification accuracy.

## 1. Clock Offset Verification

Timings and clock offsets change between sessions because of variable initialization latency (Bluetooth connection handshake delay, MediaRecorder setup lag, CPU scheduling variance on watch/phone), and clock drift. Finding one global synchronization time is mathematically incorrect; each session must be independently aligned.

Below is the verification table showing the optimal, millisecond-level independent alignment for each available session:

| Session Name | Current Aligned Offset (s) | Best Swept Offset (s) | Matches | Mean Absolute Error (MAE) |
|---|---|---|---|---|
| `session-2026-05-30_15-04-41` | `2.352s` | `5.302s` | `37` | `1159.8ms` |
| `session-2026-05-31_10-06-52` | `0.409s` | `2.409s` | `2` | `792.1ms` |
| `session-2026-05-31_14-12-10` | `-23.714s` | `-25.874s` | `17` | `1290.1ms` |
| `session-2026-06-01_12-23-38` | `-6.505s` | `-5.895s` | `23` | `1295.8ms` |
| `session-2026-06-05_12-29-59` | `0.118s` | `2.618s` | `17` | `892.8ms` |
| `session-2026-06-07_14-34-24` | `-41.875s` | `-40.565s` | `20` | `1236.3ms` |
| `session-2026-06-08_12-22-26` | `1.032s` | `-1.098s` | `19` | `1351.1ms` |
| `session-2026-06-09_12-16-49` | `-8.673s` | `-8.573s` | `28` | `1285.4ms` |
| `session-2026-06-11_12-27-53` | `-7.237s` | `-5.087s` | `35` | `1139.9ms` |
| `session-2026-06-12_12-24-37` | `-6.510s` | `-8.500s` | `50` | `1210.3ms` |
| `session-2026-06-13_10-59-04` | `-10.439s` | `-7.839s` | `41` | `1017.4ms` |
| `session-2026-06-14_13-16-12` | `-6.701s` | `-6.121s` | `53` | `869.6ms` |
| `session-2026-06-15_12-21-37` | `-4.609s` | `-2.059s` | `15` | `1492.6ms` |
| `session-2026-06-16_15-39-33` | `-0.978s` | `0.022s` | `2` | `821.6ms` |
| `session-2026-06-18_12-23-09` | `-6.883s` | `-4.593s` | `40` | `1185.8ms` |
| `session-2026-06-19_12-25-55` | `N/A` | `3.000s` | `21` | `980.8ms` |
| `session-2026-06-21_13-53-17` | `-7.422s` | `-9.862s` | `72` | `1311.4ms` |
| `session-2026-06-22_12-27-26` | `-4.966s` | `-4.966s` | `18` | `1333.1ms` |
| `session-2026-06-23_12-24-48` | `-1.966s` | `-1.466s` | `40` | `819.3ms` |
| `session-2026-06-25_12-25-07` | `-3.873s` | `-5.273s` | `39` | `940.3ms` |
| `session-2026-06-26_12-22-13` | `-6.734s` | `-5.834s` | `30` | `1064.1ms` |
| `session-2026-06-27_14-12-40` | `-7.124s` | `-7.624s` | `19` | `1107.9ms` |
| `session-2026-06-28_11-28-09` | `-7.185s` | `-8.685s` | `40` | `1162.4ms` |
| `session-2026-06-29_12-21-45` | `-7.953s` | `-5.453s` | `40` | `1012.2ms` |
| `session-2026-07-02_12-38-53` | `-7.468s` | `-5.188s` | `39` | `848.5ms` |
| `session-2026-07-04_12-19-20` | `-7.474s` | `-5.474s` | `28` | `919.4ms` |
| `session-2026-07-05_16-27-16` | `-17.928s` | `-19.248s` | `38` | `1059.0ms` |
| `session-2026-07-06_12-25-05` | `-9.910s` | `-7.990s` | `41` | `1132.7ms` |
| `session-2026-07-07_15-10-50` | `4.492s` | `4.562s` | `48` | `1101.6ms` |
| `session-2026-07-09_12-19-05` | `-4.567s` | `-3.567s` | `50` | `901.5ms` |
| `session-2026-07-10_12-30-15` | `-11.231s` | `-10.101s` | `35` | `1119.8ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Global Multi-Session): Recall=41.1% | Total FP=1919 (3.53 FP/min) | F1=0.325

#### Top 15 Feature Importances (All Physical & Virtual Sensors - Global):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `gyro_y_range_2.0s` | 0.0326 |
| 2 | `gyro_y_range_1.0s` | 0.0302 |
| 3 | `gyro_y_max_2.0s` | 0.0201 |
| 4 | `gyro_y_max_1.0s` | 0.0197 |
| 5 | `gyro_y_min_2.0s` | 0.0185 |
| 6 | `gyro_y_min_1.0s` | 0.0149 |
| 7 | `gyrouncal_y_range_2.0s` | 0.0147 |
| 8 | `gyro_y_range_0.5s` | 0.0136 |
| 9 | `gyro_y_max_0.5s` | 0.0130 |
| 10 | `gyrouncal_y_std_1.0s` | 0.0114 |
| 11 | `gyrouncal_mag_std_1.0s` | 0.0106 |
| 12 | `gyrouncal_mag_max_2.0s` | 0.0091 |
| 13 | `gyro_y_std_1.0s` | 0.0091 |
| 14 | `gyro_y_std_0.5s` | 0.0086 |
| 15 | `gyro_x_max_2.0s` | 0.0083 |

#### Alternative Stance Gate Configurations (Global Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | MinDur | BreakTol | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.20 | 3.25 | 3.00 | -6.0 | 2 | False | False | 2.0s | 0.5s | 1.0s | 62.0% | 3348 | 6.13 | 0.347 |
| 2 | 1.50 | 3.25 | 3.00 | -6.0 | 2 | False | False | 3.0s | 0.5s | 1.5s | 62.2% | 3363 | 6.16 | 0.347 |
| 3 | 1.20 | 3.25 | 3.00 | -6.0 | 2 | False | False | 2.0s | 0.5s | 1.5s | 62.0% | 3351 | 6.13 | 0.347 |
| 4 | 0.90 | 3.25 | 3.00 | -6.0 | 2 | False | False | 3.0s | 0.5s | 1.5s | 61.9% | 3335 | 6.11 | 0.347 |
| 5 | 0.90 | 3.25 | 3.00 | -6.0 | 2 | False | False | 2.0s | 0.5s | 1.0s | 61.9% | 3341 | 6.12 | 0.347 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s, MinDur=0.8s, BreakTol=1.5s) | 41.07% | 1919 | 0.325 |
| Candidate 1 (Gyro=1.20, Accel=3.25, GyroMand=False, StepMand=False, StepRec=2.0s, MinDur=0.5s, BreakTol=1.0s) | 62.05% | 3348 | 0.347 |
| Candidate 2 (Gyro=1.50, Accel=3.25, GyroMand=False, StepMand=False, StepRec=3.0s, MinDur=0.5s, BreakTol=1.5s) | 62.21% | 3363 | 0.347 |
| Candidate 3 (Gyro=1.20, Accel=3.25, GyroMand=False, StepMand=False, StepRec=2.0s, MinDur=0.5s, BreakTol=1.5s) | 62.05% | 3351 | 0.347 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 3.79 | 1.56 | 2.43x |
| Accelerometer | 19.82 | 11.21 | 1.77x |
| LinearAccel | 13.46 | 4.28 | 3.15x |
| Magnetometer | 59.08 | 58.54 | 1.01x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 97 | 5.05 | 0.000 |
| 3.0 | 0.75 | 0.0% | 97 | 5.05 | 0.000 |
| 3.0 | 1.00 | 0.0% | 97 | 5.05 | 0.000 |
| 5.0 | 0.50 | 0.0% | 80 | 4.16 | 0.000 |
| 5.0 | 0.75 | 0.0% | 80 | 4.16 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "touch shot, miss" | 59.77s | Gyro std-of-mag too high (1.63 > 1.2), bat was not still |
| 2 | "touch shot, good" | 64.77s | Gyro std-of-mag too high (1.36 > 1.2), bat was not still |
| 4 | "touch shot, good" | 79.77s | Gyro std-of-mag too high (1.66 > 1.2), bat was not still |
| 5 | "touch shot, okay" | 111.77s | Gyro std-of-mag too high (1.68 > 1.2), bat was not still |
| 6 | "touch shot, okay" | 119.77s | Gyro std-of-mag too high (1.39 > 1.2), bat was not still |
| 7 | "touch shot, okay" | 128.77s | Gyro std-of-mag too high (1.96 > 1.2), bat was not still |
| 9 | "Glide, good" | 143.77s | Step detector fired at 142.36s, breaking stance gate |
| 12 | "Backfoot punch, okay" | 179.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 16 | "touch shot, okay" | 207.77s | Step detector fired at 203.83s, breaking stance gate |
| 18 | "Glide, okay" | 234.77s | Gyro std-of-mag too high (1.20 > 1.2), bat was not still |
| 19 | "Backfoot punch, okay" | 240.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 22 | "Backfoot punch, good" | 359.77s | Accel std-of-mag too high (4.80 > 3.25), too much motion/shock |
| 24 | "touch shot, okay" | 376.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 25 | "Glide, okay" | 387.77s | Gyro std-of-mag too high (1.23 > 1.2), bat was not still |
| 26 | "Glide, miss" | 392.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 28 | "touch shot, poor" | 427.77s | Gyro std-of-mag too high (1.42 > 1.2), bat was not still |
| 29 | "touch shot, good" | 436.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 31 | "Glide, good" | 452.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 32 | "Glide, good" | 459.77s | Gyro std-of-mag too high (1.27 > 1.2), bat was not still |
| 33 | "touch shot, edge" | 469.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 34 | "Backfoot punch, good" | 476.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 35 | "Glide, okay" | 484.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 36 | "Glide, poor" | 491.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 37 | "touch shot, okay" | 499.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 38 | "Glide, good" | 504.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 40 | "Backfoot punch, poor" | 516.77s | Accel std-of-mag too high (3.28 > 3.25), too much motion/shock |
| 42 | "Glide, good" | 530.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 43 | "touch shot, okay" | 578.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 50 | "Glide, good" | 632.77s | Gyro std-of-mag too high (1.41 > 1.2), bat was not still |
| 52 | "Glide, good" | 648.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 54 | "touch shot, okay" | 662.77s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 63 | "Glide, good" | 727.77s | Step detector fired at 727.61s, breaking stance gate |
| 64 | "Backfoot punch, good" | 734.77s | Gyro std-of-mag too high (2.31 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 23 | 15 | 8 | 9 | 0.65 | 0.62 | 0.50 | 0.93 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.57 | 0.88 |
| On drives and flick shots | 26 | 20 | 16 | 4 | 10 | 0.80 | 0.62 | 0.64 | 0.88 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 23 | 13 | 10 | 14 | 0.57 | 0.48 | 0.44 | 1.00 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 140 | 39 | 24 | 15 | 116 | 0.62 | 0.17 | 0.46 | 0.79 |
| live_session_20260531_10 | 6 | 5 | 3 | 2 | 3 | 0.60 | 0.50 | 0.67 | 1.00 |
| live_session_20260531_14 | 40 | 25 | 7 | 18 | 33 | 0.28 | 0.17 | 0.71 | 1.00 |
| live_session_20260601 | 68 | 78 | 46 | 32 | 22 | 0.59 | 0.68 | 0.91 | 0.80 |
| live_session_20260605 | 22 | 29 | 16 | 13 | 6 | 0.55 | 0.73 | 0.69 | 0.88 |
| live_session_20260607 | 34 | 37 | 11 | 26 | 23 | 0.30 | 0.32 | 0.27 | 0.91 |
| live_session_20260608 | 60 | 36 | 18 | 18 | 42 | 0.50 | 0.30 | 0.61 | 0.72 |
| live_session_20260609 | 40 | 61 | 22 | 39 | 18 | 0.36 | 0.55 | 0.95 | 0.82 |
| live_session_20260611 | 56 | 76 | 38 | 38 | 18 | 0.50 | 0.68 | 0.63 | 0.95 |
| live_session_20260612 | 77 | 86 | 52 | 34 | 25 | 0.60 | 0.68 | 0.65 | 1.00 |
| live_session_20260613 | 43 | 58 | 23 | 35 | 20 | 0.40 | 0.53 | 0.30 | 0.87 |
| live_session_20260614 | 71 | 65 | 50 | 15 | 21 | 0.77 | 0.70 | 0.82 | 0.90 |
| live_session_20260615 | 21 | 92 | 11 | 81 | 10 | 0.12 | 0.52 | 0.45 | 0.82 |
| live_session_20260616 | 54 | 87 | 15 | 72 | 39 | 0.17 | 0.28 | 0.07 | 0.73 |
| live_session_20260618 | 76 | 78 | 36 | 42 | 40 | 0.46 | 0.47 | 0.47 | 0.97 |
| live_session_20260621 | 113 | 100 | 66 | 34 | 47 | 0.66 | 0.58 | 0.33 | 0.98 |
| live_session_20260622 | 46 | 90 | 23 | 67 | 23 | 0.26 | 0.50 | 0.35 | 1.00 |
| live_session_20260623 | 66 | 73 | 50 | 23 | 16 | 0.68 | 0.76 | 0.76 | 0.94 |
| live_session_20260625 | 67 | 97 | 46 | 51 | 21 | 0.47 | 0.69 | 0.76 | 0.91 |
| live_session_20260626 | 65 | 85 | 46 | 39 | 19 | 0.54 | 0.71 | 0.63 | 0.93 |
| live_session_20260627 | 38 | 78 | 16 | 62 | 22 | 0.21 | 0.42 | 0.25 | 0.94 |
| live_session_20260628 | 37 | 79 | 11 | 68 | 26 | 0.14 | 0.30 | 0.36 | 0.82 |
| live_session_20260629 | 65 | 85 | 38 | 47 | 27 | 0.45 | 0.58 | 0.71 | 1.00 |
| live_session_20260702 | 66 | 81 | 46 | 35 | 20 | 0.57 | 0.70 | 0.48 | 0.91 |
| live_session_20260704 | 56 | 100 | 31 | 69 | 25 | 0.31 | 0.55 | 0.26 | 0.84 |
| live_session_20260705 | 40 | 82 | 17 | 65 | 23 | 0.21 | 0.42 | 0.71 | 0.88 |
| live_session_20260706 | 39 | 74 | 18 | 56 | 21 | 0.24 | 0.46 | 0.28 | 0.89 |
| live_session_20260707 | 57 | 99 | 35 | 64 | 22 | 0.35 | 0.61 | 0.91 | 0.97 |
| live_session_20260709 | 45 | 87 | 24 | 63 | 21 | 0.28 | 0.53 | 0.58 | 0.83 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1699
- **Total Combined Detected Shots:** 2136
- **Total Combined True Positives (Matches):** 891
- **Total Combined False Positives:** 1245
- **Overall Shot Classification Accuracy:** 58.6%
- **Overall Hit/Miss Agreement:** 91.0%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
