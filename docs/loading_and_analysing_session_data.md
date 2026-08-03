# Loading and Analysing Batting Session Data

This document details the complete session data lifecycle, machine learning pipeline, dataset compilation protocol, and model retraining workflow for the **Pitch Analytix Pro (Cricket Batting Tracker)**. It reflects the production multi-sensor pipeline, Deepgram Nova-3 audio transcription engine, 423 Hz unified Parquet dataset architecture, PyTorch Advanced TCN model training, ONNX model transpilation, and phone database synchronization.

---

## 📋 System Architecture Overview

Pitch Analytix Pro combines high-frequency smartwatch kinematics (top hand), Polar Verity Sense IMU telemetry (bottom hand), Deepgram Nova-3 audio narration, and hardware-accelerated TCN neural network inference:

```
┌──────────────────────────┐          ┌──────────────────────────┐
│   Wear OS Smartwatch     │          │  Polar Verity Sense IMU  │
│  Top-Hand Motion Stream  │          │ Bottom-Hand Motion Stream│
│   423 Hz (6-Axis IMU)    │          │     418 Hz BLE Stream    │
└────────────┬─────────────┘          └────────────┬─────────────┘
             │                                     │
             └──────────────────┬──────────────────┘
                                ▼ (Automatic GMS Wearable Sync)
                   ┌──────────────────────────┐
                   │  Phone Companion App     │
                   │ Deepgram Audio Recorder  │
                   └────────────┬─────────────┘
                                │
                                ▼ (Mac Python Pipeline)
                  automate_pipeline.py (Nova-3 Transcribe)
                                │
                                ▼
                 build_unified_dataset.py (423 Hz Grid)
               🛡️ Ground Truth Truncation Guardrail (t <= max_narr + 10s)
                                │
                                ▼
           poc_unified_dataset/*.parquet (45 Kinematic Channels)
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
train_and_evaluate_full_scorecard.py             reprocess_sessions.py
  - PyTorch Advanced TCN (10 Dilated Blocks)       - Stage 1 Decoupled Anchor Detection
  - Canonical 8 Biomechanical Classes             - Full Session Un-narrated Shot Recovery
  - ONNX Model Export (tcn_ultimate_baseline.onnx) - Phone SQLite DB Sync & App UI Refresh
        │
        ▼
app/src/main/assets/models/tcn_ultimate_baseline.onnx
  - Kotlin TcnModelRunner.kt ONNX Runtime Inference
```

---

## 1. Session Data Collection & Wireless Extraction

### Step 1: Record a Session on Field/Nets
1. **Wear OS Smartwatch Logging**:
   - Sensor streams are logged to raw compressed files in internal storage:
     - `WatchAccelerometer.bin.gz`
     - `WatchGyroscope.bin.gz`
     - `WatchGravity.bin.gz`
     - `WatchGameOrientation.bin.gz` (Magnetometer-free quaternion — primary bat orientation)
     - `WatchOrientation.bin.gz`
     - `WatchMagnetometer.bin.gz`
     - `WatchSteps.bin.gz`
2. **Polar Verity Sense Telemetry**:
   - Streams bottom-hand IMU telemetry over BLE to the phone companion app at 418 Hz: `PolarAccelerometer.bin`, `PolarGyroscope.bin`, and `PolarMagnetometer.bin`.
3. **Deepgram Audio Narration**:
   - The phone companion app records narration audio (`narration_YYYYMMDD_HHMMSS.m4a`). The batter or coach describes shots after execution (e.g., *"Shot 10. Power drive, good"* or *"Shot 11. Leg glance, poor"*).

### Step 2: Automatic GMS Watch Sync & Phone Data Extraction

1. **Primary Operational Workflow (Automatic GMS Watch Sync)**:
   - When a session is ended on the watch, the Wear OS app compresses all sensor files into a ZIP archive (`session_YYYY-MM-DD_HH-MM-SS.zip`) and streams it directly to the phone companion app over **Google Play Services (GMS) `ChannelClient` / Data Layer API**.
   - The phone companion app receives the ZIP, unzips it into `/sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/live_watch_sessions/`, aligns Polar BLE telemetry and Deepgram audio narrations, and batch-inserts the session into SQLite.

2. **Mac Pipeline Extraction (Phone to Mac via ADB)**:
   - For offline evaluation, dataset building, and model retraining, the Mac Python pipeline pulls session folders from the **Phone**:
     ```bash
     # Pull session data from Android Phone via ADB
     adb -s <phone_serial> pull /sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/live_watch_sessions/ /Users/neilkloot/Code/Batting\ Sensor\ Stats/live_watch_sessions/
     ```

3. **Emergency Watch Recovery Fallback (Wireless ADB Direct to Watch)**:
   - *Only if an app crash or BLE disconnect prevents automatic GMS channel completion*, raw session logs can be pulled directly from the watch over Wireless ADB:
     ```bash
     # Emergency Fallback: Connect to Wear OS Watch directly over Wireless ADB
     adb connect 192.168.1.53:42147
     adb -s 192.168.1.53:42147 pull /sdcard/Android/data/com.mrpeel.cricketbattingtracker.wear/files/ ...
     ```

