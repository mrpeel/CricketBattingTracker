# Change Logfile: Pitch Analytix Pro

This file archives completed catalog items from `ACTIVE_CONTEXT.md` to conserve token quota.

| Feature ID | Feature Name | Description | Status | Verification Method |
|---|---|---|---|---|
| B-006 | Watch Teardown Crash | Fix lateinit healthServicesManager crash on onDestroy | Completed | E2E verification |
| B-007 | Transcription Reliability | Implement structured Pydantic response schema + targeted prompts on Gemini 3.5 Flash for audio narration parsing | **Completed** | Pipeline re-run producing correct 69/69 shot count for 20-min session |
| F-013 | Full Watch Sensor Stack Logging | Background logging of up to 15 physical/virtual Wear OS sensors when raw logging/diagnostics is enabled | **Completed** | E2E simulation verify 11 CSV files |
| B-008 | Stance Gate Optimization | Tune thresholds and timings to C: Moderate configuration to eliminate walking break FPs and timeout lockouts | **Completed** | E2E Simulation on session-2026-06-01_12-23-38 |
| B-009 | Random Forest Integration | Integrate scikit-learn Random Forest model into SwingDetector Kotlin logic | **Completed** | Parity test and physical scorecard alignment |
| B-010 | Clock Offset Optimization | Implement coarse-to-fine clock offset grid search in data collection pipeline | **Completed** | Verification check against all 7 trusted sessions |
| B-014 | Classifier Size Optimization | Compress Random Forest model using flat array representations and automated variant pruning to reduce Watch APK size to 2.8MB | **Completed** | Parity tests & APK size verification |
| B-015 | Bat Type Extraction | Add bat type (Gray Nicolls Giant, Eye In, Game bat) extraction and stateful forward-filling to narration pipeline | **Completed** | Run `scratch/validate_bat_parsing.py` |

