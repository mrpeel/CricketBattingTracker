# Active Context: Pitch Analytix Pro

This file defines the system objectives, feature backlog catalog, active technical approach, and verification methods.

---

## 🎯 System Objectives
*   **Active Phase**: Data Collection & Synchronization Pipeline — Transcription Reliability Improvement
*   **High-Level Vision**: Pitch Analytix Pro is a professional-grade cricket training companion utilizing Wear OS IMU sensors, local kinematics heuristics, mobile dashboards, and cloud transcription pipelines.
*   **"The Digital Pavilion" UI Spec**:
    *   **Background**: `#000000` (True Black for OLED screen battery conservation) / `#001B3D` (Deep Navy accents).
    *   **Primary Color**: `#58FF63` (Neon Green - High visibility, active tracking status).
    *   **Secondary Color**: `#BCD2FE` (Light Blue - Secondary metrics and averages).
    *   **Typography**: `Space Grotesk` (Modern, geometric, glanceable).
    *   **Roundness**: `Round Four` (Circular watch-optimized shapes).

---

## 🛠️ Technical Approach
*   **Wear OS Smartwatch**: Runs a foreground tracking service (`TrackerService`) with a partial wake lock to guarantee continuous 50Hz sensor logging. Rotates raw sensor vectors using quaternions and computes real-time metrics locally using `SwingDetector`.
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
| B-001 | Pull Shot Precision | Reduce false positive rate on Pull shot classification | Backlog | `SwingDetectorGroundTruthTest` |
| B-002 | Cover Drive Recall | Improve recall of Cover Drive shots | Backlog | `SwingDetectorGroundTruthTest` |
| B-003 | Speed Calibration | Fix speed anomalies on low-speed Cover Drives/Flicks | Backlog | `SwingDetectorGroundTruthTest` |
| B-004 | Active Watch Data | Implement active sensor logging for short-off-side/full-length | Backlog | Session collection check |
| B-005 | Companion Recording | Migrate audio recorder & transcription to App UI | Completed | E2E verification |
| B-006 | Watch Teardown Crash | Fix lateinit healthServicesManager crash on onDestroy | Completed | E2E verification |
| **B-007** | **Transcription Reliability** | **Replace brittle Gemini long-audio transcription with Whisper-based local timestamped transcription + Gemini for shot classification only** | **Active Backlog** | **Pipeline re-run producing correct shot count for 18-min session** |

---

## 🔖 Current Session State (session-2026-05-26_12-28-05)
*   **Session Directory**: `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-05-26_12-28-05`
*   **Audio File**: `narration_20260526_122802.m4a` (18 minutes, 1109 seconds)
*   **Narrations Cache**: `narrations_raw.json` — contains **72 shot narrations** (Shot 1–72) with timestamps. User reported 69 shots were actually played; discrepancy TBD.
*   **Ground Truth CSV**: `ground_truth_aligned.csv` — 72 shots aligned to sensor peaks.
*   **Last Pipeline Run Result**: 72 GT shots, 113 watch-detected, 9 correct classifications (12.5%), 93% Hit/Miss Agreement.
*   **API Quota Status**: `gemini-2.5-flash` free-tier **20 req/day limit is exhausted** for today. Cannot re-run transcription until tomorrow or with a paid API key.

---

## 🧪 Verification & Testing

### 1. Automated Verification
*   **Kinematics Unit Tests**: Run `SwingDetectorTest` to verify math helpers, ring buffer logic, and state transitions.
*   **Ground Truth Scorecard**: Run [SwingDetectorGroundTruthTest.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/test/java/com/mrpeel/cricketbattingtracker/ml/SwingDetectorGroundTruthTest.kt) to generate the performance scorecard against physical batting session datasets.

### 2. Manual E2E Simulation
*   **Launch Emulators**: Run `./start_emulators.sh` to boot Phone and Wear AVD targets.
*   **Visible E2E Script**: Execute `./run_visible_e2e.sh` to compile, deploy both apps, simulate shots, and verify synchronization.
