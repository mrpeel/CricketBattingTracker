#!/bin/bash
# pull_logs.sh
# Usage: ./pull_logs.sh [emu | 192.168.1.100]
# Extracts all CSV sensor logs from the smartwatch and drops them into Batting Sensor Stats

TARGET=$1

if [ -z "$TARGET" ]; then
    echo "Error: Need Watch IP or 'emu'"
    echo "Usage: ./pull_logs.sh 192.168.1.100"
    echo "Usage: ./pull_logs.sh emu"
    exit 1
fi

if [ "$1" == "emu" ]; then
    echo "Connecting to emulator..."
    ADB_CMD="adb -s emulator-5556"
else
    echo "Using device $TARGET..."
    # Assumes you have already run adb connect IP:PORT
    ADB_CMD="adb -s $TARGET"
fi

echo "Pulling Session Logs..."
DEST_DIR="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
mkdir -p "$DEST_DIR"

$ADB_CMD pull /storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions "$DEST_DIR"
$ADB_CMD shell "rm -rf /storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/sessions/*"

echo "Success! Logs saved to:"
echo "$DEST_DIR"
echo "You can now run 'python3 analyze_sessions.py' across these sessions."
