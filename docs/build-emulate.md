# Local Workflow: Building & Emulating on macOS

This document details the standard workflow for building and emulating the Cricket Batting Tracker on a Mac.

## 1. Prerequisites

- **Android Studio** installed on your Mac.
- **Android SDK** configured (this is usually located in `~/Library/Android/sdk/`).
- The necessary Android SDK Build-Tools and Platform SDKs for API 34 installed via the Android Studio SDK Manager.

## 2. Emulators (Android Virtual Devices - AVDs)

We use Android Studio's **Device Manager** to emulate both the phone and the watch.

1. Open Android Studio and launch the **Device Manager**.
2. **Phone Emulator**: Create a virtually emulated phone (e.g., Pixel 7) with Play Store services enabled.
3. **Watch Emulator**: Create a Wear OS 4 or newer virtual device.

## 3. Building

You can build the applications utilizing Android Studio, or locally via the command line with Gradle:

```bash
./gradlew assembleDebug
```

This will generate your APKs in:
- `app/build/outputs/apk/debug/app-debug.apk`
- `wear/build/outputs/apk/debug/wear-debug.apk`

## 4. Deployment

You can deploy the apps by simply pressing the "Run" (play) button inside Android Studio with the relevant run configuration (`app` or `wear`) and emulator selected.

For complete, step-by-step instructions on connecting to physical devices, deploying applications, and testing, see the:

👉 **[Testing Guide](testing_guide.md)**
