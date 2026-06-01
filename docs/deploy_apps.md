# Pitch Analytix Pro: Application Deployment Guide

This guide walks you through the process of connecting your physical Android Phone and Wear OS Watch (or emulators) via the Android Debug Bridge (ADB) and deploying the Pitch Analytix Pro applications.

---

## 🛠️ Step 1: Set Up ADB Environment

Ensure that the Android SDK `platform-tools` are added to your shell path.

On macOS (default layout):
```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
```

To verify ADB is installed and visible:
```bash
adb version
```

---

## 📱 Step 2: Enable Debugging on Devices

### Android Phone
1. Open **Settings** ➔ **About Phone** ➔ tap **Build Number** 7 times to unlock Developer Options.
2. Go back to **Settings** ➔ **System** ➔ **Developer Options**.
3. Toggle **USB Debugging** (if using a cable) or **Wireless Debugging** (if over Wi-Fi) to **ON**.

### Wear OS Watch (e.g., Galaxy Watch 7)
1. Open **Settings** ➔ **About Watch** ➔ **Software Information** ➔ tap **Software Version** 7 times to unlock Developer Options.
2. Go back to the main Settings menu and select **Developer Options**.
3. Toggle **ADB Debugging** to **ON**.
4. Scroll down and toggle **Wireless Debugging** to **ON**.
   * Note the displayed IP Address and Port (e.g., `192.168.1.100:5555`).

---

## 🔗 Step 3: Connect via ADB

### Connection via USB (Cable)
Plug your phone (or watch charger cradle) into your computer. Run:
```bash
adb devices
```
Check your device screen for a dialog box asking to **Allow USB Debugging** and select **Allow** (check "Always allow from this computer" for convenience).

### Connection via Wireless Debugging (Wi-Fi)
Ensure your computer and devices are connected to the **same Wi-Fi network**.

1. Connect your phone:
   ```bash
   adb connect <phone-ip>:<port>
   ```
2. Connect your watch:
   ```bash
   adb connect <watch-ip>:<port>
   ```
3. Run `adb devices` to verify both are successfully connected:
   ```text
   List of devices attached
   192.168.1.100:5555   device (Watch)
   adb-serial-number    device (Phone)
   ```

---

## 🚀 Step 4: Run the Deployment Scripts

We have provided dedicated helper scripts to compile and install the applications automatically.

### Option A: Complete Physical E2E Deploy (Phone + Watch)
If you have a physical phone and watch connected concurrently, run the following command from the root of the project workspace:
```bash
./deploy_physical.sh
```

**What this script does:**
1. Detects and categorizes connected devices into Phone and Watch handles.
2. Automatically compiles the debug APKs for both modules using Gradle:
   ```bash
   ./gradlew assembleDebug
   ```
3. Installs the watch application (`wear-debug.apk`) and phone application (`app-debug.apk`).
4. Automatically grants critical Wear OS runtime permissions (`BODY_SENSORS` and `ACTIVITY_RECOGNITION`).
5. Force-launches both applications on the device screens.

---

### Option B: Quick Wear OS Emulator Deploy
If you are running the Wear OS Emulator target (default port `5556`), run:
```bash
./install_wear_app.sh
```

**What this script does:**
1. Compiles the smartwatch module:
   ```bash
   ./gradlew wear:assembleDebug
   ```
2. Installs the APK specifically to target `emulator-5556`.
3. Forces the app UI to open on the watch face.

---

### Option C: Manual Compilation (No Auto-Install)
To compile the debug APKs without deploying them:
```bash
./deploy.sh
```
This builds both applications. The final packages will be generated at:
* **Companion Phone App**: `app/build/outputs/apk/debug/app-debug.apk`
* **Smartwatch Wear App**: `wear/build/outputs/apk/debug/wear-debug.apk`

---

## 🔑 Step 5: Verify Permissions (Wear OS)

The foreground tracking service (`TrackerService`) requires specific device permissions to access IMU sensors and pedometer counts. The deployment script grants these automatically, but you can verify or grant them manually via ADB:

```bash
# Grant Body Sensors (Gravity, Gyro, Accel, Heart Rate)
adb -s <watch-id> shell pm grant com.mrpeel.cricketbattingtracker android.permission.BODY_SENSORS

# Grant Activity Recognition (Step Pedometer suppression gate)
adb -s <watch-id> shell pm grant com.mrpeel.cricketbattingtracker android.permission.ACTIVITY_RECOGNITION
```

---

## ❌ Troubleshooting

| Problem | Root Cause | Solution |
| :--- | :--- | :--- |
| **`device unauthorized`** | Authentication prompt on device was ignored or timed out. | Disconnect/reconnect the USB cable or run `adb kill-server && adb start-server`. Watch/phone screen will show authorization pop-up. |
| **`Device offline`** | Wi-Fi wireless debugging port changed or connection was dropped. | Disable and re-enable **Wireless Debugging** on the watch Settings, and reconnect via the newly assigned port. |
| **`No physical devices found`** | No active debug targets connected. | Run `adb devices` to check your connection status. Ensure Developer Options are active. |
| **`Unable to locate a Java Runtime`** | Missing JDK path context. | The build scripts automatically bind to Corretto JDK 17: `export JAVA_HOME="$HOME/.jdk/jdk-17"`. Ensure `setup_mac_env.sh` was run to download Corretto. |
