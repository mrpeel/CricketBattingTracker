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
./start_emulators.sh
```

### 2. Run the E2E Script
This script builds both apps, deploys them, launches the UIs, and triggers the shot simulation:
```bash
./run_visible_e2e.sh
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
EMULATOR_PORT=5556 ./simulate_shots.sh
```

### Monitoring Logs
For deep technical verification of the kinematics engine:
```bash
adb -s emulator-5556 logcat | grep "SwingDetector"
```

## 🧪 Unit Testing
Validate the core logic against the biomechanics ground truth:
```bash
./gradlew :wear:testDebugUnitTest
```
