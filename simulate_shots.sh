#!/bin/bash
# simulate_shots.sh
# Connects to the active Wear OS emulator and injects realistic sensor telemetry
# traversing the new 6-state ring-buffered kinetics model.

EMULATOR_PORT="5554"

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

function inject_shot {
    local name=$1
    local peak_gyro=$2
    local peak_accel=$3
    
    echo "🏏 Sequence: $name"
    
    # 1. IDLE_RECOVERY & STANCE_LOCKED
    # Wait > 0.5s with zero/low gyro so the trailing StdDev falls < 0.9 rad/s
    adb -s emulator-$EMULATOR_PORT emu sensor set gyroscope 0.0:0.0:0.0
    adb -s emulator-$EMULATOR_PORT emu sensor set acceleration 0.0:0.0:9.8
    sleep 1.5
    
    # 2. SWING_SEARCH & MEASURING_ARC
    # Break standard dev with a big swing spike > 5.0 rad/s
    adb -s emulator-$EMULATOR_PORT emu sensor set gyroscope ${peak_gyro}:0.0:0.0
    sleep 0.2
    
    # 3. CONTACT_WAIT (The -0.45s to +0.75s narrow window relative to peak gyro)
    # Injecting the shock while inside the window!
    adb -s emulator-$EMULATOR_PORT emu sensor set acceleration ${peak_accel}:0.0:0.0
    sleep 0.1
    
    # 4. Follow through and drop acceleration
    adb -s emulator-$EMULATOR_PORT emu sensor set acceleration 0.0:0.0:9.8
    sleep 0.8
    
    # Wait out the 1.0s ARC timeout + 0.75s POST window to allow EVALUATION phase
    # Then transition back to IDLE_RECOVERY
    sleep 1.0
}

echo "Initiating Wear OS Kinetics Verification Sequence..."

# Bat Speed = Gyro * 0.8 * 3.6
# Ratio = Accel / BatSpeed

# 10.0 rad/s = 28.8 km/h. Accel 20.0. Ratio = 0.69 (< 2.5 Excellent)
inject_shot "Excellent Strike" 10.0 20.0

# 10.0 rad/s = 28.8 km/h. Accel 80.0. Ratio = 2.77 (< 3.0 Good)
inject_shot "Good Strike" 10.0 80.0

# 6.0 rad/s = 17.28 km/h. Accel 60.0. Ratio = 3.47 (> 3.0 Poor)
inject_shot "Poor Strike (Toe/Handle)" 6.0 60.0

# 8.0 rad/s = 23.0 km/h. Accel 9.8 (Just gravity). Ratio = N/A (Hit = false)
inject_shot "Play and Miss" 8.0 9.8

# Cut Shot: 6.5 rad/s = 18.7 km/h. Accel 65.0. Ratio = 3.47 (> 3.0 Poor)
inject_shot "Cut Shot (Miss-timed)" 6.5 65.0

# Cut Shot: 7.2 rad/s = 20.7 km/h. Accel 45.0. Ratio = 2.17 (< 2.5 Excellent)
inject_shot "Cut Shot (Clean Hit)" 7.2 45.0

echo "✅ Multi-Shot Session Simulation complete!"