Sessions automatically sync to `/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session_YYYY-MM-DD_HH-MM-SS`.

---

## 2. Audio Transcription & Time Synchronization

Raw session processing is orchestrated via `automate_pipeline.py`:

```bash
python3 automate_pipeline.py --session-dir "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session_2026-08-01_10-18-20"
```

### Deepgram Nova-3 Audio Transcription
* `automate_pipeline.py` sends `narration_*.m4a` to **Deepgram Nova-3** (`deepgram-sdk` API).
* Nova-3 extracts word-level and sentence-level timestamped transcripts with exact millisecond precision.
* The pipeline parses spoken shot indices, shot classification phrases, and quality ratings into `narrations_raw.json`.

### Sensor-Clock Alignment & Linear Drift Optimization
* The pipeline aligns audio timestamps to sensor clocks using **2D Joint Offset and Linear Drift Rate Optimization**:
  - Computes global clock offset $\Delta t_{\text{clock}}$ and linear drift rate $\alpha_{\text{drift}}$ across physical impact peaks.
  - Matches 100% of narrated physical shots with high-confidence $R^2 > 0.9999$ correlation.
  - Output file: `ground_truth_aligned.csv`.

---

## 3. 423 Hz Unified Parquet Dataset Generation

Model training requires structured, synchronized kinematic arrays. We build `.parquet` datasets via `pipelines/build_unified_dataset.py`:

```bash
python3 pipelines/build_unified_dataset.py
```

### 45 Kinematic Input Channels
Each session is projected onto a uniform **423 Hz temporal grid** ($dt = 2.364\text{ ms}$):
* **Smartwatch Sensors (Top Hand)**: 3D Accel (`w_acc`), 3D Gyro (`w_gyro`), 3D World-Frame Accel (`w_acc_world`), 3D World-Frame Gyro (`w_gyro_world`), 3D Gravity (`w_grav`), 3D Linear Accel (`w_lin`), 3D Mag (`w_mag`), 4D Orientation Quaternion (`w_rot`).
* **Polar Sensors (Bottom Hand)**: 3D Accel (`p_acc`), 3D Gyro (`p_gyro`), 3D Mag (`p_mag`).
* **Derived Metrics**: Gyro magnitude (`w_gyro_mag`), Accel magnitude (`w_acc_mag`), Jerk (`w_jerk_mag`), Energy (`w_gyro_energy`), Pedometer step counts (`step_cum`).

### 🛡️ Strict Ground-Truth Truncation Guardrail
> [!IMPORTANT]
> To prevent model training contamination, `build_unified_dataset.py` enforces a **Strict Ground-Truth Truncation Guardrail**:
> ```python
> # Truncate parquet training dataset at max narration timestamp + 10 seconds
> if narr:
>     valid_narr_times = [float(e['timestamp_seconds']) * 1000.0 for e in narr if 'timestamp_seconds' in e]
>     if valid_narr_times:
>         max_narr_ms = max(valid_narr_times) + 10000.0
>         df = df[df['t_ms'] <= max_narr_ms].copy()
> ```
> If audio narration stops mid-session (e.g., due to a Bluetooth disconnect), un-narrated tail data is **strictly truncated** from the `.parquet` file. This guarantees that un-narrated physical shots are **NEVER** fed to PyTorch loss functions as false `no_shot` labels!

---

## 4. Retraining the TCN Neural Network Model

Model training and evaluation are handled by `pipelines/train_and_evaluate_full_scorecard.py`:

```bash
python3 pipelines/train_and_evaluate_full_scorecard.py
```

### 🎯 The Canonical 8 Biomechanical Classes
All models are strictly aligned to the **8 Canonical Biomechanical Classes** defined in `docs/batting_dual_hand_biomechanics.md` and the app UI:

| ONNX Class Index | Canonical Biomechanical Class | Description |
| :---: | :--- | :--- |
| `0` | `no_shot` | Quiet stance, walking, or resting between deliveries |
| `1` | `pre_shot` | Backlift and downswing setup phase |
| `2` | `PULL/HOOK` | Horizontal cross-bat shot to leg side |
| `3` | `DRIVE/DEFENCE` | Vertical bat straight/forward drive or defensive block |
| `4` | `GLANCE/FLICK` | Wrist flick or deflection to fine leg |
| `5` | `CUT/PUNCH` | Square/off-side horizontal cut or back-foot punch |
| `6` | `DEFLECTION/GUIDE` | Soft-hands nudge, late cut, or third-man guide |
| `7` | `POWER DRIVE` | High-velocity aerial or ground power drive |
| `8` | `SLOG` | High-intensity un-anchored cross-bat slog |
| `9` | `SWEEP` | Low-stance sweep or reverse sweep |

