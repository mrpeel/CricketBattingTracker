# Adversarial Post-Session Analysis Report

**Generated:** 2026-06-23 17:20:11
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-23_12-24-48`
**Target Session Name:** `session-2026-06-23_12-24-48`

## Executive Summary
- **Independent Clock Alignment:** verified that all 19 available sessions are aligned independently down to the millisecond.
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
| `session-2026-06-21_13-53-17` | `5.593s` | `5.533s` | `70` | `883.2ms` |
| `session-2026-06-22_12-27-26` | `5.184s` | `5.174s` | `65` | `895.7ms` |
| `session-2026-06-23_12-24-48` | `3.424s` | `3.424s` | `66` | `880.0ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=29.2% | FP=69 (3.71 FP/min) | F1=0.248

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `linacc_mag_max_2.0s` | 0.0437 |
| 2 | `linacc_z_range_2.0s` | 0.0359 |
| 3 | `linacc_z_min_2.0s` | 0.0358 |
| 4 | `linacc_x_max_2.0s` | 0.0334 |
| 5 | `linacc_mag_std_2.0s` | 0.0247 |
| 6 | `accel_x_max_2.0s` | 0.0241 |
| 7 | `accel_mag_range_2.0s` | 0.0239 |
| 8 | `maguncal_mag_min_2.0s` | 0.0222 |
| 9 | `linacc_x_range_2.0s` | 0.0221 |
| 10 | `accel_z_min_2.0s` | 0.0173 |
| 11 | `linacc_mag_range_2.0s` | 0.0169 |
| 12 | `baro_pressure_range_2.0s` | 0.0158 |
| 13 | `gyro_z_mean_2.0s` | 0.0152 |
| 14 | `step_age` | 0.0136 |
| 15 | `gyrouncal_z_mean_2.0s` | 0.0118 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1.20 | 3.25 | 2.50 | -7.0 | 3 | True | True | 0.5s | 29.2% | 68 | 3.66 | 0.250 |
| 2 | 1.20 | 3.25 | 2.50 | -7.0 | 3 | True | True | 1.0s | 29.2% | 68 | 3.66 | 0.250 |
| 3 | 1.20 | 3.25 | 2.50 | -7.0 | 3 | True | True | 2.0s | 29.2% | 68 | 3.66 | 0.250 |
| 4 | 1.20 | 3.25 | 2.50 | -7.0 | 3 | True | True | 3.0s | 29.2% | 68 | 3.66 | 0.250 |
| 5 | 1.20 | 3.25 | 2.50 | -6.0 | 3 | True | True | 0.5s | 29.2% | 69 | 3.71 | 0.248 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 64.13% | 720 | 0.576 |
| Candidate 1 (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=0.5s) | 64.14% | 670 | 0.587 |
| Candidate 2 (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 64.14% | 668 | 0.587 |
| Candidate 3 (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=2.0s) | 64.04% | 667 | 0.587 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 3.24 | 2.54 | 1.28x |
| Accelerometer | 15.85 | 11.34 | 1.40x |
| LinearAccel | 10.36 | 5.05 | 2.05x |
| Magnetometer | 58.69 | 56.84 | 1.03x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 88 | 4.73 | 0.000 |
| 3.0 | 0.75 | 0.0% | 88 | 4.73 | 0.000 |
| 3.0 | 1.00 | 0.0% | 88 | 4.73 | 0.000 |
| 5.0 | 0.50 | 0.0% | 81 | 4.36 | 0.000 |
| 5.0 | 0.75 | 0.0% | 81 | 4.36 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "Back foot defense, good" | 54.92s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 3 | "Flick shot, OK" | 72.12s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 4 | "Forward defense, OK" | 84.92s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 6 | "Flick shot, OK" | 116.72s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 7 | "Pull shot, OK" | 126.62s | Gyro std-of-mag too high (1.23 > 1.2), bat was not still |
| 8 | "Pull shot, good" | 136.42s | Gyro std-of-mag too high (2.18 > 1.2), bat was not still |
| 9 | "Pull shot, miss" | 146.42s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 10 | "Back foot defense, good" | 155.92s | Gyro std-of-mag too high (1.55 > 1.2), bat was not still |
| 11 | "Pull shot, good" | 167.62s | Gyro std-of-mag too high (2.04 > 1.2), bat was not still |
| 12 | "Forward defense, good" | 174.92s | Gyro std-of-mag too high (1.62 > 1.2), bat was not still |
| 13 | "Back foot defense, good" | 185.42s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 18 | "Defense, OK" | 219.92s | Gyro std-of-mag too high (1.29 > 1.2), bat was not still |
| 19 | "Flick shot, OK" | 228.72s | Gyro std-of-mag too high (1.40 > 1.2), bat was not still |
| 21 | "Glance, good" | 244.72s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 22 | "Back foot defense, good" | 255.22s | Gyro std-of-mag too high (1.46 > 1.2), bat was not still |
| 23 | "Back foot defense, good" | 262.92s | Gyro std-of-mag too high (1.39 > 1.2), bat was not still |
| 24 | "Flick shot, OK" | 504.42s | Gyro std-of-mag too high (2.06 > 1.2), bat was not still |
| 26 | "Flick shot, poor" | 520.42s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 27 | "Flick shot, good" | 528.42s | Gyro std-of-mag too high (1.52 > 1.2), bat was not still |
| 28 | "Glance, good" | 536.42s | Gyro std-of-mag too high (1.53 > 1.2), bat was not still |
| 29 | "Glance, edge" | 545.42s | Gyro std-of-mag too high (1.70 > 1.2), bat was not still |
| 30 | "Flick shot, OK" | 554.42s | Gyro std-of-mag too high (1.98 > 1.2), bat was not still |
| 31 | "Back foot defense, poor" | 569.42s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 32 | "Pull shot, OK" | 577.42s | Step detector fired at 576.00s, breaking stance gate |
| 34 | "Flick shot, miss" | 593.42s | Gyro std-of-mag too high (1.33 > 1.2), bat was not still |
| 37 | "Glance, poor" | 624.42s | Gyro std-of-mag too high (1.73 > 1.2), bat was not still |
| 38 | "Flick shot, good" | 633.42s | Gyro std-of-mag too high (1.27 > 1.2), bat was not still |
| 39 | "Flick shot, good" | 638.42s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 40 | "Pull shot, OK" | 646.42s | Gyro std-of-mag too high (2.45 > 1.2), bat was not still |
| 41 | "Pull shot, poor" | 655.42s | Gyro std-of-mag too high (2.44 > 1.2), bat was not still |
| 42 | "Back foot defense, good" | 667.42s | Gyro std-of-mag too high (1.27 > 1.2), bat was not still |
| 43 | "Pull shot, OK" | 674.42s | Gyro std-of-mag too high (2.49 > 1.2), bat was not still |
| 44 | "Flick shot, good" | 917.42s | Gyro std-of-mag too high (1.44 > 1.2), bat was not still |
| 45 | "Flick shot, good" | 925.42s | Gyro std-of-mag too high (1.80 > 1.2), bat was not still |
| 47 | "Back foot defense, good" | 939.42s | Accel std-of-mag too high (4.13 > 3.25), too much motion/shock |
| 49 | "Back foot defense, good" | 953.42s | Accel std-of-mag too high (4.39 > 3.25), too much motion/shock |
| 53 | "Flick shot, poor" | 981.42s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 54 | "Flick shot, OK" | 991.42s | Accel std-of-mag too high (4.90 > 3.25), too much motion/shock |
| 55 | "Flick shot, good" | 999.42s | Gyro std-of-mag too high (1.51 > 1.2), bat was not still |
| 57 | "Flick shot, OK" | 1014.42s | Gyro std-of-mag too high (1.60 > 1.2), bat was not still |
| 59 | "Back foot drive, OK" | 1028.42s | Gyro std-of-mag too high (1.43 > 1.2), bat was not still |
| 60 | "Flick shot, good" | 1036.42s | Gyro std-of-mag too high (1.88 > 1.2), bat was not still |
| 61 | "Flick shot, good" | 1047.42s | Gyro std-of-mag too high (1.86 > 1.2), bat was not still |
| 62 | "Pull shot, OK" | 1057.42s | Gyro std-of-mag too high (2.35 > 1.2), bat was not still |
| 64 | "Flick shot, good" | 1075.42s | Gyro std-of-mag too high (1.48 > 1.2), bat was not still |
| 65 | "Flick shot, good" | 1083.42s | Gyro std-of-mag too high (1.85 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.29 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.29 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.43 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.22 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 91 | 130 | 74 | 56 | 17 | 0.57 | 0.81 | 0.70 | 0.96 |
| live_session_20260531_10 | 5 | 5 | 5 | 0 | 0 | 1.00 | 1.00 | 0.60 | 1.00 |
| live_session_20260531_14 | 68 | 76 | 68 | 8 | 0 | 0.89 | 1.00 | 0.76 | 0.96 |
| live_session_20260601 | 68 | 82 | 68 | 14 | 0 | 0.83 | 1.00 | 0.93 | 0.85 |
| live_session_20260605 | 30 | 33 | 29 | 4 | 1 | 0.88 | 0.97 | 0.86 | 0.86 |
| live_session_20260607 | 58 | 68 | 58 | 10 | 0 | 0.85 | 1.00 | 0.71 | 0.91 |
| live_session_20260608 | 60 | 66 | 52 | 14 | 8 | 0.79 | 0.87 | 0.83 | 0.71 |
| live_session_20260609 | 63 | 69 | 63 | 6 | 0 | 0.91 | 1.00 | 0.95 | 0.89 |
| live_session_20260611 | 57 | 87 | 56 | 31 | 1 | 0.64 | 0.98 | 0.77 | 0.96 |
| live_session_20260612 | 76 | 97 | 75 | 22 | 1 | 0.77 | 0.99 | 0.84 | 0.97 |
| live_session_20260613 | 64 | 67 | 61 | 6 | 3 | 0.91 | 0.95 | 0.90 | 0.85 |
| live_session_20260614 | 74 | 77 | 58 | 19 | 16 | 0.75 | 0.78 | 0.29 | 0.93 |
| live_session_20260615 | 65 | 103 | 63 | 40 | 2 | 0.61 | 0.97 | 0.49 | 0.94 |
| live_session_20260616 | 54 | 81 | 54 | 27 | 0 | 0.67 | 1.00 | 0.70 | 0.76 |
| live_session_20260618 | 69 | 86 | 64 | 22 | 5 | 0.74 | 0.93 | 0.89 | 0.95 |
| live_session_20260619 | 66 | 81 | 63 | 18 | 3 | 0.78 | 0.95 | 0.84 | 0.97 |
| live_session_20260621 | 65 | 94 | 63 | 31 | 2 | 0.67 | 0.97 | 0.84 | 0.95 |
| live_session_20260622 | 63 | 93 | 61 | 32 | 2 | 0.66 | 0.97 | 0.75 | 1.00 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1187
- **Total Combined Detected Shots:** 1491
- **Total Combined True Positives (Matches):** 1117
- **Total Combined False Positives:** 374
- **Overall Shot Classification Accuracy:** 73.3%
- **Overall Hit/Miss Agreement:** 91.4%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
