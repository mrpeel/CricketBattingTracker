# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

### 1. Kinematics Decisions
*   **Calibration Event**: Settled on a **5-tap signature** (5 sharp taps/peaks played within 2.0 seconds) to synchronize phone audio narration with watch sensors. This successfully avoids events occurring naturally during a session.
*   **Bat Radius**: Standardized bat radius at `0.68m` for rotational-to-linear speed calculation.
*   **Stroke Multipliers**: Implemented stroke-specific multipliers (`1.45x` for straight-bat shots like Defence/Drive/Push, and `1.30x` for cross-bat shots like Sweep/Pull) to model bat speed calculations.
*   **Stance Quiet Guard**: Returning to stance requires `gyro_std < 0.9 rad/s` for at least `0.15s`. A `1.5s` post-shot guard window suppresses stance triggers during follow-through wobbles.

### 2. Android & Wear OS Discoveries
*   **Rotation Vector `qw` Reconstruction**: When Rotation Vector events return only 3 values `[qx, qy, qz]`, `qw` is dynamically reconstructed using:
    ```kotlin
    val qw = sqrt(max(0.0f, 1.0f - qx * qx - qy * qy - qz * qz))
    ```
*   **Partial Wake Lock**: Wear OS aggressively suspends background sensor listeners. We use a persistent Foreground Service with a `PARTIAL_WAKE_LOCK` to ensure continuous 50Hz sensor tracking when the watch face goes dark.
*   **Gravity Fallback**: When hardware gravity sensor is missing, a Low-Pass Filter (LPF) estimates gravity vectors from raw accelerometer data (active only when accel magnitude is under 15 m/s²).

---

## 📈 SwingDetector Performance Evaluation Scorecard

Evaluated against ground truth datasets (from batting sessions) using [SwingDetectorGroundTruthTest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/test/java/com/mrpeel/cricketbattingtracker/ml/SwingDetectorGroundTruthTest.kt):

| Session | GT | Detected | TP | FP | FN | Precision | Recall | F1 | Class. Acc. | Hit/Miss Agr. | Speed MAE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Pull shots** | 24 | 35 | 23 | 12 | 1 | 0.66 | 0.96 | 0.78 | 0.86 | 0.96 | 8.88 km/h |
| **Cover drives** | 14 | 9 | 8 | 1 | 6 | 0.89 | 0.57 | 0.70 | 1.00 | 0.88 | 16.57 km/h |
| **On drives & flicks** | 26 | 31 | 25 | 6 | 1 | 0.81 | 0.96 | 0.88 | 0.78 | 0.92 | 21.17 km/h |
| **Short off side** | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | N/A (No active watch data) |
| **full_toss** | 27 | 41 | 26 | 15 | 1 | 0.63 | 0.96 | 0.76 | 0.61 | 0.96 | N/A |
| **full_length** | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | N/A (No active watch data) |

### Key Backlog Insights:
1.  **Pull Shots**: High FP rate (12 false positives). Need to refine the decision tree branch for Pull Shots.
2.  **Cover Drives**: Low recall (6 false negatives). Need to adjust Stance-relative roll angle threshold or swing plane boundaries.
3.  **Low-Speed Calibration**: Speed errors are high on gentle/slow drives (true speed is ~10-15 km/h, but detected is ~45-75 km/h). Need to calibrate speed scaling coefficients at lower velocities.
4.  **Telemetry Gaps**: "Short off side" and "Full length" sessions have 0% recall because they currently lack watch IMU telemetry (using stationary fallback).
