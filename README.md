# Pitch Analytix Pro (Cricket Batting Tracker)

Pitch Analytix Pro is a professional-grade cricket training companion that uses Wear OS smartwatch inertial sensors (IMU), local kinematic heuristics, automated audio-sensor sync pipelines, and a companion Android dashboard to capture, align, and analyze batting sessions.

---

## 🏗️ System Components

The project consists of three core components:

1.  **Wear OS Smartwatch Application (`wear`)**:
    *   Runs a foreground service tracking gyroscope, accelerometer, and gravity sensors at 50Hz.
    *   Employs a **4-state kinematics machine** to detect batting swings and exclude false positives (like walks, wiggles, and steps) using a hybrid stance gate.
    *   Evaluates shot types in real-time on-device using a transpiled, optimized **Random Forest classifier**.
2.  **Companion Android Phone Application (`app`)**:
    *   Receives data payloads from the watch via the Google Play Services Wearable Data Layer API.
    *   Saves session details in a local Room SQLite database.
    *   Integrates workout metrics and heart rate logs directly with Samsung Health / Google Health Connect.
    *   Displays a beautiful, OLED-friendly Dark Mode UI ("Digital Pavilion") for glanceable post-session summaries.
3.  **Data Processing & Alignment Pipeline (`automate_pipeline.py`)**:
    *   Pulls raw watch sensor CSVs and phone earbud audio recordings via ADB.
    *   Correlates watch impact spikes with physical bat-tap transients in the audio recording using regression-based sync-tap optimization.
    *   Calls the Gemini API to transcribe voice narrations and slice corresponding sensor segments for ground-truth model training.

---

## ⚡ Capabilities

*   **Biomechanical Stance Gating**: Employs step detectors and standard-deviation filters to lock onto the batsman's guard stance, avoiding walking wiggles.
*   **Real-time Shot Classification**: Identifies shot classes (Cover Drive, Pull, Sweep, Defense, Push, Glance, etc.) directly on the watch.
*   **Acoustic & Kinematic Synchronization**: Calibrates watch/phone clock drift using bat-tap audio transient alignment.
*   **Health Integrations**: Synchronizes training energy and heart rate to major mobile health repositories.
*   **OLED Optimized UI**: Uses true-black backgrounds (`#000000`) and high-visibility neon accents (`#58FF63`) for power-efficient outdoor use.

---

## 📂 Project Documentation

Deep-dive documentation can be found in the [docs/](file:///Users/neilkloot/Code/CricketBattingTracker/docs) folder:

*   **Setup & Build Workflows:**
    *   [build-emulate.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/build-emulate.md) — How to build and run the applications on macOS emulators.
    *   [deploy_apps.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/deploy_apps.md) — Steps for deploying the build artifacts onto physical and test devices.
*   **Testing & Diagnostics:**
    *   [testing_guide.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/testing_guide.md) — Comprehensive guide to running E2E simulations and manual shot injections.
    *   [loading_and_analysing_session_data.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/loading_and_analysing_session_data.md) — Processing, aligning, and evaluating collected session outputs.
*   **Kinematics & Analytics Details:**
    *   [batting_top_hand_biomechanics.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/batting_top_hand_biomechanics.md) — The biomechanical principles of stance, walking, and running detection.
    *   [shot_wearos_calculations.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/shot_wearos_calculations.md) — The mathematical models of swing speeds, ratings, and classifications.
    *   [gemini_narration_prompt.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/gemini_narration_prompt.md) — The prompt schema for structuring Gemini voice annotations.
    *   [batting_shot_stats.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/batting_shot_stats.md) — Detailed statistics definitions for post-session reports.
*   **Design & UX Architecture:**
    *   [wear_os_design.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/wear_os_design.md) — UI Specifications and battery conservation strategies for Wear OS smartwatches.
*   **Historical Plans & Walkthroughs:**
    *   [implementation_plan.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/implementation_plan.md) — Previous feature layout proposal documents.
    *   [walkthrough.md](file:///Users/neilkloot/Code/CricketBattingTracker/docs/walkthrough.md) — Engineering log summarizing recently verified modules.
