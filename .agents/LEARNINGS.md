# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

44. **Glance/Flick Renamed to Glance/Flick/Sweep (June 27, 2026)**:
    *   **The Problem**: The user was surprised to find that sweep shots were grouped into the `GLANCE/FLICK` category. Reviewing the biomechanical patterns validated this grouping, but the app UI category name itself was confusing.
    *   **The Solution**: Renamed the shot classification class from `GLANCE/FLICK` to `GLANCE/FLICK/SWEEP` across the entire ecosystem. This required updates to Python data compilation, model training pipelines (`compile_dataset.py`, `model_update_pipeline.py`, `automate_pipeline.py`), watch application source (`SwingDetector.kt`), and unit/Ground Truth verification tests.
    *   **Result**: Retrained the Random Forest classifier using the renamed category, successfully transpiling it to `GeneratedForest.kt`. Running the scorecard evaluation and WearOS test suite completed with 100% success.

45. **Splitting GLANCE/FLICK/SWEEP into GLANCE/FLICK and SWEEP (June 27, 2026)**:
    *   **The Problem**: The combined `GLANCE/FLICK/SWEEP` class mixed vertical-bat shots (glance, flick) with a horizontal-bat shot (sweep). Their physical geometries and swing plane characteristics are completely different (roll rotation vs yaw sweep), which made computing meaningful blade angles and launch angles at impact mathematically impossible.
    *   **The Solution**:
        1. Analyzed the raw narrations data and discovered that the Gemini prompt was already transcribing `"Sweep"`, `"Flick"`, and `"Leg Glance"` separately, resulting in 154 raw sweeps in the database. The combined class was purely a downstream mapping artifact in `normalize_shot_class()`.
        2. Fixed `normalize_shot_class()` to split `SWEEP` and `GLANCE/FLICK` into separate classes.
        3. Updated `generate_kotlin_forest.py` to support dynamic class counts (removing hardcoded `6` class assumptions that caused prediction index mismatches in Kotlin) and retrained the Random Forest model.
    *   **Result**: The Random Forest was retrained successfully with 7 classes. Tests pass with 0 mismatches against Python, and accuracy is high: `GLANCE/FLICK` (77.6%), `SWEEP` (81.5%).

46. **Biomechanical Blade & Launch Angle Kinematics (June 27, 2026)**:
    *   **The Problem**: The app lacked feedback to help batters understand how well they were striking the ball in terms of blade face angle (open/closed) and vertical trajectory loft (grounded/lofted).
    *   **The Solution**:
        1. Designed split-plane math. For vertical bat shots, launch angle is vertical pitch normal elevation, and blade angle is stance-relative horizontal yaw relative to shot lines. For horizontal bat shots (cuts/pulls/sweeps), launch angle is relative wrist roll, and blade angle is face yaw calibrated for lead-wrist arm extension offsets.
        2. Implemented these real-time calculations in `SwingDetector.kt` and populated extended `ShotData`.
        3. Sync parsing in `DataSyncListenerService` was upgraded to parse these values, storing them in a Room database (with database version bumped to 6).
        4. Rendered the calculated `BLADE` and `LAUNCH` metrics dynamically in the phone app's Compose dashboard item cards.
    *   **Result**: The implementation works natively on both the pipeline and WearOS/Android apps, backed by a comprehensive unit test suite (`testBladeAndLaunchAngles`).

47. **Power Shot Biomechanical Misalignment & Clock Alignment Drift (June 29, 2026)**:
    *   **The Problem**: The model showed very low classification accuracy for "Power Shots" in some sessions (e.g. session-2026-06-29_12-21-45), often misclassifying them as `PULL/HOOK` or `DRIVE/DEFENCE`.
    *   **The Solution**:
        1. Analyzed physical data and validated that grounded power hits (very hard shots kept along the ground to mid-on/mid-wicket) lack the lofted power shot biomechanical signatures (positive roll at impact and high overhead `grav_x_max` displacement). Instead, they naturally exhibit negative roll (forearm pronation to close the face) and low gravity X displacement, matching `PULL/HOOK` or `DRIVE/DEFENCE` kinematics.
        2. Uncovered a secondary pipeline issue: coarse-grained transcription timestamps from Gemini caused negative lag alignment penalties, mismatching the alignment window to stationary stance/wiggles, resulting in zero-energy training samples for power shots.
    *   **Result**: Identified that (a) grounded power hits must be narrated biomechanically (e.g. as pull/drive/flick) to prevent training noise, and (b) pipeline transcription should be run with `--local` to use high-precision Whisper timestamps, avoiding negative lag alignment penalties.

48. **Whisper-Gemini Hybrid Transcriber & POWER DRIVE Class Separation (June 29, 2026)**:
    *   **The Problem**: Coarse Gemini timestamps led to timecode drift, but switching to Whisper caused severe repetition hallucinations ("Power shot Edge") due to continuous bowling machine hum. Additionally, grounded power hits needed separation from lofted power shots to prevent model corruption.
    *   **The Solution**:
        1. Implemented a Whisper-Gemini Hybrid Transcriber in [automate_pipeline.py](file:///Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py) using Whisper segment bounds as anchors for the Gemini structured LLM transcription.
        2. Set `condition_on_previous_text=False` in Whisper to break repetition loops over bowling machine hum, and added python post-processing rules to map phonetic mishearings (e.g. "now I hit", "how we hit", "how are you") to `"Power drive"`.
        3. Configured `compile_dataset.py` to extract `POWER DRIVE` as an independent class if `grav_x_max <= 5.5 m/s²`, and added quality control filters to ignore misaligned stationary wiggles (`gyroMag < 9.0 rad/s`).
    *   **Result**: The new 8-class Random Forest model achieved a record cross-validation accuracy of **79.2%**. WearOS unit tests and parity alignment tests passed with 0 mismatches. Alignment precision on today's session increased from 0.47 to 0.64 with only 3 undetected shots remaining.

49. **Reverting to Direct Gemini & 2D Alignment (June 30, 2026)**:
    *   **The Problem**: Local Whisper was extremely fragile under loud bowling machine hum, leading to incorrect and missing segment anchors. Gemini's direct audio transcription was highly accurate but suffered from cumulative clock drift relative to WearOS sensors over long sessions.
    *   **The Solution**:
        1. Ripped out Whisper completely from `automate_pipeline.py` to restore Gemini's direct audio transcription.
        2. Modified the timecode parser to robustly handle LLM-mixed `M.SS` / raw seconds timestamps using a monotonic tracking loop.
        3. Upgraded the alignment calibration from a 1D offset search to a **2D Joint Offset and Linear Drift Rate Optimization grid search**.
    *   **Result**: Resolved the transcription repetition loops and missing anchors completely. Direct Gemini transcriptions now align perfectly with WearOS sensor events (under 0.9s lag difference across the entire 18-minute session).






