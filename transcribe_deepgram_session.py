#!/usr/bin/env python3
"""
transcribe_deepgram_session.py

Transcribes a batting session using Deepgram Nova-3 API (with cricket domain keyword boosting)
or re-runs lexicon formatting on cached Deepgram JSON.

Usage:
  # Transcribe session via Deepgram API:
  python3 transcribe_deepgram_session.py --session session_2026-07-25_15-16-32

  # Skip Deepgram API call and re-run lexicon logic on cached response:
  python3 transcribe_deepgram_session.py --session session_2026-07-25_15-16-32 --skip-deepgram
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

# Default base directory for sessions
DEFAULT_SESSIONS_DIR = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"

# Domain keyterms for Deepgram Nova-3 acoustic boosting
DEEPGRAM_KEYTERMS = [
    # Bat Switches
    "Gray Nicolls", "Gray Nicolls Giant", "Giant",
    "Eye In", "Iron Bat", "Game Bat", "Game Day Bat",

    # Shot Categories
    "Facing up", "Slog", "Power drive", "Cover drive", 
    "Straight drive", "Off drive", "On drive", "Flick shot", 
    "Glance", "Leg glance",
    "Pull shot", "Hook shot", "Cut shot", "Square cut", 
    "Sweep shot", "Reverse sweep", "Guide", "Late guide", 
    "Back foot punch", "Back foot defense", "Forward defense", "No shot",

    # Qualities & Session Markers
    "excellent", "good", "okay", "poor", "edge", "miss",
    "Round one", "Round two", "Round three", "End of round", "End of session"
]

def load_env_api_key():
    """Load DEEPGRAM_API_KEY from environment or .env file."""
    api_key = os.environ.get("DEEPGRAM_API_KEY")
    if api_key:
        return api_key

    # Search for .env file in script directory or workspace root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, ".env"),
        os.path.join(script_dir, "..", ".env"),
        "/Users/neilkloot/Code/CricketBattingTracker/.env"
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("DEEPGRAM_API_KEY="):
                        return line.split("=", 1)[1].strip()
    return None

def resolve_session_dir(session_arg):
    """Resolve session directory path from argument."""
    if os.path.isabs(session_arg) and os.path.isdir(session_arg):
        return session_arg
    
    # Try relative to DEFAULT_SESSIONS_DIR
    target = os.path.join(DEFAULT_SESSIONS_DIR, session_arg)
    if os.path.isdir(target):
        return target
        
    # Try relative to current working directory
    if os.path.isdir(session_arg):
        return os.path.abspath(session_arg)
        
    raise FileNotFoundError(f"❌ Session directory not found: '{session_arg}' (checked path & {DEFAULT_SESSIONS_DIR})")

def find_audio_file(session_dir):
    """Find audio file in session directory."""
    files = os.listdir(session_dir)
    audio_candidates = [f for f in files if f.endswith((".m4a", ".mp3", ".wav", ".aac", ".ogg"))]
    if not audio_candidates:
        raise FileNotFoundError(f"❌ No audio file (.m4a/.mp3) found in {session_dir}")
        
    # Prefer narration_*.m4a if present
    narrations = [f for f in audio_candidates if f.startswith("narration_")]
    if narrations:
        return os.path.join(session_dir, sorted(narrations)[-1])
        
    return os.path.join(session_dir, sorted(audio_candidates)[0])

def call_deepgram_api(audio_path, api_key, model="nova-3"):
    """Send audio file to Deepgram REST API and return JSON response."""
    print(f"📤 Uploading {os.path.basename(audio_path)} to Deepgram ({model})...")
    
    with open(audio_path, "rb") as f:
        audio_data = f.read()

    params = [
        ("model", model),
        ("smart_format", "true"),
        ("punctuate", "true"),
    ]
    for kt in DEEPGRAM_KEYTERMS:
        params.append(("keyterm", kt))

    query_string = urllib.parse.urlencode(params)
    url = f"https://api.deepgram.com/v1/listen?{query_string}"

    ext = os.path.splitext(audio_path)[1].lower()
    content_type = "audio/mp4" if ext in [".m4a", ".mp4"] else "audio/mp3" if ext == ".mp3" else "audio/*"

    req = urllib.request.Request(
        url,
        data=audio_data,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": content_type
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("✅ Deepgram transcription succeeded.")
            return data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"❌ Deepgram API error (HTTP {e.code}): {err_body}")

def group_words_into_phrases(words, max_silence_gap=0.80):
    """Group words into phrases using silence gap threshold."""
    if not words:
        return []
        
    phrases = []
    current = [words[0]]
    
    for i in range(1, len(words)):
        gap = words[i]['start'] - words[i-1]['end']
        if gap > max_silence_gap:
            text = " ".join(w['word'] for w in current)
            phrases.append({
                'start': round(current[0]['start'], 2),
                'end': round(current[-1]['end'], 2),
                'text': text
            })
            current = [words[i]]
        else:
            current.append(words[i])
            
    if current:
        text = " ".join(w['word'] for w in current)
        phrases.append({
            'start': round(current[0]['start'], 2),
            'end': round(current[-1]['end'], 2),
            'text': text
        })
        
    return phrases

def load_ground_truth_lexicon():
    """Load ground_truth_lexicon.json from docs folder."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lexicon_path = os.path.join(script_dir, "docs", "ground_truth_lexicon.json")
    if os.path.exists(lexicon_path):
        try:
            with open(lexicon_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning loading lexicon: {e}")
    return {}

def process_phrases_with_lexicon(phrases):
    """
    Format phrases into structured shot events using lexicon, phrase stitching, and bat change logic.
    Returns: (formatted_shots, raw_transcript_lines, bat_switches, admin_headers, unrecognized_phrases)
    """
    lexicon = load_ground_truth_lexicon()
    
    formatted_shots = []
    raw_transcript_lines = []
    bat_switches = []
    admin_headers = []
    unrecognized_phrases = []
    
    current_bat = None
    shot_counter = 1

    idx = 0
    while idx < len(phrases):
        p = phrases[idx]
        raw_text = p['text'].strip()
        text_lower = raw_text.lower()
        t_sec = p['start']

        # Lookahead stitching: If current phrase is unmatched and next phrase occurs within 1.5s, test combined text
        if idx + 1 < len(phrases):
            next_p = phrases[idx + 1]
            gap = next_p['start'] - p['end']
            if gap <= 1.5:
                comb_text = raw_text + " " + next_p['text'].strip()
                comb_lower = comb_text.lower()
                matched_comb = False
                if lexicon:
                    for canonical_term, variants in lexicon.items():
                        if any(v.lower() in comb_lower for v in variants):
                            matched_comb = True
                            break
                if matched_comb or any(b in comb_lower for b in ["iron bat", "gray nicolls", "game bat", "getting back"]):
                    raw_text = comb_text
                    text_lower = comb_lower
                    idx += 1  # Stitched next phrase!

        mins = int(t_sec // 60)
        secs = t_sec % 60
        time_label = f"{mins}.{secs:05.2f}"
        
        raw_transcript_lines.append(f"{time_label}: {raw_text}")

        # 1. Bat Switch Recognition
        detected_bat = None
        if any(w in text_lower for w in ["iron bat", "iron bus", "eye in", "thin bat", "light bat", "i invest", "i end that"]):
            detected_bat = "Eye In"
        elif any(w in text_lower for w in ["giant", "nicolls", "nichs", "heavy bat", "turn out"]):
            detected_bat = "Gray Nicolls Giant"
        elif any(w in text_lower for w in ["game bat", "game back", "game day bat", "normal bat", "standard bat", "getting back"]):
            detected_bat = "Game bat"

        if detected_bat:
            current_bat = detected_bat
            bat_switches.append({'timestamp': t_sec, 'text': raw_text, 'bat': current_bat})

        # 2. Check Round Headers / Administrative Utterances
        is_header = any(h in text_lower for h in ["round ", "end of round", "end of session", "tap tap tap"])
        if is_header and not any(s in text_lower for s in ["drive", "cut", "flick", "pull", "shot", "defense", "defence", "facing"]):
            admin_headers.append({'timestamp': t_sec, 'text': raw_text})
            idx += 1
            continue

        # 3. Shot Type Mapping via Lexicon
        shot_type = None
        if lexicon:
            for canonical_term, variants in lexicon.items():
                if any(v.lower() in text_lower for v in variants):
                    shot_type = canonical_term
                    break

        if shot_type is None:
            # Fallbacks for STT phonetic mishearings
            if "power drive" in text_lower or any(w in text_lower for w in ["tower drive", "now drive", "we'll drive"]):
                shot_type = "Power drive"
            elif "cover drive" in text_lower or "cover" in text_lower:
                shot_type = "Cover drive"
            elif "straight drive" in text_lower or "straight" in text_lower:
                shot_type = "Straight drive"
            elif "off drive" in text_lower:
                shot_type = "Off drive"
            elif "on drive" in text_lower:
                shot_type = "On drive"
            elif any(d in text_lower for d in ["defense", "defence", "defensive", "block", "forward edge"]):
                shot_type = "Forward defense"
            elif "the shot" in text_lower and any(q in text_lower for q in ["good", "okay", "ok", "poor", "bad", "miss", "edge", "edged", "excellent", "decent", "perfect", "smoked", "terrible", "pour"]):
                shot_type = "Flick shot"
            else:
                if not detected_bat:
                    unrecognized_phrases.append({'timestamp': t_sec, 'text': raw_text})
                idx += 1
                continue

        # 4. Determine Shot Number
        is_swing = shot_type not in ["Facing up", "No shot", "Leave", "Evade"]
        if is_swing:
            shot_num = shot_counter
            shot_counter += 1
        else:
            shot_num = None

        # 5. Quality Rating Extraction
        quality = "good"
        if any(q in text_lower for q in ["excellent", "perfect", "nailed", "smoked"]):
            quality = "excellent"
        elif any(q in text_lower for q in ["poor", "bad", "edge", "edged", "terrible", "pour"]):
            quality = "poor"
        elif any(q in text_lower for q in ["miss", "missed", "beaten", "smith"]):
            quality = "miss"
        elif any(q in text_lower for q in ["okay", "ok", "decent", "average"]):
            quality = "okay"

        formatted_shots.append({
            "timestamp_seconds": t_sec,
            "shot_number": shot_num,
            "shot_type": shot_type,
            "quality": quality,
            "bat": current_bat,
            "narrated_text": raw_text
        })
        idx += 1

    return formatted_shots, raw_transcript_lines, bat_switches, admin_headers, unrecognized_phrases

def main():
    parser = argparse.ArgumentParser(description="Transcribe batting session via Deepgram or re-run lexicon on cached response.")
    parser.add_argument("--session", "-s", required=True, help="Session folder name or absolute directory path")
    parser.add_argument("--skip-deepgram", "--use-cache", action="store_true", help="Skip Deepgram API call and use cached deepgram_response.json")
    parser.add_argument("--model", default="nova-3", help="Deepgram model (default: nova-3)")

    args = parser.parse_args()

    session_dir = resolve_session_dir(args.session)
    print(f"📂 Processing session directory: {session_dir}")

    cache_json_path = os.path.join(session_dir, "deepgram_response.json")

    # Step 1: Deepgram API Call or Cache Load
    if args.skip_deepgram:
        if not os.path.exists(cache_json_path):
            print(f"❌ Error: --skip-deepgram specified, but cached response file not found at: {cache_json_path}")
            sys.exit(1)
        print(f"📖 Loading cached Deepgram response from {cache_json_path}...")
        with open(cache_json_path, "r", encoding="utf-8") as f:
            deepgram_data = json.load(f)
    else:
        api_key = load_env_api_key()
        if not api_key:
            print("❌ ERROR: DEEPGRAM_API_KEY is not set in environment or .env file.")
            sys.exit(1)

        audio_path = find_audio_file(session_dir)
        print(f"🎙️ Audio file identified: {audio_path}")

        deepgram_data = call_deepgram_api(audio_path, api_key, model=args.model)

        # Save response cache
        with open(cache_json_path, "w", encoding="utf-8") as f:
            json.dump(deepgram_data, f, indent=2)
        print(f"💾 Saved Deepgram response cache to: {cache_json_path}")

    # Step 2: Extract words and group into phrases
    try:
        words = deepgram_data['results']['channels'][0]['alternatives'][0]['words']
    except (KeyError, IndexError) as e:
        print(f"❌ Error parsing words from Deepgram response: {e}")
        sys.exit(1)

    print(f"📊 Extracted {len(words)} words from Deepgram output.")
    phrases = group_words_into_phrases(words, max_silence_gap=0.80)
    print(f"🧩 Grouped into {len(phrases)} phrases.")

    # Step 3: Run Lexicon Matching & Format Output
    formatted_shots, raw_transcript_lines, bat_switches, admin_headers, unrecognized_phrases = process_phrases_with_lexicon(phrases)


    # Save narrations_raw.json
    narrations_path = os.path.join(session_dir, "narrations_raw.json")
    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(formatted_shots, f, indent=2)
    print(f"📝 Saved parsed narrations to: {narrations_path}")

    # Save raw_transcript.txt
    raw_transcript_path = os.path.join(session_dir, "raw_transcript.txt")
    with open(raw_transcript_path, "w", encoding="utf-8") as f:
        f.write("\n".join(raw_transcript_lines))
    print(f"📄 Saved raw transcript text to: {raw_transcript_path}")

    # Step 4: Display Summary, Bat Switches, Consecutive Facing Up Audit, & Excluded Phrases Report
    shots_only = [s for s in formatted_shots if s.get('shot_number') is not None]
    facing_only = [s for s in formatted_shots if s['shot_type'] == 'Facing up']

    # Audit consecutive "Facing up" locks with no intervening shot
    consecutive_facing = []
    for i in range(len(formatted_shots) - 1):
        curr = formatted_shots[i]
        nxt = formatted_shots[i+1]
        if curr['shot_type'] == 'Facing up' and nxt['shot_type'] == 'Facing up':
            t1 = curr['timestamp_seconds']
            t2 = nxt['timestamp_seconds']
            # Find any raw phrases in this interval
            interval_phrases = [p for p in phrases if t1 < p['start'] < t2]
            consecutive_facing.append({
                't1': t1,
                't2': t2,
                'gap': t2 - t1,
                'raw1': curr['narrated_text'],
                'raw2': nxt['narrated_text'],
                'intervening_phrases': interval_phrases
            })

    print("\n" + "=" * 80)
    print("📊 SESSION TRANSCRIPTION SUMMARY")
    print("=" * 80)
    print(f"  Total Extracted Phrases: {len(phrases)}")
    print(f"  Attacking Shots Logged:  {len(shots_only)}")
    print(f"  Facing Up Locks:         {len(facing_only)}")
    print(f"  Bat Switches Detected:   {len(bat_switches)}")
    print(f"  Consecutive Facing Ups:  {len(consecutive_facing)} ⚠️")
    print(f"  Unrecognized Utterances: {len(unrecognized_phrases)}")
    print("=" * 80)

    print("\n🏏 BAT SWITCH ANNOUNCEMENTS DETECTED:")
    print("-" * 80)
    if not bat_switches:
        print("  (None — no bat switch announcements detected)")
    else:
        for bc in bat_switches:
            t_sec = bc['timestamp']
            mins = int(t_sec // 60)
            secs = t_sec % 60
            print(f"  [{mins:2d}:{secs:05.2f}s ({t_sec:6.2f}s)]  \"{bc['text']}\"  --> Active Bat: {bc['bat']}")
    print("-" * 80)

    print("\n⚠️ CONSECUTIVE 'FACING UP' LOCKS REPORT (No shot detected in between):")
    print("-" * 80)
    if not consecutive_facing:
        print("  (None — all Facing Up locks are cleanly separated by shots!)")
    else:
        for i, cf in enumerate(consecutive_facing, 1):
            m1, s1 = int(cf['t1'] // 60), cf['t1'] % 60
            m2, s2 = int(cf['t2'] // 60), cf['t2'] % 60
            print(f"  {i:2d}. [{m1:2d}:{s1:05.2f}s → {m2:2d}:{s2:05.2f}s] (gap: {cf['gap']:5.2f}s)")
            print(f"      Facing Up 1: \"{cf['raw1']}\"")
            print(f"      Facing Up 2: \"{cf['raw2']}\"")
            if cf['intervening_phrases']:
                print("      Intervening Raw Deepgram Phrases:")
                for ip in cf['intervening_phrases']:
                    im, isec = int(ip['start'] // 60), ip['start'] % 60
                    print(f"        👉 [{im:2d}:{isec:05.2f}s] \"{ip['text']}\"")
            else:
                print("      (No speech uttered in Deepgram output between these locks)")
            print()
    print("-" * 80)

    print("\n❓ UNRECOGNIZED / UNMATCHED UTTERANCES REPORT:")
    print("-" * 80)
    if not unrecognized_phrases:
        print("  (None — all phrases were matched to valid lexicon terms or administrative headers!)")
    else:
        for i, ex in enumerate(unrecognized_phrases, 1):
            t_sec = ex['timestamp']
            mins = int(t_sec // 60)
            secs = t_sec % 60
            print(f"  {i:2d}. [{mins:2d}:{secs:05.2f}s ({t_sec:6.2f}s)]  \"{ex['text']}\"")
    print("-" * 80 + "\n")

if __name__ == "__main__":
    main()
