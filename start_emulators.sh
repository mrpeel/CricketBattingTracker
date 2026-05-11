#!/bin/bash
# start_emulators.sh
# Starts the Phone and Wear OS emulators with visible UI.

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"
export JAVA_HOME="/Users/neilkloot/.jdk/jdk-17"

# 1. Kill existing emulator processes to force a visible restart
echo "🧹 Cleaning up existing emulator processes..."
pkill -9 qemu-system || true
pkill -9 emulator || true
sleep 2

# 2. Start Emulators
start_emulator() {
    local avd=$1
    local port=$2
    echo "🚀 Starting $avd on port $port..."
    # Ensure -no-snapshot-load is used to avoid getting stuck in a bad background state
    # Ensure UI is NOT disabled (don't use -no-window)
    nohup emulator -avd "$avd" -port "$port" -no-snapshot-load > /dev/null 2>&1 &
}

start_emulator "PhoneAVD" 5554
start_emulator "WearAVD" 5556

echo "⏳ Waiting for emulators to boot (this may take 1-2 minutes)..."

wait_for_boot() {
    local port=$1
    local target="emulator-$port"
    echo "🔍 Checking $target..."
    
    # Wait for the device to appear in adb
    local count=0
    while ! adb devices | grep -q "$target"; do
        sleep 2
        count=$((count+1))
        if [ $count -gt 30 ]; then
            echo "❌ Timeout waiting for $target to appear in ADB"
            return 1
        fi
    done
    
    adb -s "$target" wait-for-device
    
    # Wait for the system UI to be ready
    local boot_completed=""
    while [ "$boot_completed" != "1" ]; do
        sleep 5
        boot_completed=$(adb -s "$target" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
        echo -n "."
    done
    echo "✅ $target is ready!"
}

wait_for_boot 5554
wait_for_boot 5556

# Configure DataLayer Bridge for emulators
echo "🔗 Bridging Wear Data Layer..."
adb -s emulator-5554 forward tcp:5601 tcp:5601
adb -s emulator-5556 forward tcp:5601 tcp:5601

echo "✨ All systems go! Emulators should now be visible on your screen."
