#!/bin/bash
set -ex

echo "Starting installation phase..."
mkdir -p /home/mrpeel/Android/Sdk/cmdline-tools
cd /home/mrpeel/Android/Sdk/cmdline-tools

if [ ! -d "latest" ]; then
    echo "Downloading Android Cmdline tools..."
    wget -q -O /tmp/cmdline-tools.zip "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    unzip -q /tmp/cmdline-tools.zip
    mv cmdline-tools latest
    rm /tmp/cmdline-tools.zip
else
    echo "Android Cmdline tools already downloaded."
fi

echo "Accepting licenses..."
yes | /home/mrpeel/Android/Sdk/cmdline-tools/latest/bin/sdkmanager --licenses > /dev/null

echo "Installing SDK components..."
/home/mrpeel/Android/Sdk/cmdline-tools/latest/bin/sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"

echo "Building applications..."
cd /home/mrpeel/Code/CricketBattingTracker
./gradlew assembleDebug

echo "Deploying applications to Chromebook Android Subsystem..."
/usr/bin/adb -s emulator-5554 install app/build/outputs/apk/debug/app-debug.apk || echo "Phone app failed to install, check ADB device"
/usr/bin/adb -s emulator-5554 install wear/build/outputs/apk/debug/wear-debug.apk || echo "Wear app failed to install, check ADB device"

echo "Done"
