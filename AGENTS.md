# Pitch Analytix Pro — Agent System Configuration & Entrypoint

Welcome to the Pitch Analytix Pro (Cricket Batting Tracker) workspace. This file serves as the always-on bootstrap context and guardrail set for agent execution.

## 👥 Roles & Governance
- **Architect (User)**: Defines high-level design, product requirements, and features. Reviewer of plans.
- **Executor (Agent)**: Proposes plans, executes implementation tasks, runs verification checks, and commits code.

## 📂 Reference Documents (Progressive Disclosure)
All reference documents reside under `.agents/` and `docs/`. **Read these on-demand when relevant to your active task—do not ingest all files unconditionally:**
- **[.agents/ACTIVE_CONTEXT.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/ACTIVE_CONTEXT.md)**: Current system objectives, active phase, recent feature backlog (`B-110`+), latest benchmark metrics, and verification procedures.
- **[.agents/ARCHITECTURE.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/ARCHITECTURE.md)**: Multi-sensor pipeline architecture (Wear OS foreground `.bin.gz` logging, Phone batch TCN ONNX inference, 3D Bat Orientation AHRS, Live In-Ear Coaching, Room SQLite v12 schema, Python pipeline).
- **[.agents/LEARNINGS.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/LEARNINGS.md)**: Fast-lookup catalog of **active architectural invariants and failure traps** grouped by subsystem (Room v12 schema parity, Python–Kotlin TCN/AHRS parity, single-flight mutex, BLE packet gaps, start-time hierarchy). **Consult before modifying database schemas, sensor streaming, AHRS, or ONNX runners.**
- **[docs/biomechanical_coaching_reference.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/biomechanical_coaching_reference.md)**: Living reference of all biomechanical flaws, coaching notes, corrective drills, and real-time audio/earcon feedback used in the app. **MUST be kept up to date** whenever modifying `LiveKinematicCoach.kt`, `EarconAudioPlayer.kt`, `BiomechanicalUiMapper.kt`, or `DiagnosticRulesEngine.kt`.
- **Historical Archives (Read only when investigating historical regressions)**:
  - **[.agents/change_logfile.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/change_logfile.md)**: Archive of completed features (`B-001` through `B-116`).
  - **[.agents/archive/LEARNINGS_ARCHIVE.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/archive/LEARNINGS_ARCHIVE.md)**: Detailed historical post-mortems and experiment logs (`#1` through `#207`).

## 🛠️ Workspace Skills (On-Demand Runbooks)
Specialized procedural workflows are packaged in `.agents/skills/` and auto-discovered by Antigravity:
- **`session-ingestion-and-reprocessing`** ([SKILL.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/skills/session-ingestion-and-reprocessing/SKILL.md)): Ingesting physical watch + Polar sessions, running `automate_pipeline.py`, updating 3D AHRS orientations (`reprocess_session_orientations.py`), and rebuilding the phone Room v12 SQLite database (`reprocess_sessions.py`).
- **`tcn-training-and-scorecard`** ([SKILL.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/skills/tcn-training-and-scorecard/SKILL.md)): Retraining and evaluating `BatPlaneGeometryThreeFamilyTCN` (`pipelines/train_and_evaluate_full_scorecard.py`), verifying the Production Quality Gate against the 12-session Holdout Test Set, and exporting `tcn_ultimate_baseline.onnx`.

## 🔒 Critical System Invariants (Always Enforce)
1. **Python ↔ Kotlin Train–Serve Parity**: Any change to Stage 1 stance thresholds, Stage 2 TCN routing/rejection (`head_reject` threshold `0.35`, Power Drive soft-routing `0.85`), 3D AHRS Euler conventions (extrinsic `'zyx'`), or consistency gates MUST be updated identically in both Python (`pipelines/telemetry_engine.py`, `pipelines/reprocess_session_orientations.py`) and Kotlin (`TcnModelRunner.kt`, `PhoneSwingDetector.kt`, `OrientationAhrs.kt`).
2. **Room Database v12 Schema & Identity Hash Parity**: Whenever `InningsEvent.kt` or `AppDatabase.kt` changes, `pipelines/reprocess_sessions.py` MUST be updated with the exact column DDL, `INSERT` placeholders (currently 57 columns), and Room identity hash (`36946e68af413e8cc2fca0555e69b534`), verified by `AppDatabaseMigrationTest.kt`.
3. **Single-Flight Per-Innings Processing & Atomic DB Swap**: `PhoneSwingDetector.processSession` must acquire the per-innings `Mutex` and swap events inside a single `database.withTransaction { delete; insert }` block—never delete timeline events before replacement rows are ready.
4. **Authoritative Session Start-Time Hierarchy**: Always resolve session start timestamps in strict order: (1) `session_config.json` -> `start_time_ms`, (2) `latest_timeline.txt` -> `SYSTEM_START: Ts=`, (3) directory name regex, (4) directory `mtime`. Never rely on sync ZIP arrival timestamps alone.

## 🚫 Strictly Forbidden Tools & Metrics
- **DO NOT USE WHISPER AI**: Local Whisper models (`base`, `tiny`, etc.) are strictly forbidden for audio narration transcription due to hallucinated repetition loops under bowling machine hum. Always use Gemini audio transcription (or Deepgram Nova-3 where configured) with 2D clock drift alignment.
- **NEVER report training-set or cross-validation accuracy as model performance**: Scikit-learn `cross_val_score`, training accuracy, or synthetic/augmented CV metrics are training diagnostics only and must NEVER be presented as model accuracy.
- **ONLY report real-world ground truth accuracy**: Use the authoritative 12-session Holdout Test Set and Clean Benchmark scorecard generated by `pipelines/train_and_evaluate_full_scorecard.py` ([full_dataset_training_scorecard.md](file:///Users/neilkloot/Code/CricketBattingTracker/full_dataset_training_scorecard.md)) or `pipelines/score_phone_pipeline.py`. Always compare **ground truth holdout scorecard before vs. after**.

## 🧪 Common Verification Commands
```bash
# Android & Wear OS unit test suites
./gradlew :app:testDebugUnitTest :wear:testDebugUnitTest

# Assemble 16 KB page-aligned release APKs
./gradlew :app:assembleRelease :wear:assembleRelease

# Python AHRS and Kinematic Guard unit tests
PYTHONPATH=pipelines python3 -m unittest pipelines/test_ahrs_and_guard.py

# Physical hardware deployment
./deploy_physical.sh
```
