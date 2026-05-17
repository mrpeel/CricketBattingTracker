#!/bin/bash

# Ensure ADB is in PATH
export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"

echo "========================================="
echo "🏏 Pitch Analytix Pro: Physical Deployment"
echo "========================================="

# 1. Check Devices
echo "Checking connected physical devices..."
DEVICES=$(adb devices | grep -v "List" | grep "device$" | awk '{print $1}')

if [ -z "$DEVICES" ]; then
    echo "❌ ERROR: No physical devices found."
    echo "Please ensure USB/Wireless debugging is enabled and devices are authorized."
    exit 1
fi

PHONE_FOUND=false
WATCH_FOUND=false
PHONE_ID=""
WATCH_ID=""

for DEV in $DEVICES; do
    # Try to determine if it's a watch or phone (simplified check)
    IS_WATCH=$(adb -s $DEV shell getprop ro.build.characteristics)
    if [[ "$IS_WATCH" == *"watch"* ]]; then
        WATCH_FOUND=true
        WATCH_ID=$DEV
        echo "✅ Wear OS Watch detected: $WATCH_ID"
    else
        PHONE_FOUND=true
        PHONE_ID=$DEV
        echo "✅ Android Phone detected: $PHONE_ID"
    fi
done

if [ "$PHONE_FOUND" = false ] || [ "$WATCH_FOUND" = false ]; then
    echo "⚠️ Warning: Both a phone and a watch are needed for a full E2E test."
    echo "Proceeding with available devices..."
fi

# 2. Build Release APKs (better performance for physics testing)
echo ""
echo "📦 Building Release APKs (this may take a minute)..."
export JAVA_HOME="/Users/neilkloot/.gradle/jdks/jetbrains_s_r_o_-21-aarch64-os_x.2/jbrsdk_jcef-21.0.10-osx-aarch64-b1163.110/Contents/Home"
./gradlew assembleDebug --no-daemon

# 3. Deploy to Watch
if [ "$WATCH_FOUND" = true ]; then
    echo ""
    echo "⌚ Deploying to Watch ($WATCH_ID)..."
    adb -s $WATCH_ID install -r wear/build/outputs/apk/debug/wear-debug.apk
    
    # Grant necessary permissions
    echo "🔑 Granting Watch Permissions..."
    adb -s $WATCH_ID shell pm grant com.mrpeel.cricketbattingtracker android.permission.BODY_SENSORS
    adb -s $WATCH_ID shell pm grant com.mrpeel.cricketbattingtracker android.permission.ACTIVITY_RECOGNITION
    
    # Launch Watch App
    adb -s $WATCH_ID shell am start -n "com.mrpeel.cricketbattingtracker/com.mrpeel.cricketbattingtracker.MainActivity" -a android.intent.action.MAIN -c android.intent.category.LAUNCHER
fi

# 4. Deploy to Phone
if [ "$PHONE_FOUND" = true ]; then
    echo ""
    echo "📱 Deploying to Phone ($PHONE_ID)..."
    adb -s $PHONE_ID install -r app/build/outputs/apk/debug/app-debug.apk
    
    # Launch Phone App
    adb -s $PHONE_ID shell am start -n "com.mrpeel.cricketbattingtracker/com.mrpeel.cricketbattingtracker.MainActivity" -a android.intent.action.MAIN -c android.intent.category.LAUNCHER
fi

echo ""
echo "✅ Deployment Complete! Check your devices."
