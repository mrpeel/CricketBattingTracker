# Local Testing Guide for Cricket Batting Tracker

This guide explains how to build, deploy, and test the `app` (Phone) and `wear` (Watch) modules of the Cricket Batting Tracker locally using a Chromebook with Linux Development environment and ADB enabled.

## Prerequisites

- Chromebook with Linux Development Environment (Crostini) enabled.
- ADB debugging enabled in ChromeOS:
  1. Go to **Settings > Advanced > Developers > Linux development environment**.
  2. Turn on **Develop Android apps** -> **Enable ADB debugging**.
  3. Restart the Chromebook when prompted to apply changes.
- Android SDK installed (`$HOME/Android/Sdk`) in the Linux environment.
- ADB (`platform-tools/adb`) available in your PATH.
- (Optional) A physical Wear OS watch connected via wireless ADB or a cloud emulator for the `wear` module testing.

## 1. Connecting to the Chromebook Android Subsystem

The Chromebook's Android environment can be accessed directly from your Linux container via ADB.

Connect to the local Android container:
```bash
~/Android/Sdk/platform-tools/adb connect arc
```
*(Alternatively, your device may show up automatically or require `adb connect 100.115.92.2:5555` depending on your ChromeOS setup).*

A prompt may appear on your Chromebook screen asking to "Allow USB debugging". Check "Always allow" and click OK.

Verify the connection:
```bash
~/Android/Sdk/platform-tools/adb devices
```
You should see `arc`, an IP address, or `emulator-XXXX` representing the ChromeOS Android subsystem.

## 2. Building the Applications

The project uses Gradle to manage builds. To build the debug APKs for both the phone and watch apps, open a terminal in the root of your project and run:

```bash
./gradlew assembleDebug
```

This will generate the following APKs:
- **Phone App:** `app/build/outputs/apk/debug/app-debug.apk`
- **Watch App:** `wear/build/outputs/apk/debug/wear-debug.apk`

## 3. Deploying using ADB

With your Chromebook Android subsystem connected, you can install the phone APK directly to test the UI.

**Deploy the Phone App:**
```bash
~/Android/Sdk/platform-tools/adb -s arc install app/build/outputs/apk/debug/app-debug.apk
# Replace "arc" with your device's identifier from `adb devices` if different.
```

**Deploy the Watch App:**
For the watch app, connect your physical watch (e.g., Galaxy Watch) via Wireless Debugging:
1. Enable Developer Options and Wireless Debugging on your watch.
2. Note the watch's IP address and port from the Wireless Debugging screen.
3. Connect via ADB:
   ```bash
   ~/Android/Sdk/platform-tools/adb connect <watch-ip>:<port>
   ```
4. Install the watch APK:
   ```bash
   ~/Android/Sdk/platform-tools/adb -s <watch-ip>:<port> install wear/build/outputs/apk/debug/wear-debug.apk
   ```

## 4. Running Tests

### Automated Tests
To run the automated instrumented tests on your attached devices:
```bash
./gradlew connectedAndroidTest
```
This will run the UI and integration tests defined in your `androidTest` directories on the connected Chromebook Android instance and any connected watch.

To run regular unit tests (does not require a connected device):
```bash
./gradlew test
```

### Manual Verification
Once deployed, you can launch the applications directly from the Chromebook launcher or your watch's app drawer.

To launch the phone app from the terminal:
```bash
~/Android/Sdk/platform-tools/adb -s arc shell monkey -p com.mrpeel.cricketbattingtracker -c android.intent.category.LAUNCHER 1
```

By following these instructions, you can successfully test the app using your Chromebook's built-in Android capabilities.
