#!/bin/bash
# install_wear_app.sh
# Quickly builds the Wear OS project, injects the new installation into an actively running Emulator, and forces the UI open.

set -e # Exit immediately if a command fails
echo "🛠 Building the Wear OS application..."

# Required environment hooks for macOS
export JAVA_HOME="$HOME/.jdk/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

# Build the latest APK
./gradlew wear:assembleDebug

echo "📦 Installing APK onto the running emulator (port 5556)..."
adb -s emulator-5556 install -r wear/build/outputs/apk/debug/wear-debug.apk

echo "🚀 Forcing the application to open on the Watch Face..."
adb -s emulator-5556 shell am start -n com.mrpeel.cricketbattingtracker/.MainActivity

echo "✅ App successfully deployed and running!"
