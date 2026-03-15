# Emulator Testing Guide for Cricket Batting Tracker

This guide explains how to build, deploy, and test the `app` (Phone) and `wear` (Watch) modules of the Cricket Batting Tracker locally using Android Emulators.

## Prerequisites

- Android SDK installed (`$HOME/Android/Sdk`)
- ADB (`platform-tools/adb`) and Emulator (`emulator/emulator`) tools available in your PATH or SDK directory.
- AVDs (Android Virtual Devices) created for both a Phone and a Wear OS watch.
  - Required AVDs for this project: `Pixel_6_API_34` and `GalaxyWatch7`.

## 1. Starting the Emulators

To list all available emulators:
```bash
~/Android/Sdk/emulator/emulator -list-avds
```

Start the phone emulator (e.g., `Pixel_6_API_34`):
```bash
ANDROID_AVD_HOME=~/.config/.android/avd ~/Android/Sdk/emulator/emulator -avd Pixel_6_API_34 -no-boot-anim &
```

Start the watch emulator (e.g., `GalaxyWatch7`):
```bash
ANDROID_AVD_HOME=~/.config/.android/avd ~/Android/Sdk/emulator/emulator -avd GalaxyWatch7 -no-boot-anim &
```

Verify that both devices are running and attached:
```bash
~/Android/Sdk/platform-tools/adb devices
```
You should see two `emulator-XXXX` devices listed.

## 2. Building the Applications

The project uses Gradle to manage builds. To build the debug APKs for both the phone and watch apps, open a terminal in the root of your project and run:

```bash
./gradlew assembleDebug
```

This will generate the following APKs:
- **Phone App:** `app/build/outputs/apk/debug/app-debug.apk`
- **Watch App:** `wear/build/outputs/apk/debug/wear-debug.apk`

## 3. Deploying to Emulators

If you only have one emulator running, you can install the APK directly using `adb install`:
```bash
~/Android/Sdk/platform-tools/adb install app/build/outputs/apk/debug/app-debug.apk
```

If multiple emulators are running, you must specify the target emulator using its serial number (`-s emulator-XXXX`).

Find the serial numbers using `adb devices`. Suppose the phone is `emulator-5554` and the watch is `emulator-5556`:

**Deploy the Phone App:**
```bash
~/Android/Sdk/platform-tools/adb -s emulator-5554 install app/build/outputs/apk/debug/app-debug.apk
```

**Deploy the Watch App:**
```bash
~/Android/Sdk/platform-tools/adb -s emulator-5556 install wear/build/outputs/apk/debug/wear-debug.apk
```

## 4. Running Tests

### Automated Tests
To run the automated instrumented tests on all attached emulators:
```bash
./gradlew connectedAndroidTest
```
This requires the emulators to be running. It will run the UI and integration tests defined in your `androidTest` directories.

To run regular unit tests (does not require emulators):
```bash
./gradlew test
```

### Manual Verification
Once deployed, you can launch the applications directly from the terminal or manually by interacting with the emulators.

To launch the phone app from the terminal:
```bash
~/Android/Sdk/platform-tools/adb -s emulator-5554 shell monkey -p com.mrpeel.cricketbattingtracker -c android.intent.category.LAUNCHER 1
```

To launch the watch app from the terminal:
```bash
~/Android/Sdk/platform-tools/adb -s emulator-5556 shell monkey -p com.mrpeel.cricketbattingtracker -c android.intent.category.LAUNCHER 1
```

By following these instructions, you can successfully emulate the physical hardware and verify the functionality and sync operations of your Cricket Batting Tracker system.
