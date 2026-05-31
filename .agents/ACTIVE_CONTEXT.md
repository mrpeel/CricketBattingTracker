# Active Context: Pitch Analytix Pro

This file defines the system objectives, feature backlog catalog, active technical approach, and verification methods.

---

## 🎯 System Objectives
*   **Active Phase**: Shot Detection Reliability — Facing-Up Anchor Implementation
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
*   **Python Automation Pipeline**: ADB automation (`automate_pipeline.py`) pulls sensor logs and phone audio, computes clock offsets automatically using the phone audio's filename and watch's `SYSTEM_START` timestamp (falling back to a 5-tap gyroscope/audio signature), calls the Gemini API (`gemini-3.5-flash`) for time-coded transcriptions, and segments sensor data into 6-second windowed CSV files for model training.

---

## 📋 Feature Catalog & Backlog

| Feature ID | Feature Name | Description | Status | Verification Method |
|---|---|---|---|---|
| F-012 | Stance Break Tolerance | 1.2s break-tolerance window handles transient failures (bat rocking) during stance lock | **Completed** | SwingDetectorTest unit tests |
| B-001 | Pull Shot Precision | Reduce false positive rate on Pull shot classification | Backlog | `SwingDetectorGroundTruthTest` |
| B-002 | Cover Drive Recall | Improve recall of Cover Drive shots | Backlog | `SwingDetectorGroundTruthTest` |
| B-003 | Speed Calibration | Fix speed anomalies on low-speed Cover Drives/Flicks | Backlog | `SwingDetectorGroundTruthTest` |
| B-004 | Active Watch Data | Implement active sensor logging for short-off-side/full-length | Backlog | Session collection check |
| B-005 | Companion Recording | Migrate audio recorder & transcription to App UI | Completed | E2E verification |
| B-006 | Watch Teardown Crash | Fix lateinit healthServicesManager crash on onDestroy | Completed | E2E verification |
| B-007 | Transcription Reliability | Implement structured Pydantic response schema + targeted prompts on Gemini 3.5 Flash for audio narration parsing | **Completed** | Pipeline re-run producing correct 69/69 shot count for 20-min session |
| F-013 | Full Watch Sensor Stack Logging | Background logging of up to 15 physical/virtual Wear OS sensors when raw logging/diagnostics is enabled | **Completed** | E2E simulation verify 11 CSV files |

---

## 🔖 Current Session State (session-2026-05-31_14-12-10)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-05-31_14-12-10`
*   **Audio File**: `narration_20260531_141205.m4a`
*   **Status**: Fully completed implementation of the wake-up step sensors and the hybrid M-of-N stance gate logic (Configuration H9). The timing failure under tighter limits was resolved by expanding the break tolerance window to 1.5s. All 10 Wear OS unit tests passed, and offline simulation confirmed 78.3% recall with 1.68 FPs/min.
*   **Previous Session (session-2026-05-31_10-06-52)**: Checked stance check alignment, indicating 4/5 locks passed.


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
