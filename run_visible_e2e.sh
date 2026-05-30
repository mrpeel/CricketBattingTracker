#!/bin/bash
# run_visible_e2e.sh
# Complete Visible End-to-End simulation script.

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
export JAVA_HOME="/Users/neilkloot/.gradle/jdks/jetbrains_s_r_o_-21-aarch64-os_x.2/jbrsdk_jcef-21.0.10-osx-aarch64-b1163.110/Contents/Home"

PHONE_TARGET="emulator-5554"
WEAR_TARGET="emulator-5556"
PHONE_PKG="com.mrpeel.cricketbattingtracker"
WEAR_PKG="com.mrpeel.cricketbattingtracker"

echo "🎯 Starting Visible E2E Simulation..."

# 1. Build Both Apps
echo "🏗️  Building Phone and Wear apps..."
if ! ./gradlew assembleDebug; then
    echo "❌ Build Failed! Please check Java/Gradle settings."
    exit 1
fi

# 2. Install Both Apps
echo "📦 Installing apps to emulators..."
adb -s $PHONE_TARGET install -r app/build/outputs/apk/debug/app-debug.apk
adb -s $WEAR_TARGET install -r wear/build/outputs/apk/debug/wear-debug.apk

# 3. Grant Permissions
echo "🔐 Granting permissions..."
# Wear permissions
adb -s $WEAR_TARGET shell pm grant $WEAR_PKG android.permission.BODY_SENSORS || true
adb -s $WEAR_TARGET shell pm grant $WEAR_PKG android.permission.ACTIVITY_RECOGNITION || true
# Phone permissions (now in manifest)
adb -s $PHONE_TARGET shell pm grant $PHONE_PKG android.permission.BODY_SENSORS || true
adb -s $PHONE_TARGET shell pm grant $PHONE_PKG android.permission.ACTIVITY_RECOGNITION || true

# 4. Launch Phone App
echo "📱 Launching Phone App..."
adb -s $PHONE_TARGET shell input keyevent KEYCODE_WAKEUP
adb -s $PHONE_TARGET shell wm dismiss-keyguard
adb -s $PHONE_TARGET shell am start -n $PHONE_PKG/$PHONE_PKG.MainActivity
sleep 2

# 5. Launch Wear App
echo "⌚ Launching Wear App..."
adb -s $WEAR_TARGET shell input keyevent KEYCODE_WAKEUP
adb -s $WEAR_TARGET shell am start -n $WEAR_PKG/$WEAR_PKG.MainActivity
sleep 2

# 6. Start Tracking Service on Wear
echo "🏃 Activating TrackerService..."
adb -s $WEAR_TARGET shell am start-foreground-service -a START_TRACKING --ez ENABLE_RAW_LOGGING true $WEAR_PKG/.services.TrackerService
sleep 5

# 7. Run Professional Shot Simulation
echo "🏏 Running Shot Simulation (Observe the Wear OS UI!)..."
EMULATOR_PORT=5556 ./simulate_shots.sh

# 8. Complete Session and Sync to Phone
echo "🔄 Ending session and syncing to Phone..."
# Sending STOP_TRACKING intent triggers the syncTimelineToPhone in onDestroy
adb -s $WEAR_TARGET shell am startservice -a STOP_TRACKING $WEAR_PKG/.services.TrackerService
sleep 5

# 9. Verify on Phone
echo "🛠️  Ensuring data is pushed to Phone via ADB bridge fallback..."
adb -s $WEAR_TARGET shell "cat /sdcard/Android/data/$WEAR_PKG/files/latest_timeline.txt" > latest_timeline.txt || true
if [ -s latest_timeline.txt ]; then
    adb -s $PHONE_TARGET push latest_timeline.txt /data/local/tmp/wear_timeline.txt
    adb -s $PHONE_TARGET shell am startservice -a com.mrpeel.cricketbattingtracker.INJECT_TIMELINE $PHONE_PKG/.services.DataSyncListenerService
    sleep 2
fi

echo "📱 Bringing Phone App to front for verification..."
adb -s $PHONE_TARGET shell am start -n $PHONE_PKG/$PHONE_PKG.MainActivity

echo "✅ E2E Simulation Complete!"
echo "The session data should now be visible on the Phone app's dashboard."
