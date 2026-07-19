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

## 3. Retraining and Transpilation Pipeline (Recommended Flow)

The easiest way to update, transpile, and verify the model is to run the end-to-end orchestration pipeline. **This script runs all steps automatically** (including dataset compilation, threshold optimization, model retraining, code transpilation, and scoring). You do not need to run the underlying scripts manually.

To retrain the classifiers on the compiled dataset:

```bash
python3 pipelines/model_update_pipeline.py
```

### Steps Executed Automatically by the Pipeline:
1. **`evaluate_shot_alignment.py`**: Improves impact timestamps and generates optimal gyro detection thresholds.
2. **`compile_dataset.py`**: Compiles raw watch `.bin.gz` logs and Polar telemetry into unified CSV files.
3. **`optimize_shot_enhancement.py`**: Calculates optimized reclassification thresholds.
4. **`score_phone_pipeline.py` (Before)**: Captures baseline performance metrics using current logic.
5. **`generate_kotlin_forest.py`**: Trains both the Shot Type Random Forest model and Shot Quality Random Forest model, transpiles them to Kotlin (`GeneratedForest.kt`, `GeneratedQualityForest.kt`, `SwingFeatures.kt`), and writes the optimized watch gyro threshold to `ShotEnhancementConfig.kt` in the `app` module.
6. **`train_quality_classifier.py`**: Trains the Python quality model for historical re-scoring.
7. **Gradle Tests & Integrity Verification**: Automatically executes the local JUnit test suite (`SwingDetectorGroundTruthTest`) to verify compilation and determinism.
8. **`score_phone_pipeline.py` (After)**: Generates the updated side-by-side performance delta report (`model_update_analysis.md`).

---

## 4. Isolated / Manual Script Execution (Optional)

In specific scenarios, such as isolated troubleshooting or feature analysis, you can run components of the pipeline manually.

### Scenario A: Recompile the Dataset Manually
If you want to regenerate `combined_features.csv` and `combined_ground_truth_aligned.csv` to inspect features without retraining any models:
```bash
python3 pipelines/compile_dataset.py
```
- **How it works**: Scans trusted session directories, loads binary `.bin.gz` logs, rotates coordinates relative to the confirmed rest stance quaternion (`qStance`), extracts the 20 features, and maps them against ground truth labels.

### Scenario B: Score the Current Models Manually
If you want to generate a performance scorecard (`phone_pipeline_scorecard.md`) for the current model in the workspace without triggering retraining:
```bash
python3 pipelines/score_phone_pipeline.py
```
- **How it works**: Reads `combined_features.csv` + `combined_ground_truth_aligned.csv`, scores the active 20-feature models, and prints class and data profile breakdowns (Watch-only 50Hz, Watch 50Hz + Polar, Watch 100Hz + Polar).

### Scenario C: Reprocess and Sync Historical Phone Data
If you have retrained the models and want to retrospectively re-process all historical sessions (identifying missing shots, filtering phantom shots, and re-classifying shot types and quality on the phone):
```bash
python3 pipelines/reprocess_sessions.py
```
- **How it works**:
  1. Pulls the `cricket_tracker_database` SQLite database from the connected phone using ADB.
  2. Scans local raw directories (`live_watch_sessions/session-*`) on your Mac to identify both existing and missing sessions on the phone.
  3. For each session:
     - Deletes previous shot event records from SQLite (ensuring a clean reconstruction).
     - Parses the session name to derive the exact start timestamp (`inningsId`).
     - If the session does not exist in SQLite, it registers the session, initializing the location to `"26 Aldinga Street, Blackburn South"`.
     - Re-runs prominence peak detection (using the optimized watch gyro threshold or Polar accelerometer threshold) to re-identify impact candidates.
     - Extracts the 20 features for each shot and applies the retrained Shot Type and Shot Quality models.
     - Re-saves updated shots, mapping quality buckets (`good`, `poor`, `miss`, `edge`) to UI parameters and adding a `"✨ Updated"` badge to descriptions.
  4. Restores the modified SQLite database back to the app databases container on the phone and restarts the app.

> [!WARNING]
> Accuracy figures in `phone_pipeline_scorecard.md` are **training-set fit** (diagnostic).
> Held-out session accuracy is the only true measure of model generalisation.


