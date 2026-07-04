# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

48. **Whisper-Gemini Hybrid Transcriber & POWER DRIVE Class Separation (June 29, 2026)**:
    *   **The Problem**: Coarse Gemini timestamps led to timecode drift, but switching to Whisper caused severe repetition hallucinations ("Power shot Edge") due to continuous bowling machine hum. Additionally, grounded power hits needed separation from lofted power shots to prevent model corruption.
    *   **The Solution**:
        1. Implemented a Whisper-Gemini Hybrid Transcriber in [automate_pipeline.py](file:///Users/neilkloot/Code/CricketBattingTracker/automate_pipeline.py) using Whisper segment bounds as anchors for the Gemini structured LLM transcription.
        2. Set `condition_on_previous_text=False` in Whisper to break repetition loops over bowling machine hum, and added python post-processing rules to map phonetic mishearings (e.g. "now I hit", "how we hit", "how are you") to `"Power drive"`.
        3. Configured `compile_dataset.py` to extract `POWER DRIVE` as an independent class if `grav_x_max <= 5.5 m/s²`, and added quality control filters to ignore misaligned stationary wiggles (`gyroMag < 9.0 rad/s`).
    *   **Result**: The new 8-class Random Forest model achieved a record cross-validation accuracy of **79.2%**. WearOS unit tests and parity alignment tests passed with 0 mismatches. Alignment precision on today's session increased from 0.47 to 0.64 with only 3 undetected shots remaining.

49. **Reverting to Direct Gemini & 2D Alignment (June 30, 2026)**:
    *   **CRITICAL DIRECTIVE: NEVER USE WHISPER AI FOR THIS PROJECT.** Local Whisper is completely unable to handle continuous bowling machine hum, leading to silent drops and repeat-hallucination loops.
    *   **The Problem**: Local Whisper was extremely fragile under loud bowling machine hum, leading to incorrect and missing segment anchors. Gemini's direct audio transcription was highly accurate but suffered from cumulative clock drift relative to WearOS sensors over long sessions.
    *   **The Solution**:
        1. Ripped out Whisper completely from `automate_pipeline.py` to restore Gemini's direct audio transcription.
        2. Modified the timecode parser to robustly handle LLM-mixed `M.SS` / raw seconds timestamps using a monotonic tracking loop.
        3. Upgraded the alignment calibration from a 1D offset search to a **2D Joint Offset and Linear Drift Rate Optimization grid search**.
    *   **Result**: Resolved the transcription repetition loops and missing anchors completely. Direct Gemini transcriptions now align perfectly with WearOS sensor events (under 0.9s lag difference across the entire 18-minute session).

50. **Improved Phone UI Session Details & Dependency Fix (July 2, 2026)**:
    *   **The Problem**: The details page for post-session analytics suffered from vertical bloat and lacked critical aggregation statistics (Avg Bat Speed, Max Efficiency) and detailed breakdowns (shot type summaries). It also lacked the option to toggle between absolute clock time and relative session duration. Additionally, adding CameraX dependencies caused a Kotlin build conflict with Guava/ListenableFuture on macOS.
    *   **The Solution**:
        1. Refactored the details screen to use a single parent `LazyColumn` for seamless scrolling and jump-to-shot auto-scrolling animations.
        2. Redesigned the cards to be highly compact, grouping speed, efficiency, reaction, blade, and launch metrics horizontally in a single row, and removing unnecessary wrist and finish angles.
        3. Added a dynamic Composable table of shot types played, with max/avg metrics, avg face, avg launch, and colored indicator dots.
        4. Implemented dynamic toggling between absolute clock time and relative session time (offset since the first event of the session) globally and by card-tapping.
        5. Resolved the CameraX build conflict by explicitly adding the `com.google.guava:guava:31.1-android` dependency to resolve classpath exclusions.
    *   **Result**: Tested and compiled successfully. All tests pass with no compilation errors.

51. **Robust Chronological Transcription & Fallback Gates (July 3, 2026)**:
    *   **The Problem**: Gemini's transcription of audio timecodes was inconsistent, mixing rolling seconds (resetting to 0 every minute) with absolute `M.SS` formats within the same session. This formatting drift corrupted the calculated offsets, leading to bad alignments. Additionally, the system was vulnerable to aligning non-overlapping or corrupt sessions blindly.
    *   **The Solution**:
        1. Updated the Gemini transcription prompt with strict linear timeline instructions.
        2. Added a robust chronological timecode parser in `automate_pipeline.py` to reconstruct rolling seconds into a monotonic absolute timeline.
        3. Upgraded the alignment validation to check that the fallback rate of active swings (ignoring stances/leaves) is <= 25%, automatically deleting `ground_truth_aligned.csv` on failure to raise immediate alarms.
        4. Removed the misleading comparison report (`compare_with_timeline`) against `latest_timeline.txt` to clarify that alignment is performed directly against raw sensor peaks.
    *   **Result**: Successfully aligned all 24 valid sessions. Restored combined ML F1 score back to **0.7670** (76.7%) from 0.56.

52. **Lossless Session Compression & Audio Speech Optimization (July 3, 2026)**:
    *   **The Problem**: 25 sessions accumulated 1.8 GB of disk space and 25,940 files, creating severe Git and backup bloat. Most files were redundant 6-second segment CSV slices, and the raw audio narration recordings were stored at a high stereo bitrate (~20MB/session).
    *   **The Solution**:
        1. Compressed narration audio to speech-optimized 16kHz mono 24kbps AAC in-place via FFmpeg after pulling (reducing files by ~81%).
        2. Switched Watch sensor logs to lossless Gzip compression (`Watch*.csv` -> `Watch*.csv.gz`), saving ~75% disk space.
        3. Modified `SensorCsvReader` in Kotlin unit tests (`SwingDetectorGroundTruthTest.kt`) to natively read `.csv.gz` files using standard Java `GZIPInputStream` (zero dependencies).
        4. Updated `compile_dataset.py` to transparently load `.csv.gz` logs via Pandas.
        5. Disabled redundant individual segment CSV outputs in the pipeline.
    *   **Result**: Reduced total disk usage of live sessions from **1.8 GB to 461 MB** (74.4% savings) and file count from **25,940 to 452 files** (98.2% reduction) with zero loss of raw kinematic data. All Kotlin tests and Python training scripts pass successfully.

53. **Parquet Integration & Adversarial Verification (July 3, 2026)**:
    *   **The Problem**: Reading from partitioned Parquet directories via Pandas (`pd.read_parquet(root_path, filters=...)`) forces Pandas to infer a unified schema across all partitioned subfolders. Because different sensor types contain completely different schemas (e.g. `gyro` has `x,y,z`, `game_orient` has `qx,qy,qz,qw`), this schema inference drops columns (like `qx`) or fails with `KeyError`.
    *   **The Solution**: Modified the Parquet loading code to target the partition subdirectories directly (`pd.read_parquet(os.path.join(root_path, "sensor_type=game_orient"), filters=[("session_id", "==", session_id)])`). This completely isolates the schema context of the target sensor type and reads files instantly.
    *   **Result**: All adversarial analysis tests ran and compiled successfully, generating a comprehensive alignment and stance gate performance report (`last_session_analysis_update.md`) across all 25 sessions.

54. **Validation Check Swing Filters Alignment (July 4, 2026)**:
    *   **The Problem**: After updating the clock synchronization algorithm to treat defenses, blocks, edges, and misses as alignment non-swings (which use the fallback path), the pipeline crashed during validation with a `RuntimeError: ❌ Alignment failed due to high fallback rate (49.4%).` This happened because the validation check's `active_swings` calculation still counted those low-energy shots as active swings, leading to a false high fallback rate calculation.
    *   **The Solution**: Modified `active_swings` in `automate_pipeline.py`'s validation block to filter out defenses, blocks, edges, and misses, aligning the validation check definitions with the clock offset search's peak matching filters.
    *   **Result**: Validated that `automate_pipeline.py` runs successfully on local session folders without crashing and accurately computes high-energy swing alignment fallback rates.

55. **Restoring Accidental Disabling of Compression & Parquet (July 4, 2026)**:
    *   **The Problem**: Today's session data was neither gzipped nor appended to the combined Parquet database. Investigating `automate_pipeline.py` revealed that the calls to `append_to_combined_parquet` and `compress_session_csvs` were placed at the end of the `compare_with_timeline` function. Since `compare_with_timeline` was removed from the main execution path in entry 51 to clarify alignment logic, these two critical calls were accidentally deactivated.
    *   **The Solution**: Moved the database append and Gzip compression function calls to the end of the `main()` function execution path in `automate_pipeline.py`.
    *   **Result**: Ran the pipeline on the uncompressed session, successfully appending all 8 watch sensor logs (approx. 430,000 rows) to `combined_sensor_data.parquet` and compressing the 14 raw CSV files to `.csv.gz`.







