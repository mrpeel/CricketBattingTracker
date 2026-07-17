# Learnings: Pitch Analytix Pro

This document captures resolved bugs, architectural changes, key logical findings, and historical evaluation scorecards across development sessions.

---

## 💡 Technical Decisions & Discoveries

84. **Phone-Bound Batch Processing Architecture (July 17, 2026)**:
    *   **The Problem**: Real-time swing detection and Random Forest classification on the watch app consumed battery and were fragile during game days when the watch disconnected from the phone boundary. Additionally, the Polar Verity Sense's 16MB internal storage can only buffer high-frequency 416Hz IMU data for ~10 minutes, making offline Polar recording infeasible.
    *   **The Solution**: Transitioned the architecture to phone-side batch processing:
        *   **Watch**: Registers sensors at `SENSOR_DELAY_FASTEST`, disables active `SwingDetector` loops, and packages the raw session directory as a ZIP archive on stop, streaming it to the phone via GMS `ChannelClient` path `/raw_session_data`.
        *   **Phone**: `DataSyncListenerService` unzips watch logs, locates the latest Polar folder, and triggers `PhoneSwingDetector` to execute linear alignment regression, Polar impact peak detection (> 24.5 m/s²), stance look-back window geodesic search, feature extraction, Random Forest classification, and video clipping entirely offline.
        *   **Python Pipeline**: Modified `automate_pipeline.py` to pull consolidated watch + Polar folders directly from the phone companion app's path, bypassing slow watch Wi-Fi ADB.
        *   **Phone UI**: Added a circular progress loading indicator on the session details screen if raw logs are still unzipping and batch processing is in progress.
    *   **Result**: Watch battery usage is minimized, data alignment is preserved, and the system functions seamlessly offline on game days with processing consolidated on the phone.

85. **Custom Minimalist Navigation Vector Drawables (July 18, 2026)**:
    *   **The Problem**: The phone companion app's bottom navigation bar used generic emojis ("📊", "🎙️", "📋") which looked simple and unpolished, falling short of premium UI design aesthetics.
    *   **The Solution**: Created three high-fidelity, clean minimalist vector XML drawables in `res/drawable/` matching the user's uploaded spec:
        - `ic_dashboard.xml`: A side-facing cricket helmet with ear guards and jaw grill protection, combined with wave lines representing telemetry streams.
        - `ic_record.xml`: A geometric, faceted cricket ball outline detailing seams and facets, including a solid "REC" recording indicator.
        - `ic_history.xml`: A binder-ring calendar showing an internal trending line chart and a prominent swooping arrow extending out to represent progression history.
        Mapped these assets inside `MainActivity.kt` using Jetpack Compose's `Icon` and `painterResource`.
    *   **Result**: Bottom tab navigation renders with custom abstract vector lines, providing a highly premium, state-of-the-art look.
