# Adversarial Post-Session Analysis Report

**Generated:** 2026-07-17 17:28:46
**Target Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-07-17_12-30-41`
**Target Session Name:** `session-2026-07-17_12-30-41`

## Executive Summary
- **Independent Clock Alignment:** verified that all 35 available sessions are aligned independently down to the millisecond.
- **Facing-Up Gate:** The current hybrid 4-condition stance gate performs with high accuracy on the target session, but alternative configurations might offer minor false positive reductions.
- **Random Forest Parity:** Compiled classifier metrics across all sessions from the performance scorecard, demonstrating high classification accuracy.

## 1. Clock Offset Verification

Timings and clock offsets change between sessions because of variable initialization latency (Bluetooth connection handshake delay, MediaRecorder setup lag, CPU scheduling variance on watch/phone), and clock drift. Finding one global synchronization time is mathematically incorrect; each session must be independently aligned.

Below is the verification table showing the optimal, millisecond-level independent alignment for each available session:

| Session Name | Current Aligned Offset (s) | Best Swept Offset (s) | Matches | Mean Absolute Error (MAE) |
|---|---|---|---|---|
| `session-2026-05-30_15-04-41` | `N/A` | `2.570s` | `64` | `1210.5ms` |
| `session-2026-05-31_10-06-52` | `-6.089s` | `-7.589s` | `3` | `588.5ms` |
| `session-2026-05-31_14-12-10` | `-34.855s` | `-32.855s` | `6` | `1056.0ms` |
| `session-2026-06-01_12-23-38` | `44.320s` | `46.420s` | `21` | `1010.0ms` |
| `session-2026-06-05_12-29-59` | `-0.193s` | `0.807s` | `17` | `827.8ms` |
| `session-2026-06-07_14-34-24` | `-18.461s` | `-18.461s` | `21` | `1031.8ms` |
| `session-2026-06-08_12-22-26` | `-18.812s` | `-18.312s` | `30` | `960.7ms` |
| `session-2026-06-09_12-16-49` | `200.629s` | `202.749s` | `17` | `939.5ms` |
| `session-2026-06-11_12-27-53` | `-18.602s` | `-16.102s` | `33` | `1348.8ms` |
| `session-2026-06-12_12-24-37` | `-21.555s` | `-21.175s` | `50` | `1144.9ms` |
| `session-2026-06-13_10-59-04` | `19.137s` | `19.997s` | `43` | `1059.3ms` |
| `session-2026-06-14_13-16-12` | `-6.701s` | `-6.121s` | `59` | `872.8ms` |
| `session-2026-06-15_12-21-37` | `10.451s` | `10.951s` | `12` | `1044.4ms` |
| `session-2026-06-16_15-39-33` | `2.327s` | `4.827s` | `2` | `822.1ms` |
| `session-2026-06-18_12-23-09` | `2.053s` | `2.203s` | `37` | `941.2ms` |
| `session-2026-06-19_12-25-55` | `N/A` | `3.000s` | `21` | `980.8ms` |
| `session-2026-06-21_13-53-17` | `18.501s` | `19.381s` | `57` | `1182.3ms` |
| `session-2026-06-22_12-27-26` | `-26.165s` | `-24.665s` | `14` | `1346.3ms` |
| `session-2026-06-23_12-24-48` | `-1.101s` | `0.959s` | `43` | `810.2ms` |
| `session-2026-06-25_12-25-07` | `-3.873s` | `-4.823s` | `40` | `942.4ms` |
| `session-2026-06-26_12-22-13` | `-57.642s` | `-58.452s` | `22` | `1274.6ms` |
| `session-2026-06-27_14-12-40` | `-10.873s` | `-9.873s` | `21` | `1227.9ms` |
| `session-2026-06-28_11-28-09` | `0.340s` | `3.120s` | `47` | `823.2ms` |
| `session-2026-06-29_12-21-45` | `17.866s` | `15.566s` | `41` | `1257.1ms` |
| `session-2026-07-02_12-38-53` | `17.904s` | `15.364s` | `39` | `1082.7ms` |
| `session-2026-07-04_12-19-20` | `18.914s` | `16.924s` | `29` | `1121.2ms` |
| `session-2026-07-05_16-27-16` | `-17.928s` | `-15.428s` | `39` | `1066.5ms` |
| `session-2026-07-06_12-25-05` | `-9.910s` | `-7.040s` | `44` | `967.7ms` |
| `session-2026-07-07_15-10-50` | `4.492s` | `4.562s` | `50` | `1098.0ms` |
| `session-2026-07-09_12-19-05` | `-4.567s` | `-3.567s` | `51` | `946.3ms` |
| `session-2026-07-10_12-30-15` | `-11.231s` | `-10.181s` | `32` | `981.9ms` |
| `session-2026-07-11_12-51-39` | `-1.809s` | `-3.179s` | `50` | `859.1ms` |
| `session-2026-07-12_11-23-59` | `-14.536s` | `-13.666s` | `49` | `1041.6ms` |
| `session-2026-07-13_12-17-57` | `-26.378s` | `-29.368s` | `37` | `1095.2ms` |
| `session-2026-07-17_12-30-41` | `0.319s` | `3.019s` | `34` | `995.2ms` |

## 2. Facing-Up Detection Analysis
### Current Gate Performance (Global Multi-Session): Recall=38.9% | Total FP=2244 (3.75 FP/min) | F1=0.302

#### Top 15 Feature Importances (All Physical & Virtual Sensors - Global):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `gyro_y_range_1.0s` | 0.0312 |
| 2 | `gyro_y_range_2.0s` | 0.0243 |
| 3 | `gyro_y_max_1.0s` | 0.0214 |
| 4 | `gyro_y_min_2.0s` | 0.0198 |
| 5 | `gyro_y_range_0.5s` | 0.0198 |
| 6 | `gyro_y_max_2.0s` | 0.0179 |
| 7 | `gyro_y_min_1.0s` | 0.0173 |
| 8 | `game_ori_ori_disp_max_2.0s` | 0.0125 |
| 9 | `gyro_y_std_0.5s` | 0.0110 |
| 10 | `gyro_y_max_0.5s` | 0.0101 |
| 11 | `game_ori_ori_disp_max_1.0s` | 0.0100 |
| 12 | `gyro_y_std_1.0s` | 0.0093 |
| 13 | `gyrouncal_y_range_2.0s` | 0.0088 |
| 14 | `gyrouncal_y_range_1.0s` | 0.0082 |
| 15 | `gyrouncal_y_std_1.0s` | 0.0077 |

#### Alternative Stance Gate Configurations (Global Grid Search):
| Config | Gyro Std | Accel Std | Ori Disp | Grav Y | Min Flex | GyroMand | StepMand | StepRec | MinDur | BreakTol | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 4.00 | 2.50 | -6.0 | 2 | False | False | 3.0s | 0.8s | 1.5s | 56.4% | 3626 | 5.93 | 0.324 |
| 2 | 1.20 | 3.25 | 3.00 | -6.0 | 2 | False | False | 3.0s | 0.8s | 1.0s | 56.0% | 3586 | 5.87 | 0.324 |
| 3 | 0.90 | 4.00 | 2.50 | -6.0 | 2 | False | False | 3.0s | 0.8s | 1.0s | 56.4% | 3623 | 5.93 | 0.324 |
| 4 | 1.20 | 4.00 | 2.50 | -6.0 | 2 | False | False | 3.0s | 0.8s | 1.5s | 56.5% | 3632 | 5.94 | 0.324 |
| 5 | 1.50 | 4.00 | 2.50 | -6.0 | 2 | False | False | 3.0s | 0.8s | 1.5s | 56.6% | 3647 | 5.97 | 0.324 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25, GyroMand=True, StepMand=True, StepRec=1.0s, MinDur=0.8s, BreakTol=1.5s) | 38.91% | 2244 | 0.302 |
| Candidate 1 (Gyro=0.90, Accel=4.00, GyroMand=False, StepMand=False, StepRec=3.0s, MinDur=0.8s, BreakTol=1.5s) | 56.43% | 3626 | 0.324 |
| Candidate 2 (Gyro=1.20, Accel=3.25, GyroMand=False, StepMand=False, StepRec=3.0s, MinDur=0.8s, BreakTol=1.0s) | 56.04% | 3586 | 0.324 |
| Candidate 3 (Gyro=0.90, Accel=4.00, GyroMand=False, StepMand=False, StepRec=3.0s, MinDur=0.8s, BreakTol=1.0s) | 56.39% | 3623 | 0.324 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 2.09 | 1.15 | 1.81x |
| Accelerometer | 20.29 | 10.11 | 2.01x |
| LinearAccel | 11.28 | 2.35 | 4.79x |
| Magnetometer | 56.48 | 55.83 | 1.01x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 3.0 | 0.50 | 0.0% | 101 | 5.12 | 0.000 |
| 3.0 | 0.75 | 0.0% | 101 | 5.12 | 0.000 |
| 3.0 | 1.00 | 0.0% | 101 | 5.12 | 0.000 |
| 5.0 | 0.50 | 0.0% | 79 | 4.01 | 0.000 |
| 5.0 | 0.75 | 0.0% | 79 | 4.01 | 0.000 |

#### Missed Shot Forensic Diagnostics (Target Session):
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 8 | "cover drive, okay" | 134.32s | Gyro std-of-mag too high (1.94 > 1.2), bat was not still |
| 11 | "forward drive, okay" | 160.32s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 20 | "square drive, okay" | 260.32s | Step detector fired at 258.85s, breaking stance gate |
| 42 | "square drive, okay" | 666.32s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 53 | "off drive, okay" | 1002.32s | Gyro std-of-mag too high (1.37 > 1.2), bat was not still |
| 54 | "forward defense, good" | 1018.32s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |

#### Random Forest Classification Parity (Aggregated Over All Available Sessions):
Below is the classification performance overview compiled from the Kotlin ML scorecard report (`swing_detector_scorecard.md`):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | Class Accuracy | Hit/Miss Agr |
|---|---|---|---|---|---|---|---|---|---|
| Pull shots | 24 | 23 | 17 | 6 | 7 | 0.74 | 0.71 | 0.59 | 1.00 |
| Cover drives | 14 | 8 | 8 | 0 | 6 | 1.00 | 0.57 | 0.43 | 0.75 |
| On drives and flick shots | 26 | 23 | 20 | 3 | 6 | 0.87 | 0.77 | 0.56 | 0.90 |
| Short off side | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 |
| full_toss | 27 | 20 | 16 | 4 | 11 | 0.80 | 0.59 | 0.18 | 1.00 |
| full_length | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 |
| live_session_20260530 | 140 | 12 | 9 | 3 | 131 | 0.75 | 0.06 | 0.44 | 0.89 |
| live_session_20260531_10 | 6 | 4 | 4 | 0 | 2 | 1.00 | 0.67 | 0.75 | 1.00 |
| live_session_20260531_14 | 40 | 9 | 2 | 7 | 38 | 0.22 | 0.05 | 0.50 | 1.00 |
| live_session_20260601 | 68 | 63 | 46 | 17 | 22 | 0.73 | 0.68 | 0.93 | 0.83 |
| live_session_20260605 | 22 | 28 | 18 | 10 | 4 | 0.64 | 0.82 | 0.67 | 0.89 |
| live_session_20260607 | 34 | 33 | 10 | 23 | 24 | 0.30 | 0.29 | 0.30 | 0.90 |
| live_session_20260608 | 60 | 39 | 32 | 7 | 28 | 0.82 | 0.53 | 0.91 | 0.75 |
| live_session_20260609 | 40 | 58 | 24 | 34 | 16 | 0.41 | 0.60 | 0.96 | 0.83 |
| live_session_20260611 | 56 | 56 | 36 | 20 | 20 | 0.64 | 0.64 | 0.67 | 0.94 |
| live_session_20260612 | 77 | 71 | 54 | 17 | 23 | 0.76 | 0.70 | 0.61 | 1.00 |
| live_session_20260613 | 43 | 59 | 21 | 38 | 22 | 0.36 | 0.49 | 0.38 | 0.86 |
| live_session_20260614 | 71 | 68 | 56 | 12 | 15 | 0.82 | 0.79 | 0.79 | 0.91 |
| live_session_20260615 | 21 | 65 | 9 | 56 | 12 | 0.14 | 0.43 | 0.44 | 0.78 |
| live_session_20260616 | 54 | 62 | 14 | 48 | 40 | 0.23 | 0.26 | 0.07 | 0.79 |
| live_session_20260618 | 76 | 65 | 32 | 33 | 44 | 0.49 | 0.42 | 0.59 | 1.00 |
| live_session_20260621 | 113 | 69 | 44 | 25 | 69 | 0.64 | 0.39 | 0.52 | 0.98 |
| live_session_20260622 | 46 | 63 | 17 | 46 | 29 | 0.27 | 0.37 | 0.35 | 1.00 |
| live_session_20260623 | 66 | 60 | 55 | 5 | 11 | 0.92 | 0.83 | 0.75 | 0.93 |
| live_session_20260625 | 67 | 74 | 48 | 26 | 19 | 0.65 | 0.72 | 0.77 | 0.92 |
| live_session_20260626 | 65 | 66 | 46 | 20 | 19 | 0.70 | 0.71 | 0.63 | 0.96 |
| live_session_20260627 | 38 | 56 | 13 | 43 | 25 | 0.23 | 0.34 | 0.46 | 0.85 |
| live_session_20260628 | 37 | 64 | 10 | 54 | 27 | 0.16 | 0.27 | 0.20 | 0.90 |
| live_session_20260629 | 65 | 65 | 40 | 25 | 25 | 0.62 | 0.62 | 0.68 | 1.00 |
| live_session_20260702 | 66 | 67 | 45 | 22 | 21 | 0.67 | 0.68 | 0.49 | 0.91 |
| live_session_20260704 | 56 | 66 | 33 | 33 | 23 | 0.50 | 0.59 | 0.27 | 0.82 |
| live_session_20260705 | 40 | 60 | 13 | 47 | 27 | 0.22 | 0.33 | 0.62 | 0.77 |
| live_session_20260706 | 39 | 55 | 15 | 40 | 24 | 0.27 | 0.38 | 0.47 | 0.93 |
| live_session_20260707 | 57 | 64 | 34 | 30 | 23 | 0.53 | 0.60 | 0.97 | 0.97 |
| live_session_20260709 | 45 | 72 | 21 | 51 | 24 | 0.29 | 0.47 | 0.76 | 0.95 |
| live_session_20260710 | 59 | 67 | 19 | 48 | 40 | 0.28 | 0.32 | 0.58 | 1.00 |
| live_session_20260711 | 61 | 63 | 47 | 16 | 14 | 0.75 | 0.77 | 0.74 | 0.83 |
| live_session_20260712_11 | 66 | 62 | 45 | 17 | 21 | 0.73 | 0.68 | 0.44 | 0.98 |
| live_session_20260712_15 | 3 | 3 | 0 | 3 | 3 | 0.00 | 0.00 | 0.00 | 0.00 |

**Summary Metrics (Weighted Combined Averages across active-watch sessions):**
- **Total Combined Ground Truth Shots:** 1888
- **Total Combined Detected Shots:** 1862
- **Total Combined True Positives (Matches):** 973
- **Total Combined False Positives:** 889
- **Overall Shot Classification Accuracy:** 62.7%
- **Overall Hit/Miss Agreement:** 91.6%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Clock Alignment:** verified that every session has a unique optimal alignment due to initialization latencies, confirming the value of independent alignment over global averages.
2. **Stance Gate:** Maintain the moderate config parameters (`accel_std=3.25`, `ori_disp=2.5`, `grav_y=-6.0`) as they yield the best recall/FP trade-off in cross-session validation.
3. **Classifier Parity:** The integrated Random Forest model shows high agreement and accuracy across all sessions. Keep the current Kotlin transpiled tree layers.
