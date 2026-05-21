#!/bin/bash
# pull_logs.sh
# Usage: ./pull_logs.sh <WATCH_IP:PORT> [phone_serial]
# Pulls sensor CSV sessions, latest watch timeline, and full diagnostic logcat
# from both watch and phone into the logs/ directory.

export PATH="$HOME/Library/Android/sdk/platform-tools:$PATH"

WATCH="${1}"
PHONE="${2:-59011FDCR000R5}"

if [ -z "$WATCH" ]; then
    echo "Usage: ./pull_logs.sh <WATCH_IP:PORT> [phone_serial]"
    echo "  e.g. ./pull_logs.sh 192.168.1.27:39233"
    exit 1
fi

echo "========================================="
echo "🏏 Pitch Analytix Pro: Log Extraction"
echo "========================================="

# Connect watch
adb connect "$WATCH"
adb devices

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p logs

# ─── 1. Watch: pull timeline file ─────────────────────────────────────────────
echo ""
echo "📋 [1/4] Pulling watch timeline (latest_timeline.txt)..."
adb -s "$WATCH" pull \
    /sdcard/Android/data/com.mrpeel.cricketbattingtracker/files/latest_timeline.txt \
    logs/watch_timeline_${TIMESTAMP}.txt 2>&1 \
    && echo "  ✅ Timeline saved → logs/watch_timeline_${TIMESTAMP}.txt" \
    || echo "  ⚠️  No timeline file on watch (run a session first)"

# ─── 2. Watch: pull diagnostic logcat ─────────────────────────────────────────
echo ""
echo "⌚ [2/4] Pulling watch diagnostic logcat..."
adb -s "$WATCH" logcat -d \
    -s "HealthServicesManager:D" "TrackerService:D" "DataSyncManager:D" \
    > logs/watch_logcat_${TIMESTAMP}.txt 2>&1
echo "  ✅ Watch logcat saved → logs/watch_logcat_${TIMESTAMP}.txt ($(wc -l < logs/watch_logcat_${TIMESTAMP}.txt) lines)"

# ─── 3. Phone: pull Health Connect logcat ─────────────────────────────────────
echo ""
echo "📱 [3/4] Pulling phone Health Connect logcat..."
adb -s "$PHONE" logcat -d \
    -s "HealthConnectManager:D" "DataSyncListener:D" \
    > logs/phone_logcat_${TIMESTAMP}.txt 2>&1
echo "  ✅ Phone logcat saved → logs/phone_logcat_${TIMESTAMP}.txt ($(wc -l < logs/phone_logcat_${TIMESTAMP}.txt) lines)"

# ─── 4. Watch: pull raw sensor CSV sessions ───────────────────────────────────
echo ""
echo "📊 [4/4] Pulling raw sensor CSV sessions..."
DEST_DIR="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
mkdir -p "$DEST_DIR"
adb -s "$WATCH" pull \
    /storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions \
    "$DEST_DIR" 2>&1 \
    && adb -s "$WATCH" shell "rm -rf /storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions/*" \
    && echo "  ✅ Sensor sessions saved → $DEST_DIR" \
    || echo "  ⚠️  No sensor session files found"

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "✅ All logs saved to: logs/"
ls -lh logs/ | grep "$TIMESTAMP"
echo ""
echo "💡 Quick checks:"
echo "  grep 'HR:' logs/watch_timeline_${TIMESTAMP}.txt | head -5"
echo "  cat logs/phone_logcat_${TIMESTAMP}.txt"
