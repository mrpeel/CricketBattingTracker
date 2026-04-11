#!/bin/bash
# simulate_shot.sh
# Connects to the active Wear OS emulator and injects sensor telemetry imitating a swing

EMULATOR_PORT="5556"

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

echo "🏏 Simulating Cricket Shot..."

# Note: 'adb shell sensor set' or 'adb emu sensor set' works depending on the AVD image.
# We use adb emu directly to the qemu console.

# 1. Idle state
adb -s emulator-$EMULATOR_PORT emu sensor set gyroscope 0:0:0
adb -s emulator-$EMULATOR_PORT emu sensor set acceleration 0:0:9.8
sleep 0.5

# 2. Wind up (High rotational velocity)
# > 5.0 rad/s needed to trip SwingDetector
echo "💨 Winding up (Angular velocity spike)..."
adb -s emulator-$EMULATOR_PORT emu sensor set gyroscope 6.0:6.0:0.0
sleep 0.1

# 3. The Impact (High acceleration)
echo "💥 Impact! (Acceleration spike)..."
adb -s emulator-$EMULATOR_PORT emu sensor set acceleration 40.0:40.0:0.0
# 4. Follow through / Return to idle (Wait 1.5s so timestamp exceeds 1s threshold)
echo "🏌️ Follow through..."
sleep 1.5
adb -s emulator-$EMULATOR_PORT emu sensor set gyroscope 0:0:0
adb -s emulator-$EMULATOR_PORT emu sensor set acceleration 0:0:9.8

echo "✅ Simulation complete. Check logcat for 'Shot detected!'"
