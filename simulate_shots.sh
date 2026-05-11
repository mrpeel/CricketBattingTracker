#!/bin/bash
# simulate_shots.sh
# Injects realistic sensor telemetry for the professional kinematics engine.

EMULATOR_PORT=${EMULATOR_PORT:-5554}
TARGET="emulator-$EMULATOR_PORT"

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

function inject_shot() {
    local type=$1
    local gyro=$2
    local accel=$3
    local grav_y=$4
    local roll=$5
    
    # 0. Settle gravity sensor (low pass filter needs time)
    adb -s $TARGET emu sensor set gyroscope 0:0:0
    adb -s $TARGET emu sensor set acceleration 0:$grav_y:9.8
    sleep 1.0

    # 1. Backlift
    adb -s $TARGET emu sensor set gyroscope 0.5:0:0
    adb -s $TARGET emu sensor set acceleration 0:$grav_y:9.8
    sleep 0.5
    
    # 2. Downswing start
    adb -s $TARGET emu sensor set gyroscope 2.0:0:0
    adb -s $TARGET emu sensor set acceleration 10.0:$grav_y:9.8
    sleep 0.2
    
    # 3. Peak Swing & Impact
    adb -s $TARGET emu sensor set gyroscope $gyro:$roll:0
    adb -s $TARGET emu sensor set acceleration $accel:$grav_y:9.8
    sleep 0.3
    
    # 4. Follow through
    adb -s $TARGET emu sensor set gyroscope 3.0:0:0
    adb -s $TARGET emu sensor set acceleration 0:$grav_y:9.8
    sleep 0.5
    
    # Reset
    adb -s $TARGET emu sensor set gyroscope 0:0:0
    sleep 2.0
}

# Clear logs first
adb -s $TARGET logcat -c

echo "🚀 Starting professional kinematic simulation..."

# ─── Helper: settle gravity to target position ───
# Injects a static accel reading for <seconds> so the low-pass gravity
# filter has time to converge before the actual shot motion starts.
settle_gravity() {
    local grav_y=$1
    local secs=${2:-1.5}
    adb -s $TARGET emu sensor set gyroscope 0:0:0
    adb -s $TARGET emu sensor set acceleration 0:$grav_y:9.8
    sleep $secs
}

# 1. COVER DRIVE: impactGyro > 14 → clear classification
# Vertical stance: grav_y≈9.8 → Angle≈0°
settle_gravity 9.0 2.0
inject_shot "COVER DRIVE" 18.0 45.0 9.0 0.1
sleep 3

# 2. PULL SHOT: wristRoll > 60° → roll=6 rad/s → 6*0.6*57.3=206°
# Nearly vertical: grav_y≈9.0
settle_gravity 9.0 2.0
inject_shot "PULL SHOT" 12.0 40.0 9.0 6.0
sleep 3

# 3. SWEEP: impactAngle > 75° → grav_y≈2 → acos(2/9.8)≈78°
# Must settle gravity to horizontal position first
settle_gravity 2.0 3.0
inject_shot "SWEEP" 10.0 35.0 2.0 0.1
sleep 3

# 4. ON-SIDE FLICK: wristRoll 20-60°, maxGyro < 14
# roll=1.2 rad/s → 1.2*0.6*57.3 = 41° wrist roll (avg will stay above 20° threshold)
settle_gravity 9.0 2.0
inject_shot "ON-SIDE FLICK" 11.0 30.0 9.0 1.2
sleep 3

# 5. DEFENCE: maxGyro < 8 (LOW gyro)
settle_gravity 9.0 1.5
inject_shot "DEFENCE" 5.0 15.0 9.0 0.1
sleep 3

# 6. PUSH: straight bat, minimal wrist — roll=0.05 rad/s → ~1.7° wristRoll (below 20°)
settle_gravity 9.0 2.0
inject_shot "PUSH" 10.0 20.0 9.0 0.05
sleep 3

echo "✅ Simulation complete. Results should be in logcat."
