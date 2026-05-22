# Requirements: Pitch Analytix Pro

This document defines the functional and non-functional requirements for the Pitch Analytix Pro tracking ecosystem.

---

## 📋 Functional Requirements

### 1. Wear OS Sensor Tracking
*   **Continuous Sampling**: Listen to Accelerometer, Gyroscope, Gravity, and Rotation Vector sensors at `50Hz` (20ms intervals).
*   **Foreground Persistence**: Use an Android Foreground Service (`TrackerService`) holding a partial wake lock to guarantee logging when the watch screen goes dark.
*   **Null-Safety**: Fail-safe listener registration with fallback defaults and warning logs if the host watch lacks specific sensors (e.g., Rotation Vector).

### 2. Shot Classification (Kinematics & ML)
*   **Real-time Classification**: Classify shots locally on the watch.
*   **Heuristics & ML**: Extract stance-relative roll angle at impact, swing plane coordinates, and yaw. Feed these into a native Kotlin decision tree.
*   **Supported Shots**: Classify Cover Drive, Pull Shot, On Drive/Flick, Defence, Push, and Play-and-Miss.
*   **Speed Calculation**: Calculate bat speed using an adjustable bat radius (`0.68m` standard) and stroke-specific multipliers (Straight-bat: `1.45x`, Cross-bat: `1.30x`).

### 3. Data Synchronization & Storage
*   **Bluetooth Sync**: Push timeline events (shots, start/end timestamps) automatically from watch to phone via Wearable Data Layer APIs.
*   **Offline Persistence**: Store innings data locally on the companion phone using Room SQLite database.
*   **Mobile Analytics**: Display batting metrics (Total Distance run, Max Bat Speed, Shot count, Heart Rate profiles, sweet-spot accuracy) via compose views.

### 4. Health Integration
*   **Samsung Health Integration**: Write exercise sessions to Android Health Connect under the "Cricket" activity type. Include total shot count, maximum bat speed, and heart rate samples.

### 5. Data Collection & Narration Script (Option A)
*   **ADB Automation**: Automate pulling sensor files (`WatchAccelerometer.csv`, `WatchGyroscope.csv`, `WatchGravity.csv`, `WatchOrientation.csv`) and phone audio recording via ADB.
*   **5-Tap Clock Synchronization**: Synchronize the audio and watch timelines by searching for a 5-tap signature (5 peaks within 2.0s) in the gyroscope magnitude and audio envelope.
*   **Gemini Audio Transcription**: Call Gemini to get time-coded transcripts of the batsman's verbal shot narrations (e.g., `"Pull shot, hit well"`).
*   **Segment Export**: Slice raw sensor data into clean 6-second windowed CSV segments (3s before, 3s after impact) labeled with shot type and quality for model training.
*   **Session Accuracy Reporting**: Generate a comparative scorecard between watch-detected shots and narrated ground-truth.

---

## ⚡ Non-Functional Requirements

### 1. Real-Time Performance
*   **CPU Budget**: The 50Hz Wear OS processing loop must use less than 10% CPU to prevent UI stutter and lag.
*   **Memory Overhead**: Math routines (`averageQuats`, `multiplyQuats`, etc.) must be allocation-free to prevent garbage collection spikes.

### 2. Synchronization Accuracy
*   **Clock Alignment**: The 5-tap calibration offset must align phone audio and watch sensor timelines with a latency tolerance under `100ms`.

### 3. CSV File Formats
*   All sensor CSV files must follow standard headers:
    *   Accel/Gyro/Gravity: `time,seconds_elapsed,x,y,z`
    *   Orientation: `time,seconds_elapsed,qx,qy,qz,qw`

---

## 🗓️ Current Feature Backlog

### 1. Classification & Accuracy Improvements
*   **Pull Shot Precision**: Improve Pull shot classification precision (current false positive rate is high, with 12 FPs in the baseline evaluation).
*   **Cover Drive Recall**: Improve Cover Drive classification recall (current recall is 0.57, with 6 false negatives).
*   **Low-Speed Calibration**: Resolve speed calculation errors and corrupt low-speed labels on slow/gentle strokes (e.g., Cover Drives/Flicks where true speed is under 20 km/h but detected speed is over 50 km/h).

### 2. Sensor Telemetry & Data Collection
*   **Active Watch Sensor Logging**: Capture and collect active watch sensor data for sessions that previously lacked telemetry and used stationary phone fallback (specifically "Short off side" and "Full length" sessions).

### 3. Pipeline & Usability Transitions
*   **Option B (Mobile Integration)**: Migrate the audio narration recording, transcription, and time-alignment out of the Python pipeline and integrate it directly into the Android Companion App UI.
