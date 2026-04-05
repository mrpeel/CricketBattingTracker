# Hybrid Workflow: CLI Testing

This document details the hybrid workflow used to develop the Cricket Batting Tracker. Because traditional Android emulators can be resource-intensive or crash the Chromebook environment, we utilize a combination of on-device testing via the Chromebook's built-in Linux/ADB environment alongside cloud testing, entirely bypassing Android Studio.

## 1. Automated Installation & Build

We have streamlined the setup and build process into a single script. It automatically downloads the Android SDK Command-line Tools, accepts the necessary SDK licenses, downloads the required build tools for API 34, runs the Gradle build, and attempts to deploy via ADB.

Run the provided installation script:
```bash
./install_and_build.sh
```

## 2. Manual Build Process

If you do not want to use the automated script, you can build the APKs locally using Gradle from your command line:

```bash
./gradlew assembleDebug
```

This will generate your APKs in:
- `app/build/outputs/apk/debug/app-debug.apk`
- `wear/build/outputs/apk/debug/wear-debug.apk`

## 3. Deployment

All testing is done locally by pushing the compiled APKs directly to your Chromebook's Android subsystem or your physical watch over ADB. Firebase Test Lab and App Distribution are no longer part of the standard workflow.

For complete, step-by-step instructions on connecting via ADB, deploying the applications, and running automated tests, please refer to the main testing documentation:

👉 **[Testing Guide](testing_guide.md)**
