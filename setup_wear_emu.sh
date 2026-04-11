#!/bin/bash
set -ex

# Use the Android tools installed from the previous script
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export JAVA_HOME="$HOME/.jdk/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"

echo "Downloading Wear OS 4 system image..."
yes | sdkmanager --licenses > /dev/null
sdkmanager "system-images;android-33;android-wear;arm64-v8a" | grep -v "="

echo "Creating Wear OS Emulator AVD..."
if ! avdmanager list avd | grep -q "WearAVD"; then
    echo "no" | avdmanager create avd -n WearAVD -k "system-images;android-33;android-wear;arm64-v8a" -d "wear_os_small_round"
fi

echo "Starting Wear OS Emulator..."
emulator -avd WearAVD -no-window -no-audio -no-snapshot-load -delay-adb &
WEAR_PID=$!

echo "Waiting for Wear OS emulator to boot (1-3 minutes)..."
adb wait-for-device
while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
    sleep 5
done
echo "Wear OS emulator booted successfully!"
