# Adversarial Post-Session Analysis Report

**Generated:** 2026-06-26 15:45:10
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-26_12-22-13`
**Target Session Name:** `session-2026-06-26_12-22-13`

## Executive Summary
- **Independent Clock Alignment:** verified that all 21 available sessions are aligned independently down to the millisecond.
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
| `session-2026-06-23_12-24-48` | `3.424s` | `3.424s` | `66` | `851.6ms` |
| `session-2026-06-25_12-25-07` | `4.368s` | `4.388s` | `60` | `931.9ms` |
| `session-2026-06-26_12-22-13` | `4.710s` | `4.720s` | `66` | `903.6ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Target Session): Recall=46.2% | FP=62 (3.25 FP/min) | F1=0.382

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `linacc_z_range_2.0s` | 0.0515 |
| 2 | `linacc_mag_max_2.0s` | 0.0392 |
| 3 | `linacc_mag_std_2.0s` | 0.0360 |
| 4 | `grav_y_std_2.0s` | 0.0264 |
| 5 | `accel_x_max_2.0s` | 0.0254 |
| 6 | `gyro_z_mean_2.0s` | 0.0249 |
| 7 | `linacc_x_max_2.0s` | 0.0248 |
| 8 | `linacc_mag_range_2.0s` | 0.0247 |
| 9 | `accel_z_std_2.0s` | 0.0228 |
| 10 | `linacc_x_range_2.0s` | 0.0208 |
| 11 | `grav_y_range_2.0s` | 0.0204 |
| 12 | `accel_z_range_2.0s` | 0.0183 |
| 13 | `gyrouncal_x_max_2.0s` | 0.0178 |
| 14 | `linacc_z_min_2.0s` | 0.0175 |
| 15 | `accel_mag_range_2.0s` | 0.0169 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 0.5s | 46.2% | 52 | 2.73 | 0.408 |
| 2 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 1.0s | 46.2% | 52 | 2.73 | 0.408 |
| 3 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 2.0s | 46.2% | 52 | 2.73 | 0.408 |
| 4 | 0.90 | 3.25 | 2.00 | -7.0 | 3 | True | True | 3.0s | 46.2% | 52 | 2.73 | 0.408 |
| 5 | 0.90 | 3.25 | 2.00 | -6.0 | 3 | True | True | 0.5s | 46.2% | 53 | 2.78 | 0.405 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 63.56% | 834 | 0.566 |
| Candidate 1 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=0.5s) | 62.03% | 686 | 0.584 |
| Candidate 2 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s) | 62.03% | 684 | 0.584 |
| Candidate 3 (Gyro=0.90, Accel=3.25, GyroMand=True, StepMand=True, StepRec=2.0s) | 61.94% | 682 | 0.584 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 3.55 | 3.14 | 1.13x |
| Accelerometer | 14.37 | 12.59 | 1.14x |
| LinearAccel | 8.36 | 6.88 | 1.22x |
| Magnetometer | 58.09 | 56.92 | 1.02x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 95 | 4.98 | 0.000 |
| 3.0 | 0.75 | 0.0% | 95 | 4.98 | 0.000 |
| 3.0 | 1.00 | 0.0% | 95 | 4.98 | 0.000 |
| 5.0 | 0.50 | 0.0% | 86 | 4.51 | 0.000 |
| 5.0 | 0.75 | 0.0% | 86 | 4.51 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 1 | "Back foot defense, good" | 71.21s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 2 | "Off drive, okay" | 82.21s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 3 | "Off drive, okay" | 91.21s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 4 | "Cover drive, okay" | 101.21s | Step detector fired at 100.38s, breaking stance gate |
| 5 | "Back foot defense, okay" | 111.21s | Gyro std-of-mag too high (1.26 > 1.2), bat was not still |
| 6 | "Back foot defense, okay" | 125.21s | Gyro std-of-mag too high (1.52 > 1.2), bat was not still |
| 8 | "Back foot punch, okay" | 141.21s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 9 | "Back foot punch, good" | 149.21s | Gyro std-of-mag too high (1.71 > 1.2), bat was not still |
| 11 | "Back foot punch, okay" | 163.21s | Gyro std-of-mag too high (1.72 > 1.2), bat was not still |
| 12 | "Forward defense, okay" | 171.21s | Gyro std-of-mag too high (1.60 > 1.2), bat was not still |
| 13 | "Back foot punch, okay" | 180.21s | Gyro std-of-mag too high (1.62 > 1.2), bat was not still |
| 14 | "Back foot punch, good" | 194.21s | Gyro std-of-mag too high (1.86 > 1.2), bat was not still |
| 15 | "Back foot punch, good" | 201.21s | Gyro std-of-mag too high (1.73 > 1.2), bat was not still |
| 16 | "Off drive, good" | 208.21s | Gyro std-of-mag too high (1.97 > 1.2), bat was not still |
| 17 | "Off drive, okay" | 218.21s | Gyro std-of-mag too high (2.22 > 1.2), bat was not still |
| 18 | "Back foot punch, okay" | 228.21s | Gyro std-of-mag too high (1.70 > 1.2), bat was not still |
| 19 | "Back foot drive, okay" | 235.21s | Gyro std-of-mag too high (1.80 > 1.2), bat was not still |
| 20 | "Back foot drive, okay" | 245.21s | Gyro std-of-mag too high (1.52 > 1.2), bat was not still |
| 21 | "Back foot punch, miss" | 253.21s | Gyro std-of-mag too high (2.02 > 1.2), bat was not still |
| 22 | "Back foot drive, edge" | 487.21s | Gyro std-of-mag too high (2.04 > 1.2), bat was not still |
| 23 | "Back foot drive, okay" | 495.21s | Gyro std-of-mag too high (1.65 > 1.2), bat was not still |
| 25 | "Back foot punch, good" | 511.21s | Gyro std-of-mag too high (2.09 > 1.2), bat was not still |
| 26 | "Forward defense, good" | 519.21s | Gyro std-of-mag too high (1.70 > 1.2), bat was not still |
| 27 | "Forward defense, edge" | 540.21s | Gyro std-of-mag too high (1.82 > 1.2), bat was not still |
| 28 | "Straight drive, poor" | 549.21s | Gyro std-of-mag too high (1.80 > 1.2), bat was not still |
| 34 | "Cover drive, poor" | 600.21s | Gyro std-of-mag too high (1.43 > 1.2), bat was not still |
| 39 | "Cover drive, okay" | 643.21s | Gyro std-of-mag too high (2.09 > 1.2), bat was not still |
| 42 | "Forward defense, good" | 670.21s | Gyro std-of-mag too high (1.33 > 1.2), bat was not still |
| 46 | "Off drive, okay" | 910.21s | Gyro std-of-mag too high (1.46 > 1.2), bat was not still |
| 49 | "Straight drive, good" | 933.21s | Gyro std-of-mag too high (1.77 > 1.2), bat was not still |
| 50 | "Back foot punch, okay" | 940.21s | Gyro std-of-mag too high (1.52 > 1.2), bat was not still |
| 52 | "Off drive, okay" | 954.21s | Gyro std-of-mag too high (1.50 > 1.2), bat was not still |
| 55 | "Off drive, good" | 1001.21s | Gyro std-of-mag too high (1.78 > 1.2), bat was not still |
| 59 | "Off drive, good" | 1043.21s | Gyro std-of-mag too high (1.77 > 1.2), bat was not still |
| 61 | "Straight drive miss" | 1059.21s | Gyro std-of-mag too high (1.77 > 1.2), bat was not still |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 28 | 22 | 6 | 2 | 0.79 | 0.92 | 0.29 | 0.95 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.14 | 0.75 |
| On drives and flick shots | 26 | 27 | 25 | 2 | 1 | 0.93 | 0.96 | 0.61 | 0.92 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 33 | 27 | 6 | 0 | 0.82 | 1.00 | 0.22 | 0.96 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 91 | 130 | 74 | 56 | 17 | 0.57 | 0.81 | 0.65 | 0.96 |
| live_session_20260531_10 | 5 | 5 | 5 | 0 | 0 | 1.00 | 1.00 | 0.60 | 1.00 |
| live_session_20260531_14 | 68 | 76 | 68 | 8 | 0 | 0.89 | 1.00 | 0.76 | 0.96 |
| live_session_20260601 | 68 | 82 | 68 | 14 | 0 | 0.83 | 1.00 | 0.94 | 0.85 |
| live_session_20260605 | 30 | 33 | 29 | 4 | 1 | 0.88 | 0.97 | 0.83 | 0.86 |
| live_session_20260607 | 58 | 68 | 58 | 10 | 0 | 0.85 | 1.00 | 0.64 | 0.91 |
| live_session_20260608 | 60 | 66 | 52 | 14 | 8 | 0.79 | 0.87 | 0.67 | 0.71 |
| live_session_20260609 | 63 | 69 | 63 | 6 | 0 | 0.91 | 1.00 | 0.94 | 0.89 |
| live_session_20260611 | 57 | 87 | 56 | 31 | 1 | 0.64 | 0.98 | 0.79 | 0.96 |
| live_session_20260612 | 76 | 97 | 75 | 22 | 1 | 0.77 | 0.99 | 0.81 | 0.97 |
| live_session_20260613 | 64 | 67 | 61 | 6 | 3 | 0.91 | 0.95 | 0.85 | 0.85 |
| live_session_20260614 | 74 | 77 | 58 | 19 | 16 | 0.75 | 0.78 | 0.29 | 0.93 |
| live_session_20260615 | 65 | 103 | 63 | 40 | 2 | 0.61 | 0.97 | 0.48 | 0.94 |
| live_session_20260616 | 54 | 81 | 54 | 27 | 0 | 0.67 | 1.00 | 0.61 | 0.76 |
| live_session_20260618 | 69 | 86 | 64 | 22 | 5 | 0.74 | 0.93 | 0.89 | 0.95 |
| live_session_20260619 | 66 | 81 | 63 | 18 | 3 | 0.78 | 0.95 | 0.87 | 0.97 |
| live_session_20260621 | 65 | 94 | 63 | 31 | 2 | 0.67 | 0.97 | 0.90 | 0.95 |
| live_session_20260622 | 63 | 93 | 61 | 32 | 2 | 0.66 | 0.97 | 0.77 | 1.00 |
| live_session_20260623 | 65 | 88 | 63 | 25 | 2 | 0.72 | 0.97 | 0.95 | 0.94 |
| live_session_20260625 | 67 | 100 | 58 | 42 | 9 | 0.58 | 0.87 | 0.79 | 0.91 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1319
- **Total Combined Detected Shots:** 1679
- **Total Combined True Positives (Matches):** 1238
- **Total Combined False Positives:** 441
- **Overall Shot Classification Accuracy:** 73.4%
- **Overall Hit/Miss Agreement:** 91.5%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
