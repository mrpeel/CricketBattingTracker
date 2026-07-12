#!/bin/bash
set -x

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export JAVA_HOME="$HOME/.jdk/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"

# Clear any dead emulators
cd "$(dirname "$0")/.."
killall qemu-system-aarch64 || true
adb kill-server || true
sleep 2

# Delete the buggy generic emulator and recreate it with the correct Wear OS profile
echo "yes" | avdmanager delete avd -n WearAVD || true
echo "no" | avdmanager create avd -n WearAVD -k "system-images;android-33;android-wear;arm64-v8a" -d "wearos_small_round" --force

# Boot Wear Emulator in the background natively so the window persists
echo "Starting Wear Emulator UI..."
nohup emulator -avd WearAVD -no-audio -no-snapshot-load -delay-adb -port 5556 > /dev/null 2>&1 &

echo "Waiting for emulator to boot up (this will take 1-3 minutes)..."
# Wait specifically for the 5556 instance
until adb devices | grep -q "emulator-5556"; do
    sleep 2
done

adb -s emulator-5556 wait-for-device
while [ "$(adb -s emulator-5556 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]; do
    sleep 5
done

# Wait for the system UI/Launcher to be ready
while [ "$(adb -s emulator-5556 shell getprop dev.bootcomplete 2>/dev/null | tr -d '\r')" != "1" ]; do
    sleep 2
done

echo "Emulator fully booted! Installing app..."
adb -s emulator-5556 install -r wear/build/outputs/apk/debug/wear-debug.apk

echo "Launching application..."
adb -s emulator-5556 shell monkey -p com.mrpeel.cricketbattingtracker -c android.intent.category.LAUNCHER 1

# Give the app time to render and start its tracking foreground service
echo "Waiting for TrackerService to initialize..."
sleep 15

echo "Triggering the hardware kinematic simulation sequence!"
EMULATOR_PORT=5556 test/simulate_shots.sh
