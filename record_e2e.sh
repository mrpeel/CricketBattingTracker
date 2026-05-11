#!/bin/bash
# record_e2e.sh
# Records the simulation process for review.

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"
export JAVA_HOME="/Users/neilkloot/.jdk/jdk-17"

PHONE_TARGET="emulator-5554"
WEAR_TARGET="emulator-5556"
PHONE_PKG="com.mrpeel.cricketbattingtracker"
WEAR_PKG="com.mrpeel.cricketbattingtracker"

echo "🎥 Starting E2E Recording Session..."

# 1. Start recording in background
echo "📹 Recording Phone..."
adb -s $PHONE_TARGET shell screenrecord /sdcard/phone_test.mp4 &
PHONE_REC_PID=$!

echo "📹 Recording Watch..."
adb -s $WEAR_TARGET shell screenrecord /sdcard/wear_test.mp4 &
WEAR_REC_PID=$!

# 2. Run the Visible E2E Simulation
./run_visible_e2e.sh

# 3. Stop recording
echo "🛑 Stopping recordings..."
sleep 2
adb -s $PHONE_TARGET shell pkill -INT screenrecord
adb -s $WEAR_TARGET shell pkill -INT screenrecord
sleep 5

# 4. Pull videos to current directory
echo "📂 Pulling videos..."
adb -s $PHONE_TARGET pull /sdcard/phone_test.mp4 ./phone_test.mp4
adb -s $WEAR_TARGET pull /sdcard/wear_test.mp4 ./wear_test.mp4

# 5. Get detailed logs for this period
echo "📜 Extracting logs..."
adb -s $WEAR_TARGET logcat -d > wear_logcat.txt
adb -s $PHONE_TARGET logcat -d > phone_logcat.txt

echo "✅ Recording complete. Files available: phone_test.mp4, wear_test.mp4, wear_logcat.txt, phone_logcat.txt"
