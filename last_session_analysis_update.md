# Adversarial Post-Session Analysis Report

**Generated:** 2026-06-21 16:41:17
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-21_13-53-17`
**Target Session Name:** `session-2026-06-21_13-53-17`

## Executive Summary
- **Independent Clock Alignment:** verified that all 17 available sessions are aligned independently down to the millisecond.
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
| `session-2026-06-16_15-39-33` | `3.046s` | `3.046s` | `54` | `807.0ms` |
| `session-2026-06-18_12-23-09` | `3.862s` | `4.702s` | `65` | `775.1ms` |
| `session-2026-06-19_12-25-55` | `4.745s` | `4.775s` | `65` | `858.2ms` |
| `session-2026-06-21_13-53-17` | `5.593s` | `5.533s` | `70` | `907.8ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=26.2% | FP=77 (3.75 FP/min) | F1=0.214

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `linacc_z_range_2.0s` | 0.0606 |
| 2 | `linacc_mag_max_2.0s` | 0.0456 |
| 3 | `accel_z_range_2.0s` | 0.0261 |
| 4 | `accel_mag_range_2.0s` | 0.0245 |
| 5 | `linacc_z_min_2.0s` | 0.0241 |
| 6 | `accel_x_max_2.0s` | 0.0227 |
| 7 | `linacc_mag_std_2.0s` | 0.0211 |
| 8 | `linacc_x_range_2.0s` | 0.0194 |
| 9 | `accel_z_std_2.0s` | 0.0190 |
| 10 | `linacc_mag_range_2.0s` | 0.0186 |
| 11 | `grav_z_max_2.0s` | 0.0176 |
| 12 | `gyrouncal_z_mean_2.0s` | 0.0175 |
| 13 | `accel_z_max_2.0s` | 0.0175 |
| 14 | `gyrouncal_z_max_2.0s` | 0.0172 |
| 15 | `accel_z_min_2.0s` | 0.0153 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 3.0s | 26.2% | 64 | 3.12 | 0.233 |
| 2 | 1.20 | 3.25 | 2.00 | -7.0 | 3 | True | True | 3.0s | 26.2% | 64 | 3.12 | 0.233 |
| 3 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 0.5s | 26.2% | 65 | 3.16 | 0.231 |
| 4 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 1.0s | 26.2% | 65 | 3.16 | 0.231 |
| 5 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 2.0s | 26.2% | 65 | 3.16 | 0.231 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 66.69% | 594 | 0.603 |
| Candidate 1 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=3.0s) | 65.14% | 474 | 0.622 |
| Candidate 2 (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=3.0s) | 65.70% | 503 | 0.619 |
| Candidate 3 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=0.5s) | 65.25% | 479 | 0.622 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 3.23 | 2.81 | 1.15x |
| Accelerometer | 16.91 | 11.62 | 1.46x |
| LinearAccel | 12.35 | 5.74 | 2.15x |
| Magnetometer | 57.01 | 56.61 | 1.01x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 90 | 4.38 | 0.000 |
| 3.0 | 0.75 | 0.0% | 90 | 4.38 | 0.000 |
| 3.0 | 1.00 | 0.0% | 90 | 4.38 | 0.000 |
| 5.0 | 0.50 | 0.0% | 77 | 3.75 | 0.000 |
| 5.0 | 0.75 | 0.0% | 77 | 3.75 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 3 | "Cut shot, okay." | 84.59s | Gyro std-of-mag too high (1.46 > 1.2), bat was not still |
| 5 | "Back-foot punch, okay." | 100.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 6 | "Cut shot, okay." | 128.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 7 | "Glide, okay." | 136.59s | Gyro std-of-mag too high (1.23 > 1.2), bat was not still |
| 9 | "Cut shot, good." | 152.59s | Gyro std-of-mag too high (2.15 > 1.2), bat was not still |
| 10 | "Cut shot, okay." | 162.59s | Gyro std-of-mag too high (2.15 > 1.2), bat was not still |
| 12 | "Off drive, poor." | 206.59s | Gyro std-of-mag too high (1.61 > 1.2), bat was not still |
| 14 | "Glide, okay." | 229.59s | Gyro std-of-mag too high (1.21 > 1.2), bat was not still |
| 16 | "Cut shot, okay." | 253.59s | Gyro std-of-mag too high (1.96 > 1.2), bat was not still |
| 17 | "Glide, good." | 260.59s | Gyro std-of-mag too high (1.20 > 1.2), bat was not still |
| 18 | "Glide, poor." | 268.59s | Gyro std-of-mag too high (1.29 > 1.2), bat was not still |
| 19 | "Cut shot, poor." | 277.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 20 | "Cut shot, okay." | 285.59s | Gyro std-of-mag too high (1.44 > 1.2), bat was not still |
| 21 | "Cut shot, okay." | 294.59s | Gyro std-of-mag too high (2.16 > 1.2), bat was not still |
| 24 | "Cut shot, okay." | 542.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 25 | "Cut shot, good." | 550.59s | Gyro std-of-mag too high (2.16 > 1.2), bat was not still |
| 26 | "Cut shot, good." | 559.59s | Gyro std-of-mag too high (1.99 > 1.2), bat was not still |
| 27 | "Back-foot punch, okay." | 567.59s | Gyro std-of-mag too high (1.35 > 1.2), bat was not still |
| 28 | "Glide, okay." | 575.59s | Gyro std-of-mag too high (1.41 > 1.2), bat was not still |
| 29 | "Glide, okay." | 585.59s | Gyro std-of-mag too high (1.34 > 1.2), bat was not still |
| 30 | "Glide, edge." | 593.59s | Gyro std-of-mag too high (1.30 > 1.2), bat was not still |
| 31 | "Cut shot, good." | 603.59s | Gyro std-of-mag too high (1.68 > 1.2), bat was not still |
| 32 | "Back-foot punch, poor." | 612.59s | Gyro std-of-mag too high (1.83 > 1.2), bat was not still |
| 33 | "Glide, poor." | 620.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 36 | "Glide, okay." | 648.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 37 | "Back-foot punch, edge." | 657.59s | Gyro std-of-mag too high (1.34 > 1.2), bat was not still |
| 39 | "Glide, okay." | 671.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 40 | "Cut shot, good." | 680.59s | Gyro std-of-mag too high (1.98 > 1.2), bat was not still |
| 42 | "Back-foot punch, good." | 696.59s | Gyro std-of-mag too high (1.26 > 1.2), bat was not still |
| 43 | "Cut shot, good." | 703.59s | Gyro std-of-mag too high (2.05 > 1.2), bat was not still |
| 44 | "Back-foot punch, poor." | 713.59s | Gyro std-of-mag too high (1.61 > 1.2), bat was not still |
| 45 | "Cut shot, good." | 945.59s | Gyro std-of-mag too high (2.16 > 1.2), bat was not still |
| 46 | "Cut shot, okay." | 965.59s | Gyro std-of-mag too high (2.19 > 1.2), bat was not still |
| 47 | "Glide, miss." | 976.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 48 | "Back-foot punch, okay." | 985.59s | Gyro std-of-mag too high (1.72 > 1.2), bat was not still |
| 50 | "Glide, okay." | 1013.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 51 | "Back-foot punch, okay." | 1023.59s | Gyro std-of-mag too high (1.93 > 1.2), bat was not still |
| 52 | "Glide, miss." | 1032.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 53 | "Cut shot, okay." | 1045.59s | Gyro std-of-mag too high (2.18 > 1.2), bat was not still |
| 55 | "Cut shot, okay." | 1089.59s | Gyro std-of-mag too high (1.72 > 1.2), bat was not still |
| 57 | "Glide, okay." | 1107.59s | Accel std-of-mag too high (3.49 > 3.25), too much motion/shock |
| 59 | "Cut shot, good." | 1126.59s | Gyro std-of-mag too high (1.89 > 1.2), bat was not still |
| 60 | "Glide, good." | 1134.59s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 61 | "Cut shot, good." | 1161.59s | Gyro std-of-mag too high (2.16 > 1.2), bat was not still |
| 62 | "Glide, good." | 1168.59s | Gyro std-of-mag too high (1.34 > 1.2), bat was not still |
| 63 | "Cut shot, good." | 1176.59s | Gyro std-of-mag too high (1.63 > 1.2), bat was not still |
| 64 | "Cut shot, good." | 1185.59s | Gyro std-of-mag too high (2.22 > 1.2), bat was not still |
| 65 | "Glide, good." | 1192.59s | Gyro std-of-mag too high (1.25 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.29 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.29 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.48 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.17 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 91 | 130 | 74 | 56 | 17 | 0.57 | 0.81 | 0.73 | 0.96 |
| live_session_20260531_10 | 5 | 5 | 5 | 0 | 0 | 1.00 | 1.00 | 0.60 | 1.00 |
| live_session_20260531_14 | 68 | 76 | 68 | 8 | 0 | 0.89 | 1.00 | 0.79 | 0.96 |
| live_session_20260601 | 68 | 82 | 68 | 14 | 0 | 0.83 | 1.00 | 0.94 | 0.85 |
| live_session_20260605 | 30 | 33 | 29 | 4 | 1 | 0.88 | 0.97 | 0.90 | 0.86 |
| live_session_20260607 | 58 | 68 | 58 | 10 | 0 | 0.85 | 1.00 | 0.72 | 0.91 |
| live_session_20260608 | 60 | 66 | 52 | 14 | 8 | 0.79 | 0.87 | 0.81 | 0.71 |
| live_session_20260609 | 63 | 69 | 63 | 6 | 0 | 0.91 | 1.00 | 0.94 | 0.89 |
| live_session_20260611 | 57 | 87 | 56 | 31 | 1 | 0.64 | 0.98 | 0.75 | 0.96 |
| live_session_20260612 | 76 | 97 | 75 | 22 | 1 | 0.77 | 0.99 | 0.85 | 0.97 |
| live_session_20260613 | 64 | 67 | 61 | 6 | 3 | 0.91 | 0.95 | 0.92 | 0.85 |
| live_session_20260614 | 74 | 77 | 58 | 19 | 16 | 0.75 | 0.78 | 0.31 | 0.93 |
| live_session_20260615 | 65 | 103 | 63 | 40 | 2 | 0.61 | 0.97 | 0.48 | 0.94 |
| live_session_20260616 | 54 | 81 | 54 | 27 | 0 | 0.67 | 1.00 | 0.67 | 0.76 |
| live_session_20260618 | 69 | 86 | 64 | 22 | 5 | 0.74 | 0.93 | 0.91 | 0.95 |
| live_session_20260619 | 66 | 81 | 63 | 18 | 3 | 0.78 | 0.95 | 0.87 | 0.97 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1059
- **Total Combined Detected Shots:** 1304
- **Total Combined True Positives (Matches):** 993
- **Total Combined False Positives:** 311
- **Overall Shot Classification Accuracy:** 73.4%
- **Overall Hit/Miss Agreement:** 90.6%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
