# Context: Pitch Analytix Pro

This document maps the project directory layout, key architectural classes, dependencies, and integration interfaces.

---

## 📂 Workspace Layout

```
├── .planning/                  # SDD documentation (Project, Requirements, State, Context)
├── app/                        # Android companion app module
│   └── src/main/java/.../
│       ├── data/               # Room Database schemas (InningsEvent, HeartRateEvent)
│       ├── services/           # DataSyncListenerService, HealthConnectManager
│       └── MainActivity.kt     # Jetpack Compose Dashboards
├── wear/                       # Wear OS smartwatch app module
│   └── src/main/java/.../
│       ├── ml/                 # SwingDetector (Kinematics & Decision Tree)
│       ├── services/           # TrackerService (IMU sensor logging)
│       └── MainActivity.kt     # Wear watch UI
├── automate_pipeline.py        # Python script for audio-sensor data collection & alignment
├── pull_logs.sh                # Shell script to manually extract watch CSV log folder
├── deploy_physical.sh          # Builds and installs Debug APKs onto connected USB/Wifi devices
└── testing_guide.md            # Comprehensive instructions for running simulation/live sessions
```

---

## 🔗 Key Code Linkages

### 1. Watch App (`:wear`)
*   **[TrackerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/services/TrackerService.kt)**: Registers Accel/Gyro/Gravity/Rotation Vector sensor listeners, maintains a foreground wake lock, writes raw 50Hz logs to CSV files, and sends rotation vector events to `SwingDetector`.
*   **[SwingDetector.kt](file:///Users/neilkloot/Code/CricketBattingTracker/wear/src/main/java/com/mrpeel/cricketbattingtracker/ml/SwingDetector.kt)**: Implements Stance Orientation Locking, rotates raw vector data to stance-relative coordinate systems, calculates wrist roll and swing plane angles, and runs the stroke-type decision tree classifier.

### 2. Phone App (`:app`)
*   **[DataSyncListenerService.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/DataSyncListenerService.kt)**: Listens for incoming timeline strings via Google Play Services Wearable APIs, parses incoming shots/heart rate/system events, writes them to the Room DB, and starts the Health Connect syncing logic.
*   **[HealthConnectManager.kt](file:///Users/neilkloot/Code/CricketBattingTracker/app/src/main/java/com/mrpeel/cricketbattingtracker/services/HealthConnectManager.kt)**: Maps parsed batting session parameters and heart rates to a standard Google/Samsung Health exercise schema and writes them to the on-device Health Connect client.

### 3. Data Processing Script
*   **[automate_pipeline.py](file:///Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py)**: Pulls CSV logs and phone recordings, runs cross-correlation/peak-finding to calculate clock offsets, sends audio files to Gemini (`gemini-2.5-flash`) for Pydantic-structured transcription, aligns spoken narrations to gyroscope impact peaks, and outputs windowed CSV segments for machine learning training.

---

## 📦 Core Dependencies
*   **Android App/Wear OS**:
    *   *Kotlin Standard Library / Coroutines*
    *   *Androidx Health Services* (Exercise Client)
    *   *Androidx Health Connect* (SDK Integration)
    *   *Androidx Room* (SQLite database persistence)
    *   *Play Services Wearable* (Data Layer Communication)
    *   *Jetpack Compose / Wear Compose* (User Interface)
*   **Python Pipeline**:
    *   *google-genai* (Official Gemini API client)
    *   *numpy*, *pandas*, *scipy* (Signal analysis and peak-finding)
    *   *pydantic* (JSON schema validation)
