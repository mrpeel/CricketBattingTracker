#!/bin/bash
# boot_wear_and_phone.sh
# Automated bootstrapping for the dual-emulator testing environment.

echo "🏏 Booting Dual-Emulator Cricket Testing Pipeline..."

export JAVA_HOME="/Users/neilkloot/.jdk/jdk-17"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"

# 1. Kill any stale emulator instances to ensure clean sockets
cd "$(dirname "$0")/.."
adb devices | grep emulator | cut -f1 | while read line; do adb -s $line emu kill; done
sleep 2

# 2. Boot Phone Emulator asynchronously
echo "📱 Booting PhoneAVD..."
emulator -avd PhoneAVD -no-snapshot-load &
PHONE_PID=$!

# 3. Boot Wear Emulator asynchronously
echo "⌚ Booting WearAVD..."
emulator -avd WearAVD -no-snapshot-load &
WEAR_PID=$!

echo "⏳ Waiting for both emulators to fully boot (This may take up to 2 minutes on first run)..."

adb wait-for-device
while [ "$(adb -d shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do sleep 1; done
echo "✅ Emulators booted!"

echo "🔨 Compiling and installing latest payloads..."
./gradlew :app:installDebug :wear:installDebug

echo "🎉 Success! Both devices are primed."
echo "Now, open Android Studio -> Device Manager -> Click 'Pair Device' on WearAVD to bridge the Bluetooth APIs."
echo "Then launch the apps and run ./simulate_shots.sh!"
