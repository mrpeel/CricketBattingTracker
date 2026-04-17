# Cricket Batting Tracker App (Wear OS & Android)

This document outlines the architecture for an automated cricket batting tracker using a Samsung Galaxy Watch 7 worn on the top hand. It synchronizes standard fitness metrics directly to the Samsung/Google Health ecosystem and routes custom kinematic cricket data to a dedicated companion mobile app.

## User Review Required
> [!IMPORTANT]
> **Kinematics & Shot Detection Reality**
> 
> Achieving reliable automatic detection of shots exclusively from wrist IMU data requires a robust mechanism to filter out noise, bat-twirling, and repositioning. Our Python data analysis proved that real-time semantic shot-type inference (Pull vs. Drive) is unreliable due to the sheer variety of individual execution styles.
> 
> Instead, our Wear OS pipeline uses a **6-State Ring-Buffered State Machine**: 
> 1. Requires a strict `Quiet Stance` (std < 0.9 rad/s) barrier to reset the lock and explicitly suppress double-counting.
> 2. Searches a narrow contact Window (-0.45s to +0.75s) around the derived Swing Peak.
> 3. Captures exactly when the true physics shock arrives, generating the relative Sweet Spot (Shock-to-Speed) ratio.
> 
> This approach allows the watch to track every genuine Swing + Contact event immediately on device, operating directly on batched Android sensor events in constant O(1) memory via primitive `FloatArray` ring buffers.

## Proposed Changes

We will build a multi-module Kotlin Android project encompassing both the Watch OS and the Smartphone OS.

---
### Android App Setup & Foundation

- Initialize a standard modern Android project utilizing **Jetpack Compose** for all UI elements.
- Create two distinct modules:
  - `:wear` - The Wear OS target for the Galaxy Watch 7.
  - `:app` - The standard Android mobile target for post-innings review.

---
### `:wear` - Wear OS Tracker Module

This module runs natively on the watch and handles all data ingestion.
- **Foreground Service**: To ensure the sensor data continues to be tracked faithfully while the watch screen is off.
- **SensorManager Implementation**: Hooks into high-frequency hardware sensors (Accelerometer and Gyroscope) to record the 3D vectors of the left (top) wrist. 
- **Swing Detection Utility**: A processing loop that detects threshold spikes in angular velocity (indicating a swing) and sudden negative acceleration spikes (indicating ball-bat impact).
- **Health Services API (`ExerciseClient`)**: We will tap into the official Wear OS Health integrations to securely record standard activity (like calories and distance run). This automatically guarantees interoperability with Samsung Health.

---
### Data Sync Hub

We will use the **Wearable Data Layer API** to bridge the devices.
- High-frequency kinematics and the detected "timeline events" (e.g., "Event 1: Swing detected at 60km/h", "Event 2: Distance run 20m") are cached locally on the watch.
- When connected to the phone post-innings, the DataLayer seamlessly streams the timeline JSON payload natively to the phone.

---
### `:app` - Mobile Companion UI

This is the phone application used for post-innings review.
- **Room Database**: For persisting multiple innings.
- **Summary Dashboard**: Displays aggregate metrics (Total distance, max bat speed observed, total shots/swings detected).
- **Activity Timeline**: A vertical tracking list (think of a traditional cricket over-by-over ticker) that lays out exactly what happened, step by step, ordered chronologically.

## Verification Plan

### Automated Tests
- Unit tests validating the signal-processing math (e.g., detecting a peak in an array of IMU floating-point numbers).

### Manual Verification
- We will boot up a Wear OS emulator (or execute via Android Studio to the physical watch) to verify the sensor background service stays alive when the screen is disabled.
- Simulate Bluetooth payload drops from the Watch target to the Phone target to ensure the Timeline UI populates successfully.
