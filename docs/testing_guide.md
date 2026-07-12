# Local Testing Guide for Cricket Batting Tracker (Professional Edition)

This guide explains how to perform a **full, visible end-to-end (E2E) simulation** of the cricket batting tracker using Phone and Wear OS emulators.

## Prerequisites

- **macOS** with **Android Studio** installed.
- **AVDs Configured**: `PhoneAVD` (API 33+) and `WearAVD` (Wear OS 3+).
- **Java 17**: Ensure `JAVA_HOME` points to a JDK 17.
- **ADB**: Platform-tools added to your PATH.

---

## 🚀 The Visible E2E Simulation (Recommended)

This is the most comprehensive way to verify the system. You will see the watch UI update in real-time as shots are "played" and then see the data sync to the phone.

### 1. Start the Emulators
Launch both required emulators and wait for them to fully boot:
```bash
test/start_emulators.sh
```

### 2. Run the E2E Script
This script builds both apps, deploys them, launches the UIs, and triggers the shot simulation:
```bash
test/run_visible_e2e.sh
```

### 3. What to Observe
1.  **Watch UI**: As the script runs, watch the **Wear OS emulator**. You will see the "Glanceable Ring" update for every shot detected (Cover Drive, Pull, Sweep).
2.  **Real-time Metrics**: Note the Bat Speed and Sweet Spot ratings appearing instantly.
3.  **Data Sync**: After the simulation, the watch session will end, and the **Phone emulator** will automatically refresh to show the new session timeline.
4.  **Phone Verification**: Verify the **Innings ID**, **Shot Types**, and **Biomechanics** (Angles) on the phone dashboard.

---

## 🛠️ Individual Tooling

### Building the Apps
```bash
./gradlew assembleDebug
```

### Manual Shot Injection
If you want to test specific shots manually while watching the UI:
```bash
# Ensure the Wear app is running and 'Tracking' is active
EMULATOR_PORT=5556 test/simulate_shots.sh
```

### Monitoring Logs
For deep technical verification of the kinematics engine:
```bash
adb -s emulator-5556 logcat | grep "SwingDetector"
```

## 📊 Automated Data Collection & Narration Alignment

This pipeline automates the extraction and alignment of watch sensor data with phone voice recordings using a 5-tap calibration signature and the Gemini API.

### Prerequisites
1. Set your Gemini API key in your terminal:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
2. Ensure both the watch and phone are connected to your Mac via ADB (USB or wireless debugging).

### How to Collect Data & Narration
1. **Start the session**: Start the workout tracking on your Galaxy Watch.
2. **Start recording audio**: On your phone (using earbuds), start recording audio.
3. **Perform calibration**: Immediately after starting both, **tap your bat handle 5 times in quick succession** (all 5 taps must occur within 2 seconds). This creates a distinct timestamp signature in both the watch gyroscope and phone audio recording.
4. **Bat and Narrate**: Play your shots and verbally narrate each shot immediately after hitting it (e.g., say: *"Cover drive, middle of the bat"* or *"Pull shot, hit well"*).
5. **End session**: Stop both the watch tracking and the audio recording.

### Run the Pipeline
Run the script from your Mac:
```bash
./automate_pipeline.py --watch-ip 192.168.1.27:37129
```
*   **What it does**:
    1. Connects to the watch via ADB, pulls the latest raw sensor session folders, and clears the watch directory.
    2. Scans the connected phone via ADB, auto-detects the latest `.m4a`/`.mp3` voice recording, and pulls it.
    3. Converts the audio to AIFF using native macOS `afconvert` and detects the 5-tap audio and gyroscope peaks to calculate the exact clock offset.
    4. Uploads the audio to Gemini for high-accuracy time-coded transcriptions of your narrations.
    5. Saves `ground_truth_aligned.csv` matching narrations to raw sensor timestamps.
    6. Extracts 6-second windowed CSV segments (3s before, 3s after impact) for all sensor metrics under the `segments/` folder for model training.
    7. Prints a **Session Accuracy Report** comparing the watch's real-time classifications to your narrated ground truth.

