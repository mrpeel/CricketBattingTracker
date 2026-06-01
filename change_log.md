# Change Log: Pitch Analytix Pro

This file tracks the historical changes and completed features for Pitch Analytix Pro that have been archived from the active feature backlog.

---

## Completed Features

| Feature ID | Feature Name | Description | Verification Method |
|---|---|---|---|
| F-001 | Continuous Sampling | Listen to Accel/Gyro/Gravity/Rotation Vector at 50Hz | Unit Tests & Emulation |
| F-002 | Foreground Service | Keep `TrackerService` running when screen is dark | Physical target verification |
| F-003 | Wearable Sync | Timeline JSON sync over Wearable Data Layer API | E2E Simulation |
| F-004 | SQLite Persistence | Local Room database storage on the phone companion | Phone UI verification |
| F-005 | Health Connect Sync | Push Innings and Heart Rate profiles under Cricket type | Health Connect client check |
| F-006 | Narration Pipeline | Pull files, run auto-start sync, transcribe via Gemini | Running pipeline script |
| F-007 | Companion Audio Recording | Companion App Audio Recording & Local Transcription Integration | E2E verification |
| F-008 | Facing-Up Anchor | 4-condition facing-up gate anchors all shot detection to a confirmed guard stance | GroundTruthTest + next live session |
| F-009 | Game Rotation Vector | Switch primary bat orientation quaternion to TYPE_GAME_ROTATION_VECTOR (no magnetometer) | Build passes; next live session |
| F-010 | Step Detector Integration | TYPE_STEP_DETECTOR feeds a walking kill-switch into the facing-up gate | Build passes; next live session |
| F-011 | Watch UI Stance Indicator | Pulsing 'Facing Up' badge on Wear OS UI for real-time stance confirmation | Manual stance check on watch screen |
| F-012 | Stance Break Tolerance | 1.2s break-tolerance window handles transient failures (bat rocking) during stance lock | SwingDetectorTest unit tests |
