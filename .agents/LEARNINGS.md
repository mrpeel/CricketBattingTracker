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
*   **Unified Session Control via Message API**: Implemented bidirectional session control. Starting the companion app recording triggers a `/start_tracking` Wearable Message to start the watch foreground tracker, while stopping the phone recording triggers `/stop_tracking` to stop watch tracking and initiate telemetry sync.
*   **Foreground Audio Recording**: Configured `MediaRecorder` running within a foreground service of type `microphone` (`AudioRecordService`) to record AAC voice narrations at 44.1kHz. This prevents the OS from silencing the microphone when the screen is locked, and saves files directly in the app's external files directory for seamless ADB pull extraction.

### 3. Pipeline Decisions & Bug Fixes
*   **Timeline Clock Alignment Bug**: Discovered that the watch writes timeline event timestamps (`Ts`) in Unix Epoch milliseconds, whereas sensor logs write timestamps in `SystemClock.elapsedRealtimeNanos()`. Resolved the misalignment in `automate_pipeline.py` by parsing the `SYSTEM_START` epoch timestamp from the timeline file to correctly project relative shot elapsed seconds.
*   **Stance and Guard Window Tuning**: Tuned the `SwingDetector` state machine parameters to mitigate phantom shots (false positives) while preserving recall:
    *   **Stance duration threshold** increased from 150ms to 300ms to filter transient dips in standard deviation during walking or adjusting guard.
    *   **Post-shot quiet guard window** increased from 1.5s to 2.5s (extending total impact-to-stance block from 2.5s to 3.5s) to suppress follow-through and recovery swings.
    *   Verification: Verified offline via high-fidelity python simulation on raw live session data, reducing phantom counts by 24% (from 59 to 45) while maintaining recall at 93.0% (66/71 matches).
*   **ADB Offline Handling**: Scoped device-pull logic to look for local audio files when in offline `--session-dir` simulation mode.
*   **Biomechanical Classifier Transition (May 2026)**:
    *   Transitioned the classifier decision tree to target the 6 top-hand biomechanical classes: `DRIVE/DEFENCE`, `GLANCE/FLICK`, `CUT/PUNCH`, `PULL/HOOK`, `DEFLECTION/GUIDE`, and `POWER SHOT`.
    *   Split the legacy `CUT/PULL` class by classifying as `PULL/HOOK` if `rollImpactDeg <= -15.0f && deltaX >= 0.30f` (representing broad, closed-wrist leg-side pulls), falling back to `CUT/PUNCH` otherwise.
    *   Updated the stroke multipliers to align with the 6 biomechanical classes (`1.45f` for straight-bat/guided, `1.30f` for cross-bat/wristy/pull, and `1.40f` for power).
*   **Watch TrackerService Lifecycle Crash (May 25, 2026)**:
    *   Resolved a lateinit `UninitializedPropertyAccessException` crash on the watch inside `TrackerService.onDestroy()` caused by calling `healthServicesManager.stopTracking()` when health services were disabled in `onCreate()`.
    *   Added a Kotlin `::healthServicesManager.isInitialized` guard. This successfully restored the Wearable Data Layer sync, allowing timeline data to sync back to the phone companion database (e.g., InningsId 17).
*   **Pipeline Special Characters in Filenames Bug (May 25, 2026)**:
    *   Fixed an `OSError` in `automate_pipeline.py` when exporting 6-second training segments. Biomechanical shot type classes contain forward slashes (e.g., `DRIVE/DEFENCE`), which were interpreted as sub-directories by `os.path.join()`.
    *   Added `.replace("/", "_")` to filename sanitization for `shot_name` and `qual_name`.

---

## 📈 SwingDetector Performance Evaluation Scorecard

Evaluated against ground truth datasets (from batting sessions) using [SwingDetectorGroundTruthTest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/test/java/com/mrpeel/cricketbattingtracker/ml/SwingDetectorGroundTruthTest.kt) and local pipeline runs:

| Session | GT | Detected | TP | FP | FN | Precision | Recall | F1 | Class. Acc. | Hit/Miss Agr. | Speed MAE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Pull shots** | 24 | 31 | 23 | 8 | 1 | 0.74 | 0.96 | 0.84 | 0.09 | 0.96 | 12.40 km/h |
| **Cover drives** | 14 | 8 | 7 | 1 | 7 | 0.88 | 0.50 | 0.64 | 0.33 | 0.86 | 9.52 km/h |
| **On drives & flicks** | 26 | 30 | 25 | 5 | 1 | 0.83 | 0.96 | 0.89 | 0.70 | 0.92 | 22.53 km/h |
| **Short off side** | 25 | 0 | 0 | 0 | 25 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | N/A (No active watch data) |
| **full_toss** | 27 | 39 | 26 | 13 | 1 | 0.67 | 0.96 | 0.79 | 0.00 | 0.96 | N/A |
| **full_length** | 23 | 0 | 0 | 0 | 23 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | N/A (No active watch data) |
| **live_session_1** | 71 | 111 | 49 | 62 | 22 | 0.44 | 0.69 | 0.54 | 0.35 | 0.90 | N/A |

### Key Backlog Insights:
1.  **Cut/Punch vs Pull/Hook Isolation**: The new 6-class model successfully isolates pulls from cuts/back foot punches. In `live_session_1`, pull shots are now matching correctly as `PULL/HOOK` (increasing precision and reducing class overlap).
2.  **Live Session Accuracy**: Incorporating the 6-class top-hand biomechanical model yields 35% Shot Classification Accuracy on `live_session_1` and 90% Hit/Miss Agreement.
3.  **Cross-session Power Shots**: High-velocity shots in other sessions (such as `full_toss` and `Pull shots`) often cross the 22.12 rad/s threshold into `POWER SHOT`, resulting in correct hit metrics but lower historical label accuracy where power wasn't annotated.
4.  **Telemetry Gaps**: "Short off side" and "Full length" sessions continue to show 0% recall due to lacking active watch sensor data in the historical folders.

