# Loading and Analysing Batting Session Data

This document outlines the complete session lifecycle and machine learning pipeline for the **Pitch Analytix Pro (Cricket Batting Tracker)**. It explains how raw smartwatch sensor streams and Polar Sense bottom-hand telemetry are collected, aligned, compiled, and used to update the phone-side batch detection engine, Random Forest classifiers, and evaluation scripts.

---

## 📋 Pipeline Architecture Overview

The batting tracker ecosystem relies on matching real-time smartwatch kinematics with Polar Verity Sense telemetry and narrated ground truth records:

```
[Wear OS Watch]             [Polar Sense IMU]
Raw 50Hz/100Hz Binary        418Hz BLE Stream
Watch*.bin.gz                bottom-hand data
     │                              │
     └─────────────┬────────────────┘
                   ▼ (Sync via GMS ZIP)
         [Phone companion app]
        PhoneSwingDetector.kt
          1. Paired Gyro Peak Alignment (Regression)
          2. Peak Prominence Detection (Initial Pass)
          3. 20-Feature Extraction
          4. GeneratedForest.predict() -> Shot Type
          5. GeneratedQualityForest.predict() -> Quality
          6. Room DB -> Compose History UI
                   │
                   ▼ (Mac Pipeline / ADB)
        compile_dataset.py
          combined_features.csv + combined_ground_truth_aligned.csv
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
generate_kotlin_forest.py   score_phone_pipeline.py
  - GeneratedForest.kt        - phone_pipeline_scorecard.md
  - GeneratedQualityForest.kt
  - ShotEnhancementConfig.kt
```

---

## 1. Collecting & Loading Individual Session Data

To collect high-fidelity kinematics data, you must record watch sensor binary files and phone audio narrations:

### Step 1: Record a Live Session
1. **Watch Logging**: Raw sensors are recorded to internal storage at 50Hz or 100Hz in compressed little-endian binary format:
   - `WatchAccelerometer.bin.gz`
   - `WatchGyroscope.bin.gz`
   - `WatchGravity.bin.gz`
   - `WatchGameOrientation.bin.gz` (Magnetometer-free quaternion - *primary bat orientation*)
   - `WatchOrientation.bin.gz`
   - `WatchMagnetometer.bin.gz`
   - `WatchSteps.bin.gz` (Pedometer step times)
2. **Polar Telemetry**: The Polar Verity Sense streams bottom-hand IMU telemetry at 418Hz to the phone companion app via BLE.
3. **Narration Audio**: Record audio narration on the phone companion app. Immediately after playing a shot, verbally describe it (e.g., *"Shot 5. Cover drive, good"* or *"Shot 6. Traditional sweep, poor"*).

### Step 2: Extract and Align
When the session ends, the watch app compresses all sensor files into a ZIP archive and streams it to the phone via GMS `ChannelClient`. The companion app unzips and batch-processes the data:
- **Time Alignment**: The companion app matches tap sequences on the watch and Polar sensor, running linear regression to compute millisecond-level time alignment (offset and drift correction).
- **Peak Prominence Detection**: Runs SciPy-style prominence peak detection on gyro magnitude to identify exact bat-ball impact candidate timestamps.
- **20-Feature Extraction**: Extracts a 20-feature window around each impact candidate (14 watch features + 6 Polar bottom-hand features).
- **Model Classification**: The phone calls `GeneratedForest.predict()` and `GeneratedQualityForest.predict()`, utilizing the 20-feature vector to classify both the shot type and quality inline on the device.

---

## 2. Immediate Session Analysis (Pipelines & ADB)

For offline development, evaluation, and model retraining, the raw files are pulled from the phone via ADB:

1. **Gemini Narration Transcription**:
   `automate_pipeline.py` uploads the narration audio `.m4a` file to the Gemini API (`gemini-3.5-flash`), loading vocabulary templates from `gemini_narration_prompt.md`. Gemini returns a structured JSON timeline of time-coded shot types and ratings.
2. **DP Sequence Alignment**:
   It matches transcribed audio events to watch-detected kinematic events using dynamic programming sequence alignment, updating the ground truth mapping.
3. **Outputs Generated**:
   - `ground_truth_aligned.csv`: Unified chronological mapping of narrated shots to raw sensor timestamps.
   - `segments/`: 6-second sliced CSV files (3s before, 3s after impact) for every shot.

### 🔄 Gemini Transcription Failures & Resuming

If Gemini transcription fails or if you need to rerun the alignment step without calling the Gemini API again, the pipeline supports cached runs:

- **Cached Resuming**: If `narrations_raw.json` already exists in the session directory, run `automate_pipeline.py` without `--force-retranscribe` to skip the Gemini API call entirely.
- **Force Retranscribe**: Run with `--force-retranscribe` and `--model gemini-3.5-flash` to force a clean API call.

---

## 3. Combined Multi-Session Dataset Compilation

To train the companion app's classifiers, individual sessions are compiled into a unified dataset:

```bash
python3 pipelines/compile_dataset.py
```

- **How it works**:
  The script scans trusted session directories, loads the binary `.bin.gz` files (or fallback `.csv.gz`), rotates coordinates relative to the confirmed rest stance quaternion (`qStance`), extracts the 20 features, and maps them against ground truth labels.
- **Outputs Generated**:
  - `combined_features.csv`: A dataset of all trustworthy swing shots (imputing Polar features to `0.0` when absent).
  - `combined_ground_truth_aligned.csv`: A compiled list of all physical swings and their timestamps.

---

## 4. Model Retraining and Transpilation Pipeline

To quickly retrain the companion app's models and sync the latest configuration:

```bash
python3 pipelines/model_update_pipeline.py
```

### Steps Executed Automatically:

1. **Retrain Models**: Trains both a 200-tree Shot Type Random Forest model and a 100-tree Shot Quality Random Forest model.
2. **Transpile Classifiers**: Transpiles the trees into flat-array hex-packed Kotlin code files:
   - `GeneratedForest.kt` (Shot Type classifier)
   - `GeneratedQualityForest.kt` (Shot Quality classifier)
   - `SwingFeatures.kt` (Data class defining the 20-feature signature, with Polar fields defaulting to `0f` for watch-only backward compatibility)
3. **Sync Detection Thresholds**: Reads `optimized_detection_config.json` (produced during alignment evaluation) and writes `ShotEnhancementConfig.kt`, updating the companion app's watch gyro detection threshold to match optimal parameters.
4. **Deploy Check**: Automatically copies the Kotlin classes to both `wear` and `app` modules and runs local JUnit model integrity tests.

---

## 5. Authoritative Performance Scorecard

The performance scorecard is evaluated offline using the actual phone pipeline output:

```bash
python3 pipelines/score_phone_pipeline.py
```

- Reads `combined_features.csv` + `combined_ground_truth_aligned.csv`.
- Scores the retrained 20-feature RF models.
- Generates `phone_pipeline_scorecard.md` broken down by session, shot class, and data profile (`50hz_watch`, `50hz_watch_polar`, `100hz_watch_polar`).

> [!WARNING]
> Accuracy figures in `phone_pipeline_scorecard.md` are **training-set fit** (diagnostic).
> Held-out session accuracy is the only true measure of model generalisation.
