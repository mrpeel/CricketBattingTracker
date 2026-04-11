#!/bin/bash
set -ex

echo "Starting macOS environment setup..."

# 1. Setup Java 17
mkdir -p ~/.jdk
cd ~/.jdk
if [ ! -d "jdk-17" ]; then
    echo "Downloading Amazon Corretto JDK 17 for macOS ARM64..."
    curl -sL "https://corretto.aws/downloads/latest/amazon-corretto-17-aarch64-macos-jdk.tar.gz" -o corretto.tar.gz
    tar -xzf corretto.tar.gz
    # Correct extraction target
    mv amazon-corretto-17.jdk/Contents/Home jdk-17
    rm corretto.tar.gz
    rm -rf amazon-corretto-17.jdk
fi
export JAVA_HOME="$HOME/.jdk/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"

# 2. Setup Android SDK
export ANDROID_HOME="$HOME/Library/Android/sdk"
mkdir -p "$ANDROID_HOME/cmdline-tools"
cd "$ANDROID_HOME/cmdline-tools"
if [ ! -d "latest" ]; then
    echo "Downloading Android Command Line Tools for macOS..."
    curl -sL "https://dl.google.com/android/repository/commandlinetools-mac-11076708_latest.zip" -o cmdline-tools.zip
    unzip -q cmdline-tools.zip
    mv cmdline-tools latest
    rm cmdline-tools.zip
fi

export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

# 3. Accept Licenses & Install SDK components
echo "Accepting Android SDK licenses..."
yes | sdkmanager --licenses > /dev/null

echo "Installing Android SDK components..."
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" "system-images;android-34;google_apis;arm64-v8a" "emulator" | grep -v "="

# 4. Building the Application
echo "Building the application using Gradle..."
cd /Users/neilkloot/Code/CricketBattingTracker
./gradlew assembleDebug

# 5. Create AVD
echo "Creating Phone Emulator AVD..."
if ! avdmanager list avd | grep -q "PhoneAVD"; then
    echo "no" | avdmanager create avd -n PhoneAVD -k "system-images;android-34;google_apis;arm64-v8a" -d "pixel_7"
fi

# 6. Emulate
echo "Starting Emulator..."
# Use hardware acceleration natively (important for ARM Mac)
emulator -avd PhoneAVD -no-window -no-audio -no-snapshot-load -delay-adb &
EMULATOR_PID=$!

echo "Waiting for emulator to boot (this will take 1-3 minutes)..."
adb wait-for-device
while [ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != "1" ]; do
    sleep 5
done
echo "Emulator booted!"

# 7. Deploy
echo "Deploying Phone app to emulator..."
adb install -r app/build/outputs/apk/debug/app-debug.apk

echo "Done! The emulator is running (PID: $EMULATOR_PID) and the app is installed."
