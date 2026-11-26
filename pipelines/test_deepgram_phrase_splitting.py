import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import transcribe_deepgram_session as tdg


def _mk_words(tokens_with_times):
    return [{"word": w, "start": t, "end": t + 0.30} for w, t in tokens_with_times]


class TestDeepgramPhraseSplitting(unittest.TestCase):
    def test_splits_shot_facing_up_shot(self):
        words = _mk_words([
            ("cut", 233.98), ("shot", 234.30), ("edge", 234.65),
            ("facing", 235.10), ("up", 235.45),
            ("cut", 237.12), ("shot", 237.45), ("good", 237.80),
        ])
        phrases = tdg.group_words_into_phrases(words, max_silence_gap=2.0)
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        real_shots = [s for s in shots if s["shot_type"] != "Facing up"]
        self.assertEqual(len(real_shots), 2)
        self.assertEqual(real_shots[0]["shot_type"], "Cut shot")
        self.assertAlmostEqual(real_shots[0]["timestamp_seconds"], 233.98, places=2)
        self.assertEqual(real_shots[1]["shot_type"], "Cut shot")
        self.assertAlmostEqual(real_shots[1]["timestamp_seconds"], 237.12, places=2)

    def test_splits_stuttered_facing_up_with_noise_prefix(self):
        words = _mk_words([
            ("good", 197.28), ("facing", 197.60), ("facing", 199.54),
            ("up", 199.90), ("up", 200.25),
            ("off", 201.06), ("drive", 201.40), ("good", 201.75),
        ])
        phrases = tdg.group_words_into_phrases(words, max_silence_gap=2.0)
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        real_shots = [s for s in shots if s["shot_type"] != "Facing up"]
        self.assertEqual(len(real_shots), 1)
        self.assertEqual(real_shots[0]["shot_type"], "Off drive")
        self.assertEqual(real_shots[0]["narrated_text"], "off drive good")
        self.assertAlmostEqual(real_shots[0]["timestamp_seconds"], 201.06, places=2)

    def test_splits_unrecognized_prefix_before_facing_up_shot(self):
        words = _mk_words([
            ("squad", 1226.90), ("good", 1227.25),
            ("facing", 1227.70), ("up", 1228.05),
            ("back", 1229.30), ("foot", 1229.65), ("punch", 1230.00), ("good", 1230.35),
        ])
        phrases = tdg.group_words_into_phrases(words, max_silence_gap=2.0)
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        real_shots = [s for s in shots if s["shot_type"] != "Facing up"]
        self.assertEqual(len(real_shots), 1)
        self.assertEqual(real_shots[0]["shot_type"], "Back foot punch")
        self.assertAlmostEqual(real_shots[0]["timestamp_seconds"], 1229.30, places=2)

    def test_splits_facing_up_partial_prefix_for_lookahead_stitching(self):
        # Mimics today's session: 'facing up foot' followed 1.2s later by 'shot miss'
        words = _mk_words([
            ("facing", 191.91), ("up", 192.39), ("foot", 193.34),
            ("shot", 195.03), ("miss", 195.34),
        ])
        phrases = tdg.group_words_into_phrases(words, max_silence_gap=0.80)
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        real_shots = [s for s in shots if s["shot_type"] != "Facing up"]
        self.assertEqual(len(real_shots), 1)
        self.assertEqual(real_shots[0]["shot_type"], "Flick shot")
        self.assertEqual(real_shots[0]["quality"], "miss")
        self.assertAlmostEqual(real_shots[0]["timestamp_seconds"], 193.34, places=2)

    def test_splits_back_to_back_shots_without_facing_up(self):
        words = _mk_words([
            ("cover", 855.64), ("drive", 856.00), ("okay", 856.35),
            ("back", 857.10), ("foot", 857.45), ("defense", 857.80), ("good", 858.15),
        ])
        phrases = tdg.group_words_into_phrases(words, max_silence_gap=1.0)
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        real_shots = [s for s in shots if s["shot_type"] != "Facing up"]
        self.assertEqual(len(real_shots), 2)
        self.assertEqual(real_shots[0]["shot_type"], "Cover drive")
        self.assertEqual(real_shots[1]["shot_type"], "Back foot defense")
        self.assertAlmostEqual(real_shots[1]["timestamp_seconds"], 857.10, places=2)

    def test_lexicon_excludes_alright_and_maps_slip_shot_to_sweep(self):
        words = _mk_words([
            ("alright", 10.0), ("let's", 10.4), ("get", 10.8), ("going", 11.2),
            ("slip", 20.0), ("shot", 20.4), ("okay", 20.8),
        ])
        phrases = tdg.group_words_into_phrases(words, max_silence_gap=0.80)
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        self.assertEqual(len(shots), 1)
        self.assertEqual(shots[0]["shot_type"], "Sweep shot")

    def test_normalise_shot_type_back_foot_punch_is_cut_punch(self):
        sys.path.insert(0, os.path.join(ROOT_DIR, "pipelines"))
        from telemetry_engine import normalise_shot_type as te_norm
        from build_unified_dataset import normalise_shot_type as bud_norm

        for fn in (te_norm, bud_norm):
            self.assertEqual(fn("Back foot punch"), "CUT/PUNCH")
            self.assertEqual(fn("Back foot defense"), "DRIVE/DEFENCE")
            self.assertEqual(fn("Back foot drive"), "DRIVE/DEFENCE")
            self.assertEqual(fn("Square upper cut"), "DEFLECTION/GUIDE")

    def test_footshot_and_oh_shut_lexicon_and_no_facing_up_swallow(self):
        # Mimics Nov 26 'footshot is' + 'facing up' + 'footshot four' and Nov 24 'oh shut okay'
        phrases = [
            {"start": 528.58, "end": 529.60, "text": "footshot is"},
            {"start": 531.06, "end": 531.80, "text": "facing up"},
            {"start": 536.18, "end": 537.10, "text": "footshot four"},
            {"start": 540.00, "end": 540.50, "text": "what is this"},
            {"start": 541.50, "end": 542.20, "text": "facing up"},
            {"start": 545.00, "end": 545.90, "text": "oh shut okay"},
            {"start": 550.00, "end": 550.30, "text": "facing"},
            {"start": 551.10, "end": 551.40, "text": "up"},
        ]
        shots, _, _, _, _ = tdg.process_phrases_with_lexicon(phrases)
        self.assertEqual(
            [(s["shot_type"], s["quality"], round(s["timestamp_seconds"], 2)) for s in shots],
            [
                ("Flick shot", "good", 528.58),
                ("Facing up", "good", 531.06),
                ("Flick shot", "poor", 536.18),
                ("Facing up", "good", 541.50),
                ("Pull shot", "okay", 545.00),
                ("Facing up", "good", 550.00),
            ],
        )

    def test_dp_alignment_respects_facing_up_barrier_and_small_negative_lag(self):
        import automate_pipeline as ap

        # Mimics Nov 24 Shot #37: Facing up at 564.3s, pull shot spoken at 567.85s,
        # real 27.3 rad/s impact at 568.57s (lag = -0.72s) vs tiny 4.1 rad/s noise at 563.53s (before Facing up)
        narrations = [
            {"timestamp_seconds": 564.30, "shot_type": "Facing up"},
            {"timestamp_seconds": 567.85, "shot_type": "Pull shot"},
        ]
        all_candidates = [
            [{"time": 563.80, "mag": 1.0, "is_fallback": True}],
            [
                {"time": 563.53, "mag": 4.1, "is_fallback": False},
                {"time": 568.57, "mag": 27.3, "is_fallback": False},
                {"time": 567.05, "mag": 1.0, "is_fallback": True},
            ],
        ]
        chosen = ap.align_narrations_dp(narrations, all_candidates, offset=0.0, drift_rate=0.0)
        self.assertEqual(chosen, [0, 1])

        # Mimics Nov 26 Shot #53: delayed narration ('glance pour' at 831.30s) after Facing up (826.50s),
        # real 16.2 rad/s hit at 827.96s (lag=+3.34s) should beat 9.19 rad/s bat twirl at 830.57s (lag=+0.73s)
        s_real = ap.score_alignment_candidate({"time": 827.96, "mag": 16.2, "is_fallback": False}, 831.30)
        s_twirl = ap.score_alignment_candidate({"time": 830.57, "mag": 9.19, "is_fallback": False}, 831.30)
        self.assertGreater(s_real, s_twirl)

    def test_telemetry_engine_mount_mode_defaults_to_none_without_polar(self):
        import pandas as pd
        sys.path.insert(0, os.path.join(ROOT_DIR, "pipelines"))
        from telemetry_engine import resolve_session_mount_mode

        df_none = pd.DataFrame({"has_polar": [0, 0], "polar_mount_mode": [0, 0]})
        df_bat = pd.DataFrame({"has_polar": [1, 1], "polar_mount_mode": [2, 2]})
        self.assertEqual(resolve_session_mount_mode("nonexistent_session_id", df_none, sessions_dir="/tmp"), "NONE")
        self.assertEqual(resolve_session_mount_mode("nonexistent_session_id", df_bat, sessions_dir="/tmp"), "BAT_HANDLE")


if __name__ == "__main__":
    unittest.main()
