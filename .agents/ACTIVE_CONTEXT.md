# Active Context: Pitch Analytix Pro

This file defines the system objectives, feature backlog catalog, active technical approach, and verification methods.

---

## 🎯 System Objectives
*   **Active Phase**: Shot Detection Reliability — Random Forest Integration
*   **High-Level Vision**: Pitch Analytix Pro is a professional-grade cricket training companion utilizing Wear OS IMU sensors, local kinematics heuristics, mobile dashboards, and cloud transcription pipelines.
*   **"The Digital Pavilion" UI Spec**:
    *   **Background**: `#000000` (True Black for OLED screen battery conservation) / `#001B3D` (Deep Navy accents).
    *   **Primary Color**: `#58FF63` (Neon Green - High visibility, active tracking status).
    *   **Secondary Color**: `#BCD2FE` (Light Blue - Secondary metrics and averages).
    *   **Typography**: `Space Grotesk` (Modern, geometric, glanceable).
    *   **Roundness**: `Round Four` (Circular watch-optimized shapes).

---

## 🛠️ Technical Approach
*   **Wear OS Smartwatch**: Runs a foreground tracking service (`TrackerService`) with a partial wake lock to guarantee continuous 50Hz sensor logging. Rotates raw sensor vectors using quaternions and computes real-time metrics locally using `SwingDetector`. When raw logging is enabled (diagnostics mode), it dynamically registers and logs the full watch sensor stack (up to 15 standard Wear OS physical and virtual sensors) to CSV files using a dedicated background thread (`SensorLoggingThread`) to prevent system lag.
*   **Companion Android App**: Uses a Room SQLite database for offline storage. Receives timeline data packages via Google Play Services Wearable Data Layer API. Integrates exercise sessions into Samsung/Google Health Connect under the "Cricket" type.
*   **Python Automation Pipeline**: ADB automation (`automate_pipeline.py`) pulls sensor logs and phone audio. Transcribes audio directly using the Gemini API. Computes clock alignment using a **2D Joint Offset and Linear Drift Rate Optimization grid search** to calibrate any temporal speed mismatch between the watch and the recording device, snapping nartations precisely to the maximum gyroscope magnitude peaks.

---

## 📋 Feature Catalog & Backlog

| Feature ID | Feature Name | Description | Status | Verification Method |
|---|---|---|---|---|
| B-001 | Pull Shot Precision | Reduce false positive rate on Pull shot classification | Backlog | `SwingDetectorGroundTruthTest` |
| B-002 | Cover Drive Recall | Improve recall of Cover Drive shots | Backlog | `SwingDetectorGroundTruthTest` |
| B-003 | Speed Calibration | Fix speed anomalies on low-speed Cover Drives/Flicks | Backlog | `SwingDetectorGroundTruthTest` |
| B-004 | Active Watch Data | Implement active sensor logging for short-off-side/full-length | Backlog | Session collection check |
| B-013 | Power Shot Precision | Reduce POWER SHOT → PULL/HOOK misclassification. Session-2026-06-15 was ~90% power shots and scored only 40% accuracy, exposing severe underrepresentation of this class in training data. Retrain after collecting more power shot sessions. | Backlog | `SwingDetectorGroundTruthTest` |
| B-015 | Bat Type Extraction | Add bat type (Gray Nicolls Giant, Eye In, Game bat) extraction and stateful forward-filling to narration pipeline | **Completed** | Run `scratch/validate_bat_parsing.py` |
| B-016 | Blade & Launch Angles | Implement mathematical calculation of blade (face normal) angle and launch (loft/grounded) angle in Python and real-time WearOS Kotlin, persisting and rendering them on the Android app dashboard | **Completed** | Real-time calculations matching python prototype, passing unit tests, verified database and dashboard integration |
| B-017 | Video Session foundations | Implement 120fps video capture + passive watch sensor recording and ADB sync pull utility | **Completed** | Manual E2E on phone + watch; `video_analysis_poc.py` execution |
| B-018 | Direct Gemini & 2D Alignment | Revert to direct Gemini audio transcription and implement a 2D Joint Offset and Linear Drift Rate Optimization grid search to mathematically align narration timelines precisely to WearOS sensors. | **Completed** | Parity check and WearOS unit tests successful, 0 prediction mismatches. |
| B-019 | Improved Phone UI | Refactor Selected Session screen details grid, summaries, table breakdown, compact horizontal card metrics and time toggles | **Completed** | Gradle build and compilation verification |

---

## 🔖 Current Session State (session-2026-06-29_12-21-45)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-29_12-21-45`
*   **Audio File**: `narration_20260629_122136.m4a`
*   **Status**: Transcribed using direct Gemini 2.5 Flash audio transcription. Aligned using 2D Clock Offset and Linear Drift Rate Optimization grid search, yielding perfect chronological sequence and sub-second precision alignment across the 18-minute session. Renamed POWER SHOT to SLOG/slog across the codebase. 51 grounded power hits successfully identified and updated to 'Power drive' via `fix_power_drives.py`.


---

## 🧪 Verification & Testing

### 1. Automated Verification
*   **Kinematics Unit Tests**: Run `SwingDetectorTest` to verify math helpers, ring buffer logic, and state transitions.
*   **Ground Truth Scorecard**: Run [SwingDetectorGroundTruthTest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/test/java/com/mrpeel/cricketbattingtracker/ml/SwingDetectorGroundTruthTest.kt) to generate the performance scorecard against physical batting session datasets.

### 2. Manual E2E Simulation
*   **Launch Emulators**: Run `./start_emulators.sh` to boot Phone and Wear AVD targets.
*   **Visible E2E Script**: Execute `./run_visible_e2e.sh` to compile, deploy both apps, simulate shots, and verify synchronization.

### 3. Live Session Verification
*   Deploy `wear` debug APK to physical watch: `./deploy_physical.sh`
*   Record a session with `ENABLE_RAW_LOGGING=true` to get all 7 CSV files including `WatchGameOrientation.csv` and `WatchSteps.csv`
*   Run `automate_pipeline.py` and compare detection count to narrated shot count
