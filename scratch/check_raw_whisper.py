import whisper
import os

audio_path = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-05-31_10-06-52/narration_20260531_100649.m4a"
model = whisper.load_model("base")
result = model.transcribe(audio_path, verbose=False)

print("=== Raw Whisper Segments ===")
for s in result.get("segments", []):
    print(f"[{s['start']:.2f}s - {s['end']:.2f}s]: '{s['text']}'")
