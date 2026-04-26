#!/bin/bash
# test_sync_bridge.sh
# Physically bridges Wear OS output directly into the Phone Database via ADB.

export ANDROID_HOME="$HOME/Library/Android/sdk"
export PATH="$ANDROID_HOME/platform-tools:$PATH"

echo "⌚ 1/3 Extracting raw Match Timeline from Watch Emulator..."
rm -f ./latest_timeline.txt
adb -s emulator-5554 pull /storage/emulated/0/Android/data/com.mrpeel.cricketbattingtracker/files/latest_timeline.txt ./latest_timeline.txt

if [ ! -f ./latest_timeline.txt ]; then
    echo "❌ Error: Could not find timeline. Did you run the watch session and tap Stop?"
    exit 1
fi

echo "📱 2/3 Injecting payload into Phone Emulator via hidden ADB tunnel..."
adb -s emulator-5556 push ./latest_timeline.txt /data/local/tmp/wear_timeline.txt

echo "🧠 3/3 Triggering DataSyncListenerService in Phone App..."
adb -s emulator-5556 shell am start -n com.mrpeel.cricketbattingtracker/.MainActivity
sleep 1
adb -s emulator-5556 shell am startservice -n com.mrpeel.cricketbattingtracker/.services.DataSyncListenerService -a com.mrpeel.cricketbattingtracker.INJECT_TIMELINE

echo "✅ Bridge execution complete! Look at your Phone Emulator now!"
