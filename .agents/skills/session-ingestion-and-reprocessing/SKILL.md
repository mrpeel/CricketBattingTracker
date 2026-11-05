---
name: session-ingestion-and-reprocessing
description: >-
  Use this skill when pulling new physical batting sessions from the phone/watch,
  transcribing and aligning ground-truth audio narrations, computing 3D bat/wrist
  AHRS orientations, building 423 Hz unified Parquet files, or reprocessing and
  pushing the Room v12 SQLite database to the Android phone.
---

# Session Ingestion, Alignment & Room v12 Reprocessing Runbook

Follow this workflow whenever the user records new physical batting sessions or asks to reprocess historical sessions into the dataset and phone database.

## 1. Pre-Flight Invariants
Before modifying or running any ingestion or reprocessing script, enforce these invariants (detailed in [.agents/LEARNINGS.md](../../LEARNINGS.md)):
1. **No Whisper AI**: Never use local Whisper models for audio transcription. Use Gemini audio transcription or Deepgram Nova-3 as configured in `automate_pipeline.py`.
2. **Authoritative Start-Time Hierarchy**: Session start time (`session_start_ms`) must always resolve in strict order:
   1. `session_config.json` $\rightarrow$ `start_time_ms`
   2. `latest_timeline.txt` $\rightarrow$ `SYSTEM_START: Ts=`
   3. Directory name regex (`session_YYYY-MM-DD_HH-mm-ss`)
   4. Directory `mtime`
3. **Room v12 Schema & Hash Parity**: `pipelines/reprocess_sessions.py` must maintain exact 57-column DDL parity and Room v12 identity hash `36946e68af413e8cc2fca0555e69b534` with `InningsEvent.kt` and `AppDatabase.kt`.

## 2. Step-by-Step Pipeline Execution

### Step 1: Pull Sessions & Align Narration (`automate_pipeline.py`)
Pulls raw watch ZIPs and Polar Verity Sense directories from the connected phone via ADB, transcribes audio narration, aligns speech timestamps to IMU impact peaks using 2D clock drift optimization, and writes `ground_truth_aligned.csv`:
```bash
python3 automate_pipeline.py
```
*Note*: Make sure `session_config.json` is present at the session root (or copied from `PolarSense/session_config.json`) so `polar_mount_mode` (`WRIST` vs `BAT_HANDLE`), `bat_id`, and mid-session `bat_switches` are preserved.

### Step 2: Compile 423 Hz Unified Parquet Dataset (`build_unified_dataset.py`)
Resamples watch + Polar streams onto the 423 Hz unified grid (`poc_unified_dataset/`), clamping `p_acc_*` / `p_gyro_*` to `0.0f` during `BAT_HANDLE` sessions while routing raw bat handle kinematics to `b_acc_*` / `b_gyro_*`:
```bash
python3 pipelines/build_unified_dataset.py
```

### Step 3: Reconstruct 3D Bat/Wrist Orientation & Run Kinematic Guard (`reprocess_session_orientations.py`)
Calibrates BLE packet batching latency (`med_dt`), runs state-gated 3D AHRS (`OrientationAhrs`) and `KinematicGuard` ($\Delta t \le 15\text{ms}$ contiguous check), and backfills `p_rot_qx..w`, `blade_pitch_deg`, `face_angle_deg`, `swing_yaw_deg`, and `is_kinematically_valid` into both `ground_truth_aligned.csv` and the unified Parquet files:
```bash
python3 pipelines/reprocess_session_orientations.py
```

### Step 4: Rebuild & Push Phone Room v12 SQLite Database (`reprocess_sessions.py`)
Rebuilds `scratch/cricket_tracker_database.db` (57-column `innings_events` table) and pushes it to the connected Android phone via ADB:
```bash
python3 pipelines/reprocess_sessions.py
```

## 3. Verification Checklist
1. **Python AHRS & Guard Unit Tests**:
   ```bash
   PYTHONPATH=pipelines python3 -m unittest pipelines/test_ahrs_and_guard.py
   ```
2. **Android Room v12 Migration & DDL Parity Test**:
   ```bash
   ./gradlew :app:testDebugUnitTest --tests "com.mrpeel.cricketbattingtracker.data.AppDatabaseMigrationTest"
   ```
3. **Database Sanity Check**: Verify that the target session in `scratch/cricket_tracker_database.db` has `"Session Started"`, all expected physical shots with non-null `bat_name` / `bat_weight_grams`, and `"Session Ended"`, with zero duplicate blocks.
