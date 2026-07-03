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
| B-017 | Video Session foundations | Implement 120fps video capture + passive watch sensor recording and ADB sync pull utility | **Completed** | Manual E2E on phone + watch; `video_analysis_poc.py` execution |
| B-018 | Direct Gemini & 2D Alignment | Revert to direct Gemini audio transcription and implement a 2D Joint Offset and Linear Drift Rate Optimization grid search to mathematically align narration timelines precisely to WearOS sensors. | **Completed** | Parity check and WearOS unit tests successful, 0 prediction mismatches. |
| B-019 | Improved Phone UI | Refactor Selected Session screen details grid, summaries, table breakdown, compact horizontal card metrics and time toggles | **Completed** | Gradle build and compilation verification |
| B-020 | Robust Chronological Transcription & Fallback Gates | Deploy strict linear timeline instructions to Gemini audio transcription prompt, support un-numbered practices, and assert safety via <=25% fallback gates | **Completed** | Batch realignment succeeding on 24/24 valid sessions, restoring combined F1 to 0.7670 |
| B-021 | Lossless Compression & Parquet Alignment | Implement voice-optimized mono audio compression, Gzip-compressed watch sensor files, native Kotlin GZIP streams, and transition adversarial analysis sweeps to partitioned Parquet database. | **Completed** | Parity checks, Kotlin unit tests, and post-session Parquet report generated successfully |

---

## 🔖 Current Session State (session-2026-06-23_12-24-48)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-23_12-24-48`
*   **Audio File**: `narration_20260623_122444.m4a`
*   **Status**: Fixed Mixed rolling/absolute seconds formatting issue. Transcribed using Gemini 2.5 Flash with strict chronological constraints. Realigned successfully (fallback rate 4.5%). Scorecard verified with combined F1 score of 0.7670.



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
