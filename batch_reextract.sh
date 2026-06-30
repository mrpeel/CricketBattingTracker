#!/usr/bin/env bash
# ============================================================
# batch_reextract.sh
# Re-runs automate_pipeline.py for every live_watch_session.
#
# What this does:
#   1. Forces re-transcription via Gemini (--force-retranscribe)
#      so narrations_raw.json is refreshed with bat type data.
#   2. Re-generates ground_truth_aligned.csv using the updated
#      normalize_shot_class() which splits SWEEP from GLANCE/FLICK.
#
# Requirements:
#   - Apply the normalize_shot_class() one-line fix BEFORE running this.
#   - GOOGLE_API_KEY env var must be set (for Gemini API).
#   - Run from the CricketBattingTracker project root.
#
# Usage:
#   chmod +x batch_reextract.sh
#   ./batch_reextract.sh
#
# To dry-run (print commands without executing):
#   DRY_RUN=1 ./batch_reextract.sh
# ============================================================

set -euo pipefail

SESSIONS_DIR="/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions"
PIPELINE="$(pwd)/automate_pipeline.py"
LOG_DIR="$(pwd)/logs/batch_reextract_$(date +%Y%m%d_%H%M%S)"
DRY_RUN="${DRY_RUN:-0}"

mkdir -p "$LOG_DIR"

echo "================================================================"
echo "  Batch Re-extraction: $(date)"
echo "  Sessions dir: $SESSIONS_DIR"
echo "  Pipeline:     $PIPELINE"
echo "  Logs:         $LOG_DIR"
echo "  Dry run:      $DRY_RUN"
echo "================================================================"
echo ""

# Collect all session dirs with an audio file
SESSION_DIRS=()
while IFS= read -r -d '' dir; do
    if ls "$dir"/*.m4a &>/dev/null; then
        SESSION_DIRS+=("$dir")
    fi
done < <(find "$SESSIONS_DIR" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

TOTAL=${#SESSION_DIRS[@]}
echo "Found $TOTAL sessions with audio files."
echo ""

SUCCESS=0
FAILED=()
SKIPPED=0

for i in "${!SESSION_DIRS[@]}"; do
    session_dir="${SESSION_DIRS[$i]}"
    session_name="$(basename "$session_dir")"
    session_num=$((i + 1))

    # Find the audio file
    audio_file="$(ls "$session_dir"/*.m4a 2>/dev/null | head -1)"
    if [[ -z "$audio_file" ]]; then
        echo "[$session_num/$TOTAL] ⚠️  SKIP $session_name — no audio file"
        ((SKIPPED++)) || true
        continue
    fi

    log_file="$LOG_DIR/${session_name}.log"

    echo "[$session_num/$TOTAL] 🔄  $session_name"
    echo "             audio: $(basename "$audio_file")"
    echo "             log:   $log_file"

    if [[ "$DRY_RUN" == "1" ]]; then
        echo "             [DRY RUN] python3 $PIPELINE \\"
        echo "               --session-dir \"$session_dir\" \\"
        echo "               --audio \"$audio_file\" \\"
        echo "               --force-retranscribe"
        echo ""
        continue
    fi

    if python3 "$PIPELINE" \
        --session-dir "$session_dir" \
        --audio "$audio_file" \
        --force-retranscribe \
        >"$log_file" 2>&1; then
        echo "             ✅ Done"
        ((SUCCESS++)) || true
    else
        echo "             ❌ FAILED — see $log_file"
        FAILED+=("$session_name")
    fi

    echo ""

    # Brief pause between sessions to avoid Gemini rate limits
    if [[ $session_num -lt $TOTAL ]]; then
        echo "   ⏳ Waiting 5s before next session (Gemini rate limit buffer)..."
        sleep 5
        echo ""
    fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo "================================================================"
echo "  Batch Re-extraction Complete: $(date)"
echo "================================================================"
echo "  Total sessions:  $TOTAL"
echo "  ✅ Succeeded:    $SUCCESS"
echo "  ⚠️  Skipped:     $SKIPPED"
echo "  ❌ Failed:       ${#FAILED[@]}"

if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo ""
    echo "  Failed sessions:"
    for s in "${FAILED[@]}"; do
        echo "    - $s"
        echo "      Log: $LOG_DIR/${s}.log"
    done
    echo ""
    echo "  To retry a failed session manually:"
    echo "    python3 automate_pipeline.py \\"
    echo "      --session-dir \"$SESSIONS_DIR/<session-name>\" \\"
    echo "      --audio \"$SESSIONS_DIR/<session-name>/<audio>.m4a\" \\"
    echo "      --force-retranscribe"
fi

echo ""
echo "  All logs saved to: $LOG_DIR"
echo "================================================================"
