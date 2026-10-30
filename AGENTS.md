# Pitch Analytix Pro — Agent System Configuration & Entrypoint

Welcome to the Pitch Analytix Pro (Cricket Batting Tracker) workspace. This file serves as the bootstrap context for agent execution.

## 👥 Roles & Governance
- **Architect (User)**: Defines high-level design, product requirements, and features. Reviewer of plans.
- **Executor (Agent)**: Proposes plans, executes implementation tasks, runs verification checks, and commits code.

## 📂 Reference Documents (Progressive Disclosure)
All reference documents reside under the `.agents/` folder. **Read these on-demand when relevant to your active task—do not ingest all files unconditionally:**
- **[.agents/ACTIVE_CONTEXT.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/ACTIVE_CONTEXT.md)**: Current system objectives, active phase, recent feature backlog, and session state. Consult when aligning on feature requirements or updating task progress.
- **[.agents/ARCHITECTURE.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/ARCHITECTURE.md)**: Multi-sensor pipeline architecture (Wear OS foreground logging, Phone batch ONNX inference, 3D Bat Orientation AHRS, Room SQLite schema, Python pipeline). Consult when modifying kinematics, data formats, or service pipelines.
- **[.agents/LEARNINGS.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/LEARNINGS.md)**: Active architectural discoveries, invariant failure traps (Room v12 parity, BLE packet gaps, AHRS modulo arithmetic, 16KB page alignment), and critical bug fixes. Consult before touching database schemas, sensor streaming, or ONNX runners.
- **[.agents/change_logfile.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/change_logfile.md)**: Historical archive of completed features (B-001 through B-090).
- **[.agents/archive/LEARNINGS_ARCHIVE.md](file:///Users/neilkloot/Code/CricketBattingTracker/.agents/archive/LEARNINGS_ARCHIVE.md)**: Historical archive of past bug analyses and experiments.
- **[docs/biomechanical_coaching_reference.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/biomechanical_coaching_reference.md)**: Living reference of all biomechanical flaws, coaching notes, corrective drills, and real-time audio/earcon feedback used in the app. **MUST be kept up to date** whenever modifying `LiveKinematicCoach.kt`, `EarconAudioPlayer.kt`, `BiomechanicalUiMapper.kt`, or `DiagnosticRulesEngine.kt`.

## 🚫 Strictly Forbidden Tools
- **DO NOT USE WHISPER AI**: Local Whisper models (like Whisper `base` or `tiny`) are strictly forbidden for audio narration transcription. They are highly fragile under continuous background noise (such as bowling machine hum), leading to hallucinated repetition loops and missing anchors. Gemini's direct audio transcription must always be used instead, with systematic clock drift resolved mathematically at the sensor alignment layer (e.g., using 2D Joint Offset and Linear Drift Rate Optimization).

## 🚫 Strictly Forbidden Metrics Reporting
- **NEVER report training-set or cross-validation accuracy as model performance**. Scikit-learn `cross_val_score`, training accuracy, or any metric computed on data used for training (including synthetic/augmented data) is a training diagnostic only. It must NEVER be presented to the user as the model's accuracy or used to justify model quality.
- **ONLY report real-world ground truth accuracy** from `SwingDetectorGroundTruthTest.kt` scorecard results (or the authoritative `score_phone_pipeline.py` script output). This is the single source of truth for model performance.
- When reporting accuracy improvements, always compare the **ground truth scorecard before vs after** — never synthetic CV metrics.

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