### 🧠 PyTorch Advanced TCN Architecture & Training Optimization
The model is an **Advanced Temporal Convolutional Network (TCN)**:
* **Input Layer**: 45 features $\times$ sequence frames ($423\text{ Hz}$).
* **Residual Backbone**: 10 Dilated Causal Conv1D Residual Blocks with exponentially growing receptive fields ($d = 1, 2, 4, 8, 16, 32, 64, 128, 256, 512$).
* **Temporal Anchor Jitter Augmentation**: Applies random frame offsets ($\pm 30\text{ms} = \pm 13\text{ frames}$) during training window slicing to make the TCN invariant to minor alignment drift.
* **Dynamic Inverse-Frequency Focal Loss**: Combines Focal Loss ($\gamma = 2.0$) with automated inverse-frequency class weighting:
  $$\text{Weight}[c] = \frac{\text{Total Samples}}{\text{Num Classes} \times \text{Count}[c]}$$
  This automatically self-scales loss multipliers for minority classes (e.g. `POWER DRIVE` at 5.2x boost) and smoothly decays toward 1.0x as dataset volume scales, eliminating manual hardcoded scalars.

### 🔒 Production ONNX Quality Gate & Model Export
Upon training completion, the script runs an automated **Production Quality Gate Check**:
* **Verification Gate**: The ONNX model asset is exported to `app/src/main/assets/models/tcn_ultimate_baseline.onnx` **ONLY IF**:
  $$\text{Overall Precision} \ge 75\% \quad \text{AND} \quad \text{Holdout F1 Score} \ge 50\%$$
* **Asset Protection**: If experimental parameters degrade precision or introduce false alarm spikes, the production asset is automatically protected and retained.
* **Scorecard Evaluation**: Evaluates held-out session performance (`HOLDOUT_SESSIONS`) and writes the full-dataset report to `full_dataset_training_scorecard.md`.

---

## 5. Phone Reprocessing & Database Synchronization

To reprocess historical sessions, update shot classifications, and sync SQLite databases back to the phone:

```bash
python3 pipelines/reprocess_sessions.py
```

### 🔄 What `reprocess_sessions.py` Does:
1. **Pull Database**: Pulls `cricket_tracker_database.db` from the connected Android phone via ADB.
2. **Scan Sessions**: Scans all local session directories in `live_watch_sessions/`.
3. **Full Session Un-narrated Shot Recovery**:
   - For narrated shots, uses ground-truth labels.
   - For un-narrated sensor tails (e.g., when audio disconnects), runs **Stage 1 Decoupled Impact Anchor Detection** ($a_{\text{impact}} \ge 30.0\text{ m/s}^2, \omega_{\text{impact}} \ge 4.0\text{ rad/s}$) + ONNX TCN inference to detect and classify **100% of un-narrated physical shots**.
4. **Dual-Model Feature Routing**:
   - Sessions with Polar telemetry use **Dual-Hand 26-Feature Routing**.
   - Sessions without Polar telemetry use **Top-Hand Watch 14-Feature Routing**.
5. **Database Push & App Restart**:
   - Cleans legacy duplicate events in SQLite.
   - Inserts updated shot records, bat speeds, impact forces, and qualitative coaching cards.
   - Pushes the database back to `/data/data/com.mrpeel.cricketbattingtracker/databases/` and restarts the Android app automatically.

---

## 6. Android Native Runtime & Safety Infrastructure

### 🛡️ 16 KB ELF Page Alignment (Android 15+)
Android 15 requires all native shared libraries (`.so`) inside packaged APKs to be aligned on **16 KB (16384 bytes) page boundaries**:
* **ONNX Runtime Upgrade**: Upgraded `com.microsoft.onnxruntime:onnxruntime-android` to `1.22.0` in `app/build.gradle.kts`.
* **CMake Linker Flags**: Added `arguments("-DANDROID_STL=c++_static")` and `-Wl,-z,max-page-size=16384` in `CMakeLists.txt`.
* **AGP Packaging**: Set `packaging.jniLibs.useLegacyPackaging = false` so AGP stores uncompressed `.so` binaries aligned on 16 KB boundaries inside output APKs.
* **Gradle Post-Processing**: Added automated `zipAlign16kb` Gradle task in `app/build.gradle.kts` to zipalign output APKs to `16384` bytes.

### ⚡ RxJava 3 UndeliverableException Handling
To prevent BLE disconnects from crashing the Android JVM when Polar Sense streams drop:
* **Global Error Handler**: `RxJavaPlugins.setErrorHandler { ... }` is registered in `PolarSenseManager.kt` and `MainActivity.kt`.
* **Non-Blocking Reconnect**: Disposes stale RxJava subscriptions and executes a 2.0-second non-blocking reconnection loop in `handleStreamError()`.

---

## ⚡ Quick Reference Command Summary

| Task | Command |
| :--- | :--- |
| **Process New Live Session (Deepgram Nova-3)** | `python3 automate_pipeline.py --session-dir "/path/to/session"` |
| **Build 423 Hz Unified Parquet Datasets** | `python3 pipelines/build_unified_dataset.py` |
| **Retrain TCN Model & Export ONNX** | `python3 pipelines/train_and_evaluate_full_scorecard.py` |
| **Reprocess & Push SQLite Database to Phone** | `python3 pipelines/reprocess_sessions.py` |
| **Verify ELF 16 KB Page Alignment** | `python3 pipelines/verify_elf_alignment.py` |
| **Run Android Gradle Unit Tests** | `./gradlew test` |
