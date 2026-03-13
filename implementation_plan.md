# Cricket Batting Tracker App (Wear OS & Android)

This document outlines the architecture for an automated cricket batting tracker using a Samsung Galaxy Watch 7 worn on the top hand. It synchronizes standard fitness metrics directly to the Samsung/Google Health ecosystem and routes custom kinematic cricket data to a dedicated companion mobile app.

## User Review Required
> [!IMPORTANT]
> **Machine Learning & Auto-Detection Reality for V1**
> 
> Achieving 100% automatic detection of specific shot types (e.g., Pull vs. Drive vs. Cut) exclusively from wrist IMU data without the user explicitly telling the watch what they did is a complex classification problem requiring a trained Machine Learning model. 
> 
> For **V1**, I propose we build the core end-to-end system: 
> 1. The Wear OS background tracking service
> 2. The Bluetooth device sync 
> 3. The Mobile Activity Timeline UI
> 4. A **heuristic physics algorithm** using Accelerometer/Gyroscope peaks to automatically detect when an "impact" or "swing" occurs, and approximate the bat speed from wrist angular velocity.
> 
> Once V1 is built, you can use it in the nets. The data captured during these sessions can then be exported to train a custom on-device AI model (like TensorFlow Lite) for **V2**, which will categorize the exact semantic shot types. We should also lean on Google's Health Services API to calculate the running distances and automatically sync to Samsung Health.

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
