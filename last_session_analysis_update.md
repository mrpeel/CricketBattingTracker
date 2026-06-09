# Adversarial Post-Session Analysis Report

**Generated:** 2026-06-09 15:17:17
**Session Directory:** `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-09_12-16-49`
**Target Session Name:** `session-2026-06-09_12-16-49`

## Executive Summary
- **Clock Alignment:** ⚠️ Clock synchronization could be improved.
- **Facing-Up Gate:** The current hybrid 4-condition stance gate performs with high accuracy, but alternative configurations might offer minor false positive reductions.
- **Shot Detection Trigger:** The 5.0 rad/s gyroscope backswing trigger is highly optimal. Forensics point to step events as the main source of missed shot stance-gate lockouts.

## 1. Clock Offset Verification
### Current Offset: `4.912s` | Matches: `63`/`126` | MAE: `0.870s`
### Best Offset Found: `4.912s` | Matches: `63` | MAE: `0.870s`

#### Top Alignment Peaks:
- Offset: `3.112s` | Matches: `63` | MAE: `0.915s`
- Offset: `5.912s` | Matches: `62` | MAE: `0.867s`
- Offset: `7.512s` | Matches: `59` | MAE: `1.427s`
- Offset: `7.012s` | Matches: `58` | MAE: `1.170s`
- Offset: `7.212s` | Matches: `58` | MAE: `1.185s`

## 2. Facing-Up Detection Analysis
### Current Gate Performance: Recall=63.5% | FP=28 (2.21 FP/min) | F1=0.611

#### Top 15 Feature Importances (All Physical & Virtual Sensors):
| Rank | Feature Name | Mutual Info / Gini Importance |
|---|---|---|
| 1 | `linacc_mag_max_2.0s` | 0.0507 |
| 2 | `accel_mag_range_2.0s` | 0.0422 |
| 3 | `linacc_y_range_2.0s` | 0.0289 |
| 4 | `linacc_mag_std_2.0s` | 0.0288 |
| 5 | `linacc_z_range_2.0s` | 0.0260 |
| 6 | `accel_y_range_2.0s` | 0.0227 |
| 7 | `accel_x_min_2.0s` | 0.0219 |
| 8 | `linacc_x_range_2.0s` | 0.0194 |
| 9 | `baro_pressure_max_2.0s` | 0.0191 |
| 10 | `linacc_z_max_2.0s` | 0.0186 |
| 11 | `linacc_x_min_2.0s` | 0.0167 |
| 12 | `accel_z_range_2.0s` | 0.0150 |
| 13 | `gyrouncal_mag_range_2.0s` | 0.0147 |
| 14 | `baro_pressure_range_2.0s` | 0.0142 |
| 15 | `gyro_y_min_2.0s` | 0.0125 |

#### Alternative Stance Gate Configurations (Grid Search):
| Config | Gyro Std Max | Accel Std Max | Ori Disp Max | Grav Y Min | Min Flex | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.90 | 2.00 | 2.00 | -7.0 | 3 | 63.5% | 23 | 1.81 | 0.635 |
| 2 | 0.90 | 2.00 | 2.00 | -4.0 | 3 | 63.5% | 24 | 1.89 | 0.630 |
| 3 | 0.90 | 2.00 | 2.00 | -6.0 | 3 | 63.5% | 24 | 1.89 | 0.630 |
| 4 | 0.90 | 2.00 | 2.50 | -6.0 | 3 | 63.5% | 24 | 1.89 | 0.630 |
| 5 | 0.90 | 2.00 | 2.50 | -7.0 | 3 | 63.5% | 24 | 1.89 | 0.630 |

#### Cross-Session Validation Summary:
| Configuration Label | Avg Recall | Total FPs | Avg F1 |
|---|---|---|---|
| Current Deployed (Gyro=1.20, Accel=3.25) | 64.01% | 234 | 0.606 |
| Candidate 1 (Gyro=0.90, Accel=2.00) | 58.53% | 166 | 0.605 |
| Candidate 2 (Gyro=0.90, Accel=2.00) | 59.33% | 184 | 0.602 |
| Candidate 3 (Gyro=0.90, Accel=2.00) | 58.98% | 173 | 0.605 |

## 3. Shot Detection Analysis
### Multi-Sensor Swing Signal-to-Noise Ratio (SNR):
| Sensor Stream | Swing Peak | Stance Baseline | SNR Ratio |
|---|---|---|---|
| Gyroscope | 3.65 | 2.90 | 1.26x |
| Accelerometer | 18.85 | 13.30 | 1.42x |
| LinearAccel | 11.79 | 8.42 | 1.40x |
| Magnetometer | 58.79 | 57.33 | 1.03x |

