#!/bin/bash
# load_and_simulate.sh
# Deploys the professional build and runs simulation on an ALREADY RUNNING emulator.

# Configuration
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

PORT=${1:-5556}
TARGET="emulator-$PORT"
PKG="com.mrpeel.cricketbattingtracker"

echo "🎯 Targeting $TARGET..."

# 1. Verify connection
if ! adb devices | grep -q "$TARGET"; then
    echo "❌ Error: $TARGET not found. Please ensure the emulator is running on port $PORT."
    exit 1
fi

# 2. Install the professional build
echo "📦 Installing Professional Wear OS build..."
adb -s $TARGET install -r builds/CricketWear-Professional.apk

# 3. Grant Permissions
echo "🔐 Granting sensor and health permissions..."
adb -s $TARGET shell pm grant $PKG android.permission.BODY_SENSORS || true
adb -s $TARGET shell pm grant $PKG android.permission.ACTIVITY_RECOGNITION || true

# 4. Launch the application UI
echo "🚀 Launching UI..."
adb -s $TARGET shell am start -n $PKG/$PKG.MainActivity || true

# 5. START THE TRACKER SERVICE EXPLICITLY
# This is required for the SwingDetector to actually listen to sensors
echo "🏃 Starting TrackerService..."
adb -s $TARGET shell am start-foreground-service -a START_TRACKING $PKG/.services.TrackerService || \
adb -s $TARGET shell am startservice $PKG/.services.TrackerService

# 6. Verify process is running
sleep 3
PID=$(adb -s $TARGET shell pidof $PKG)
if [ -z "$PID" ]; then
    echo "❌ Error: Application failed to start. Checking logs..."
    adb -s $TARGET logcat -d "*:E" | tail -n 20
    exit 1
fi
echo "✅ App running with PID: $PID"

# 7. Wait for initialization
echo "⏳ Waiting 10 seconds for TrackerService to warm up..."
sleep 10

# 8. Run simulation
echo "🏏 Triggering kinematic simulation..."
EMULATOR_PORT=$PORT ./simulate_shots.sh

echo "✅ Done! Monitor logs using: adb -s $TARGET logcat | grep SwingDetector"
