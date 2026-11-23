import os
import sys
import unittest
import numpy as np

PIPELINES_DIR = os.path.dirname(os.path.abspath(__file__))
if PIPELINES_DIR not in sys.path:
    sys.path.insert(0, PIPELINES_DIR)

from telemetry_engine import (
    extract_high_energy_bypass_candidates,
    BYPASS_MIN_GYRO_RAD_S,
    BYPASS_MIN_ACC_SHOCKWAVE_MS2,
    BYPASS_EXCLUSION_FRAMES,
)


class TestStage1BypassParity(unittest.TestCase):
    def test_recovers_plateau_peak_with_offset_shockwave(self):
        # 423Hz forward-filled 4-sample flat plateau peak at frames 1000..1003 (midpoint 1001)
        # with shockwave acc peak 40 frames (~95ms) after gyro peak
        n = 3000
        gyr = np.zeros(n, dtype=np.float32)
        acc = np.full(n, 9.8, dtype=np.float32)
        gyr[900:1000] = np.linspace(0.5, 14.0, 100, dtype=np.float32)
        gyr[1000:1004] = 15.0
        gyr[1004:1060] = np.linspace(14.0, 1.0, 56, dtype=np.float32)
        acc[1040] = 72.5

        res = extract_high_energy_bypass_candidates(gyr, acc, existing_anchor_frames=[])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["anchor_f"], 1001)
        self.assertAlmostEqual(res[0]["peak_gyr"], 15.0, places=3)
        self.assertAlmostEqual(res[0]["peak_acc_150"], 72.5, places=3)

    def test_rejects_practice_swing_without_shockwave(self):
        n = 3000
        gyr = np.zeros(n, dtype=np.float32)
        acc = np.full(n, 25.0, dtype=np.float32)  # below 50 m/s^2
        gyr[900:1000] = np.linspace(0.5, 16.0, 100, dtype=np.float32)
        gyr[1000:1004] = 18.0
        gyr[1004:1060] = np.linspace(16.0, 1.0, 56, dtype=np.float32)

        res = extract_high_energy_bypass_candidates(gyr, acc, existing_anchor_frames=[])
        self.assertEqual(res, [])

    def test_respects_stage1_exclusion_zone(self):
        n = 3000
        gyr = np.zeros(n, dtype=np.float32)
        acc = np.full(n, 9.8, dtype=np.float32)
        gyr[900:1000] = np.linspace(0.5, 13.0, 100, dtype=np.float32)
        gyr[1000:1004] = 14.0
        gyr[1004:1060] = np.linspace(13.0, 1.0, 56, dtype=np.float32)
        acc[1001] = 85.0

        # Existing Stage 1 candidate 300 frames away (< 635) must suppress bypass
        res = extract_high_energy_bypass_candidates(gyr, acc, existing_anchor_frames=[1300])
        self.assertEqual(res, [])

        # Existing Stage 1 candidate 800 frames away (>= 635) must NOT suppress bypass
        res_far = extract_high_energy_bypass_candidates(gyr, acc, existing_anchor_frames=[1801])
        self.assertEqual(len(res_far), 1)
        self.assertEqual(res_far[0]["anchor_f"], 1001)

    def test_greedy_descending_height_suppression(self):
        # Two peaks 400 frames apart (< 635): taller second peak at 1400 must win over 1000
        n = 3000
        gyr = np.zeros(n, dtype=np.float32)
        acc = np.full(n, 9.8, dtype=np.float32)
        gyr[900:1000] = np.linspace(1.0, 11.0, 100, dtype=np.float32)
        gyr[1000] = 12.0
        gyr[1001:1050] = np.linspace(11.0, 1.0, 49, dtype=np.float32)
        gyr[1300:1400] = np.linspace(1.0, 17.0, 100, dtype=np.float32)
        gyr[1400] = 19.0
        gyr[1401:1450] = np.linspace(17.0, 1.0, 49, dtype=np.float32)
        acc[1000] = 70.0
        acc[1400] = 90.0

        res = extract_high_energy_bypass_candidates(gyr, acc, existing_anchor_frames=[])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["anchor_f"], 1400)
        self.assertAlmostEqual(res[0]["peak_gyr"], 19.0, places=3)

    def test_constants_match_kotlin_parity(self):
        self.assertEqual(BYPASS_MIN_GYRO_RAD_S, 10.0)
        self.assertEqual(BYPASS_MIN_ACC_SHOCKWAVE_MS2, 50.0)
        self.assertEqual(BYPASS_EXCLUSION_FRAMES, 635)


if __name__ == "__main__":
    unittest.main()
