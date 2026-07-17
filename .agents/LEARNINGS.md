# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

75. **Kotlin Integration and Verification of 14-Feature Segmented Model (July 10, 2026)**:
    *   **The Problem**: We needed to implement the optimal 14-feature 3-segment feature-extraction logic in Kotlin, regenerate the transpiled Random Forest model (`GeneratedForest.kt`), and verify parity against the Python implementation.
    *   **The Solution**: Modified `SwingDetector.kt` to partition the swing window relative to `contactTime` into Segment 1 (`[-0.80s, -0.20s]`), Segment 2 (`[-0.20s, -0.05s]`), and Segment 3 (`[-0.05s, +0.30s]`), extracting the 14 segmented features. Manually ran `generate_kotlin_forest.py` to bootstrap compile the new 14-property `SwingFeatures` class definition, then executed `model_update_pipeline.py`.
    *   **Result**: Re-run of all Wear OS unit tests and `SwingDetectorRandomForestAlignmentTest.kt` passed successfully with **0 mismatches** against Python predictions, validating exact feature extraction and mathematical prediction parity.

76. **Global Multi-Session Adversarial Sweep Refactoring (July 10, 2026)**:
    *   **The Problem**: The adversarial stance-gate parameter search was previously targeted at and optimized for a single session, which limited generalization and failed to utilize the full breadth of the historical dataset.
    *   **The Solution**: Refactored `adversarial_facing_up_search.py` and `adversarial_analysis.py` to run globally. The scripts now load all 31 sessions with ground truth shots, apply stance stress-testing to all of them, merge all session datasets to compute feature importances, and perform the parameter grid search sweep across all available session datasets.
    *   **Result**: Successfully executed E2E, yielding robust global optimal parameters and generating the report showing metrics aggregated across all available data.

77. **Stance Gate Segment-Based Feature Comparison (July 10, 2026)**:
    *   **The Problem**: Point-in-time features used for stance gating (`gyro_std`, `accel_std`, `ori_disp`, `mean_grav_y` computed over a single window ending at `t`) are susceptible to false wiggles or step movements.
    *   **The Solution**: Created a script `scratch/compare_facing_up_features.py` to extract segment-based features (splitting the 2.0s history into segment 1 `[-2.0s, -1.0s]` and segment 2 `[-1.0s, 0.0s]`) across 31 sessions under stressed stance conditions. Evaluated point-in-time vs segment features using depth-4 Decision Tree classifiers.
    *   **Result**: Segment-based feature extraction achieved a **+0.0919 F1-score improvement** (0.4416 vs 0.3497 PIT) and raised stance gate recall from **21.57% to 29.51%** (+7.94% recall), proving that capturing temporal dynamics over multiple segments significantly improves stance detection accuracy.

78. **ADB Connection Timeout Resilience (July 11, 2026)**:
    *   **The Problem**: Typos in command arguments (e.g. `--watch-ip 92.168.1.79:45271` instead of `192.168.1.79:45271`) or network routing errors caused `adb connect` to hang indefinitely, blocking pipeline automation.
    *   **The Solution**: Added `timeout=8` and exception handling around the `subprocess.run(["adb", "connect", watch_ip], ...)` call in `check_adb_devices` within `automate_pipeline.py`.
    *   **Result**: The script now times out gracefully after 8 seconds and continues the checks instead of hanging forever, immediately exposing the connection/IP failure to the user.

79. **Integrated Camera viewfinder, Zoom controls, and Camera direction flip (July 12, 2026)**:
    *   **The Problem**: The app ran a headless background service `VideoRecordService` with a fixed rear-facing camera configuration, lacking target controls for direction aiming, zoom setups, or frame rate adjustments before commencing batting sessions.
    *   **The Solution**:
        *   Introduced a live setup screen `VideoSetupScreen` utilizing CameraX's `PreviewView` bound to Compose lifecycle controls.
        *   Added UI configuration interfaces: a camera swap toggle button, a linear zoom slider (`0.0f..1.0f`) mapping to `cameraControl.setLinearZoom()`, and a segmented target capture FPS selector (120 FPS / 60 FPS / 30 FPS).
        *   Saved state choices in local SharedPreferences and propagated settings via Intent extras to `VideoRecordService` at start.
        *   Passed border modifier compilation constraints by cleanly importing `androidx.compose.foundation.border`.
    *   **Result**: Gradle `assembleDebug` successfully compiles, and video setup settings cleanly hook E2E into the CameraX provider lifecycle.

80. **Polar Sense Bottom Hand Refinement and Magnetometer Integration (July 13, 2026)**:
    *   **The Problem**: Shot classification and bat speed metrics were generated solely based on top-hand (watch) dynamics, ignoring bottom-hand telemetry. Additionally, Polar Sense magnetometer readings were uncaptured, and today's session saved empty files because `PolarSenseService` connected to the sensor but never started the data streams.
    *   **The Solution**:
        *   Enabled 52Hz magnetometer streaming in `PolarSenseManager` and saved telemetry to `PolarMagnetometer.csv`.
        *   Resolved the auto-streaming bug by adding a check inside `bleSdkFeatureReady` to trigger `startStreaming()` automatically once the SDK signals the `ONLINE_STREAMING` feature is ready.
        *   Added Python grid-search optimization pipeline (`optimize_shot_enhancement.py`) to determine optimal bottom-hand reclassification boundaries using ground-truth sessions, outputting them into generated Kotlin configuration classes.
        *   Refined shot types (e.g., reclassifying straight drives to power drives under bottom-hand dominance) and adjusted bat speed dynamically in `ShotEnhancementEngine`.
        *   Updated Room DB schema to version 9 (migration `MIGRATION_8_9`) to store magnetometer metrics, and enhanced UI badges to display dominance and release timing.
    *   **Result**: Automated grid search successfully compiles and runs, generating valid thresholds, and the companion app supports robust dual-sensor biomechanics with streaming verified end-to-end.

81. **Phone Audio Recording Selection Logic (July 17, 2026)**:
    *   **The Problem**: The ADB automation pipeline (`automate_pipeline.py`) rejected valid phone audio recordings when run more than 30 minutes after the batting session. This occurred because `session_time` was computed from the local file modification time of `WatchGyroscope.csv` (which gets updated to the current time when files are freshly pulled to the local directory), rather than the actual time the session occurred.
    *   **The Solution**: Updated `pull_audio_from_phone` to parse the session's actual start time directly from the folder name (e.g. `session-2026-07-17_12-30-41`) using a regex pattern, with a fallback to the file modification time if parsing fails.
    *   **Result**: Valid recordings are correctly matched and pulled regardless of how long after the session the automation script is run. Today's session was successfully completed E2E.
