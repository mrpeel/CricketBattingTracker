# Local Testing Guide for Cricket Batting Tracker on macOS

This guide explains how to build, deploy, and test the `app` (Phone) and `wear` (Watch) modules of the Cricket Batting Tracker utilizing a Mac.

## Prerequisites

- **macOS** with **Android Studio** installed.
- Android platform-tools (`adb`) installed and added to your PATH (default location: `~/Library/Android/sdk/platform-tools`).
- USB cable or Wi-Fi connected for physical device debugging.

## 1. Device Setup

You can use either Android Studio Emulators (AVDs) or physical devices.

### Using Emulators
Launch Android Studio and use the **Device Manager** to start:
- An Android Phone Emulator (for the `:app` module).
- A Wear OS Emulator (for the `:wear` module).

### Using Physical Devices
1. **Enable Developer Options**: Go to Settings -> About Phone/Watch -> repeatedly tap "Build Number" until Developer Options are enabled.
2. **Enable USB Debugging** on your phone (or Wireless Debugging for the watch).
3. Connect devices to your Mac. If using the watch through wireless debugging, connect using:
   ```bash
   adb connect <watch-ip-address>:<port>
   ```

Verify your devices are connected:
```bash
adb devices
```

## 2. Building the Applications

The project uses Gradle for builds. From the terminal in the root directory:

```bash
./gradlew assembleDebug
```

This will generate the required APKs under the `/build/outputs/apk/` directory of their respective modules.

## 3. Deploying using ADB

You can bypass Android Studio's UI to deploy directly from the command line once your devices or emulators are connected.

**Deploy the Phone App:**
```bash
adb -s <phone-device-id> install app/build/outputs/apk/debug/app-debug.apk
```

**Deploy the Watch App:**
```bash
adb -s <watch-device-id> install wear/build/outputs/apk/debug/wear-debug.apk
```

*(Note: If you only have one device attached, you can drop the `-s <device-id>` flag).*

## 4. Running Tests

### Automated Tests
To run unit tests locally on your Mac's JVM without needing a device/emulator:
```bash
./gradlew test
```

To run instrumented integration and UI tests on your connected physical devices or emulators:
```bash
./gradlew connectedAndroidTest
```

### Manual Verification
After the applications have been successfully installed, locate them in the app drawer of your emulator or physical device. Launch both the watch and phone apps to verify synchronization, UI responsiveness, and correct rendering.
