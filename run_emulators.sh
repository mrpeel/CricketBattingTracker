#!/bin/bash
set -x

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export JAVA_HOME="$HOME/.jdk/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"

# Wait for gradle build to finish if it's currently running
cd /Users/neilkloot/Code/CricketBattingTracker
./gradlew assembleDebug

# Clear any dead emulators
killall qemu-system-aarch64 || true
adb kill-server || true

# Boot Phone Emulator
echo "Starting Phone Emulator..."
emulator -avd PhoneAVD -no-audio -no-snapshot-load -delay-adb -port 5554 &

# Recreate Wear Emulator without the invalid device flag
if ! avdmanager list avd | grep -q "WearAVD"; then
    echo "no" | avdmanager create avd -n WearAVD -k "system-images;android-33;android-wear;arm64-v8a"
fi

# Boot Wear Emulator
echo "Starting Wear Emulator..."
emulator -avd WearAVD -no-audio -no-snapshot-load -delay-adb -port 5556 &

# Loop until both emulators have boot_completed
echo "Waiting for both emulators to boot up (this will take 2-4 minutes)..."
WAIT_PHONE=true
WAIT_WEAR=true
while $WAIT_PHONE || $WAIT_WEAR; do
    if [ "$(adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; then
        WAIT_PHONE=false
    fi
    if [ "$(adb -s emulator-5556 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; then
        WAIT_WEAR=false
    fi
    sleep 5
done

echo "Emulators fully booted! Installing apps..."
adb -s emulator-5554 install -r app/build/outputs/apk/debug/app-debug.apk
adb -s emulator-5556 install -r wear/build/outputs/apk/debug/wear-debug.apk

echo "Launching applications..."
adb -s emulator-5554 shell monkey -p com.mrpeel.cricketbattingtracker -c android.intent.category.LAUNCHER 1
adb -s emulator-5556 shell monkey -p com.mrpeel.cricketbattingtracker -c android.intent.category.LAUNCHER 1

echo "Applications have been started on both emulated devices!"
