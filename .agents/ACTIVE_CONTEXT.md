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
*   **Python Automation Pipeline**: ADB automation (`automate_pipeline.py`) pulls sensor logs and phone audio, computes clock offsets automatically using the phone audio's filename and watch's `SYSTEM_START` timestamp (falling back to a 5-tap gyroscope/audio signature), calls the Gemini API (`gemini-3.5-flash`) for time-coded transcriptions, and segments sensor data into 6-second windowed CSV files for model training.

---

## 📋 Feature Catalog & Backlog

| Feature ID | Feature Name | Description | Status | Verification Method |
|---|---|---|---|---|
| B-001 | Pull Shot Precision | Reduce false positive rate on Pull shot classification | Backlog | `SwingDetectorGroundTruthTest` |
| B-002 | Cover Drive Recall | Improve recall of Cover Drive shots | Backlog | `SwingDetectorGroundTruthTest` |
| B-003 | Speed Calibration | Fix speed anomalies on low-speed Cover Drives/Flicks | Backlog | `SwingDetectorGroundTruthTest` |
| B-004 | Active Watch Data | Implement active sensor logging for short-off-side/full-length | Backlog | Session collection check |
| B-013 | Power Shot Precision | Reduce POWER SHOT → PULL/HOOK misclassification. Session-2026-06-15 was ~90% power shots and scored only 40% accuracy, exposing severe underrepresentation of this class in training data. Retrain after collecting more power shot sessions. | Backlog | `SwingDetectorGroundTruthTest` |
| B-008 | Stance Gate Optimization | Tune thresholds and timings to C: Moderate configuration to eliminate walking break FPs and timeout lockouts | **Completed** | E2E Simulation on session-2026-06-01_12-23-38 |
| B-009 | Random Forest Integration | Integrate scikit-learn Random Forest model into SwingDetector Kotlin logic | **Completed** | Parity test and physical scorecard alignment |
| B-010 | Clock Offset Optimization | Implement coarse-to-fine clock offset grid search in data collection pipeline | **Completed** | Verification check against all 7 trusted sessions |
| B-011 | Stance Gate Re-Optimization | Re-align all 7 sessions & grid-search optimal stance gate thresholds after sync fix. accel_std→3.25, ori_disp→2.5°, grav_y→-6.0, post_shot_guard→1.5s | **Completed** | 12/12 unit tests green, 95% avg recall, 26% FP reduction |
| B-012 | Adversarial Analysis Pipeline | Build a set of Python scripts to adversarially challenge clock offset, stance gate, and shot detection on raw logs | **Completed** | Run on June 9 session generating last_session_analysis_update.md |

---

## 🔖 Current Session State (session-2026-06-15_12-21-37)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-15_12-21-37`
*   **Audio File**: `narration_20260615_122132.m4a`
*   **Status**: Re-transcribed with `gemini-3.5-flash` using new `--force-retranscribe` flag. 65 segments aligned and saved. Session accuracy: **40.0%** (26/65 correct) — near-exclusively power shots causing heavy POWER SHOT → PULL/HOOK confusion. B-013 raised. Pipeline guard changes committed.
*   **Previous Session (session-2026-06-09_12-16-49)**: Retrained RF model on 443 swings across 8 sessions. All 12 Wear OS unit tests pass. Overall classification accuracy: **77.5%**.


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