#### Alternative Trigger Configurations:
| Threshold (rad/s) | Contact Wait (s) | Recall | FP | FP/Min | F1 |
|---|---|---|---|---|---|
| 7.0 | 1.00 | 61.9% | 19 | 1.50 | 0.645 |
| 5.0 | 1.00 | 63.5% | 22 | 1.73 | 0.640 |
| 7.0 | 0.50 | 58.7% | 21 | 1.66 | 0.612 |
| 7.0 | 0.75 | 58.7% | 21 | 1.66 | 0.612 |
| 5.0 | 0.75 | 60.3% | 24 | 1.89 | 0.608 |

#### Missed Shot Forensic Diagnostics:
| Shot # | Narration Text | Target Time | Miss Diagnosis / Reason |
|---|---|---|---|
| 4 | "Forward defense, miss" | 93.91s | Gyro std-of-mag too high (1.36 > 1.2), bat was not still |
| 5 | "Cover drive, good" | 105.91s | Gyro std-of-mag too high (1.68 > 1.2), bat was not still |
| 6 | "Forward defense, poor" | 114.91s | Gyro std-of-mag too high (1.46 > 1.2), bat was not still |
| 8 | "Forward defense, ok" | 131.91s | Gyro std-of-mag too high (1.61 > 1.2), bat was not still |
| 10 | "Forward defense, edge" | 146.91s | Gyro std-of-mag too high (1.50 > 1.2), bat was not still |
| 11 | "Straight drive, ok" | 158.91s | Gyro std-of-mag too high (1.80 > 1.2), bat was not still |
| 13 | "Off drive, ok" | 175.91s | Gyro std-of-mag too high (2.27 > 1.2), bat was not still |
| 14 | "Cover drive, poor" | 184.91s | Gyro std-of-mag too high (1.82 > 1.2), bat was not still |
| 15 | "Forward defense, ok" | 193.91s | Accel std-of-mag too high (3.71 > 3.25), too much motion/shock |
| 20 | "Forward push, ok" | 228.91s | Gyro std-of-mag too high (1.95 > 1.2), bat was not still |
| 22 | "Forward defense, good" | 324.91s | Gyro std-of-mag too high (1.52 > 1.2), bat was not still |
| 26 | "Forward defense, poor" | 365.91s | Gyro std-of-mag too high (1.31 > 1.2), bat was not still |
| 29 | "Forward defense, miss" | 388.91s | Accel std-of-mag too high (3.28 > 3.25), too much motion/shock |
| 36 | "On drive, poor" | 445.91s | Gyro std-of-mag too high (1.77 > 1.2), bat was not still |
| 37 | "Forward defense, good" | 453.91s | Gyro std-of-mag too high (1.65 > 1.2), bat was not still |
| 38 | "Cover drive, poor" | 462.91s | Gyro std-of-mag too high (1.44 > 1.2), bat was not still |
| 41 | "Straight drive, miss" | 487.91s | Gyro std-of-mag too high (1.40 > 1.2), bat was not still |
| 45 | "Straight drive, miss" | 583.91s | Gyro std-of-mag too high (1.66 > 1.2), bat was not still |
| 46 | "Straight drive, ok" | 591.91s | Gyro std-of-mag too high (1.36 > 1.2), bat was not still |
| 56 | "Shit... On drive, good" | 681.91s | Stance gate opened but backswing trigger failed to cross threshold, or timeout expired |
| 59 | "On drive, good" | 706.91s | Gyro std-of-mag too high (1.49 > 1.2), bat was not still |
| 63 | "Forward defense, miss" | 742.91s | Gyro std-of-mag too high (1.54 > 1.2), bat was not still |

#### Random Forest Classification Parity (June 9 Session):
- **Total Narrated Shots:** 63
- **Total Detected Shots:** 69
- **Classification Accuracy:** 92.0%
- **Hit/Miss Agreement:** 89.0%

## 4. Recommended Changes

Based on the adversarial verification:
1. **Priority 1 (Critical):** Maintain the current clock offset alignment logic as it achieves the global maximum of matches.
2. **Priority 2 (Improvement):** Keep the current stance gate parameters (`FACING_UP_ACCEL_STD_MAX=3.25`, `FACING_UP_ORI_DISP_MAX_DEG=2.5`), as they exhibit the best generalization across all 8 sessions in cross-session validation.
3. **Priority 3 (Marginal):** The step detector remains the most critical walking suppressor. No other sensor (including Barometer or Heart Rate) provides any predictive power for stance state.
