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
*   **Wear OS Smartwatch**: Runs a foreground tracking service (`TrackerService`) with a partial wake lock to guarantee continuous 50Hz sensor logging. Rotates raw sensor vectors using quaternions and computes real-time metrics locally using `SwingDetector`. Now records 7 data streams: Accel, Gyro, Gravity, Rotation Vector, **Game Rotation Vector** (magnetometer-free), **Step Detector events**, and Heart Rate.
*   **Companion Android App**: Uses a Room SQLite database for offline storage. Receives timeline data packages via Google Play Services Wearable Data Layer API. Integrates exercise sessions into Samsung/Google Health Connect under the "Cricket" type.
*   **Python Automation Pipeline**: ADB automation (`automate_pipeline.py`) pulls sensor logs and phone audio, computes clock offsets automatically using the phone audio's filename and watch's `SYSTEM_START` timestamp (falling back to a 5-tap gyroscope/audio signature), calls the Gemini API (`gemini-2.5-flash`) for time-coded transcriptions, and segments sensor data into 6-second windowed CSV files for model training.

---

## 📋 Feature Catalog & Backlog

| Feature ID | Feature Name | Description | Status | Verification Method |
|---|---|---|---|---|
| F-001 | Continuous Sampling | Listen to Accel/Gyro/Gravity/Rotation Vector at 50Hz | Completed | Unit Tests & Emulation |
| F-002 | Foreground Service | Keep `TrackerService` running when screen is dark | Completed | Physical target verification |
| F-003 | Wearable Sync | Timeline JSON sync over Wearable Data Layer API | Completed | E2E Simulation |
| F-004 | SQLite Persistence | Local Room database storage on the phone companion | Completed | Phone UI verification |
| F-005 | Health Connect Sync | Push Innings and Heart Rate profiles under Cricket type | Completed | Health Connect client check |
| F-006 | Narration Pipeline | Pull files, run auto-start sync (5-tap fallback), transcribe via Gemini | Completed | Running pipeline script |
| F-007 | Companion Audio Recording | Companion App Audio Recording & Local Transcription Integration | Completed | E2E verification |
| F-008 | Facing-Up Anchor | 4-condition facing-up gate anchors all shot detection to a confirmed guard stance | **Completed** | GroundTruthTest + next live session |
| F-009 | Game Rotation Vector | Switch primary bat orientation quaternion to TYPE_GAME_ROTATION_VECTOR (no magnetometer) | **Completed** | Build passes; next live session |
| F-010 | Step Detector Integration | TYPE_STEP_DETECTOR feeds a walking kill-switch into the facing-up gate | **Completed** | Build passes; next live session |
| F-011 | Watch UI Stance Indicator | Pulsing 'Facing Up' badge on Wear OS UI for real-time stance confirmation | **Completed** | Manual stance check on watch screen |
| F-012 | Stance Break Tolerance | 1.2s break-tolerance window handles transient failures (bat rocking) during stance lock | **Completed** | SwingDetectorTest unit tests |
| B-001 | Pull Shot Precision | Reduce false positive rate on Pull shot classification | Backlog | `SwingDetectorGroundTruthTest` |
| B-002 | Cover Drive Recall | Improve recall of Cover Drive shots | Backlog | `SwingDetectorGroundTruthTest` |
| B-003 | Speed Calibration | Fix speed anomalies on low-speed Cover Drives/Flicks | Backlog | `SwingDetectorGroundTruthTest` |
| B-004 | Active Watch Data | Implement active sensor logging for short-off-side/full-length | Backlog | Session collection check |
| B-005 | Companion Recording | Migrate audio recorder & transcription to App UI | Completed | E2E verification |
| B-006 | Watch Teardown Crash | Fix lateinit healthServicesManager crash on onDestroy | Completed | E2E verification |
| B-007 | Transcription Reliability | Implement structured Pydantic response schema + targeted prompts on Gemini 3.5 Flash for audio narration parsing | **Completed** | Pipeline re-run producing correct 69/69 shot count for 20-min session |

---

## 🔖 Current Session State (session-2026-05-29_12-27-17)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-05-29_12-27-17`
*   **Audio File**: `narration_20260529_122712.m4a`
*   **Narrations Cache**: `narrations_raw.json` — contains 69 narrated shots with accurate timestamps.
*   **Ground Truth CSV**: `ground_truth_aligned.csv` — 69 shots aligned to sensor peaks.
*   **Primary Problem Diagnosed**: Low shot recall (53.6% missed shots) due to too-strict orientation stability limit (0.5°) and 1.5s lock duration requirement.
*   **Resolution**: Decoupled standard deviation metrics (1.0s window) from orientation stability (500ms window), loosened limits (`g_lim=1.5`, `a_lim=3.0`, `o_lim=3.0°`), and reduced duration to `0.8s`. This increased simulated recall from 55.1% to **92.8%**.
*   **Next Step**: Deploy the optimized `SwingDetector` to physical watch and test.

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
