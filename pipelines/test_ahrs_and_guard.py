#!/usr/bin/env python3
"""
pipelines/test_ahrs_and_guard.py — Unit Tests for AHRS & Kinematic Guard
"""

import unittest
import numpy as np
from orientation_ahrs import (
    quat_mult, quat_conjugate, quat_rotate, quat_from_two_vectors, quat_exp_map,
    StateGatedOrientationEstimator
)
from kinematic_guard import KinematicGuard, GuardResult


class TestOrientationAhrs(unittest.TestCase):
    def test_quaternion_identity(self):
        q_id = np.array([0.0, 0.0, 0.0, 1.0])
        v = np.array([1.0, 2.0, 3.0])
        v_rot = quat_rotate(q_id, v)
        np.testing.assert_allclose(v_rot, v, atol=1e-6)

    def test_quaternion_90deg_z_rotation(self):
        # 90 deg around z-axis: [0, 0, sin(45 deg), cos(45 deg)]
        half_angle = np.radians(45.0)
        q = np.array([0.0, 0.0, np.sin(half_angle), np.cos(half_angle)])
        v = np.array([1.0, 0.0, 0.0])
        v_rot = quat_rotate(q, v)
        # Expected: [0, 1, 0]
        np.testing.assert_allclose(v_rot, [0.0, 1.0, 0.0], atol=1e-6)

    def test_two_vector_alignment(self):
        u = np.array([0.0, 0.0, 9.81])
        v = np.array([0.0, 0.0, 1.0])
        q = quat_from_two_vectors(u, v)
        u_rot = quat_rotate(q, u / np.linalg.norm(u))
        np.testing.assert_allclose(u_rot, v, atol=1e-6)

    def test_exp_map_small_angle(self):
        omega = np.array([0.1, 0.0, 0.0])
        dt = 0.01
        dq = quat_exp_map(omega, dt)
        self.assertAlmostEqual(np.linalg.norm(dq), 1.0, places=6)


class TestKinematicGuard(unittest.TestCase):
    def setUp(self):
        self.guard = KinematicGuard(configured_mount_mode="BAT_HANDLE")

    def test_clean_shot(self):
        t_impact = 10.0
        p_t_acc = np.linspace(9.0, 11.0, 846)
        # Normal 1g gravity with 25g impact shockwave
        p_acc = np.zeros((846, 3), dtype=np.float32)
        p_acc[:, 2] = 9.81
        p_acc[423, 2] = 245.0 # 25g
        
        p_t_gyr = np.linspace(9.0, 11.0, 846)
        p_gyro = np.zeros((846, 3), dtype=np.float32)
        p_gyro[423, 0] = 15.0 # 15 rad/s downswing
        
        w_t_acc = np.linspace(9.0, 11.0, 100)
        w_acc = np.zeros((100, 3), dtype=np.float32)
        w_acc[:, 2] = 9.81
        w_acc[50, 2] = 40.0 # 4g watch shockwave
        
        w_t_gyr = np.linspace(9.0, 11.0, 100)
        w_gyro_mags = np.zeros(100, dtype=np.float32)
        w_gyro_mags[50] = 8.0

        res = self.guard.evaluate_shot(
            t_impact=t_impact,
            p_t_acc=p_t_acc,
            p_acc=p_acc,
            p_t_gyr=p_t_gyr,
            p_gyro=p_gyro,
            w_t_acc=w_t_acc,
            w_acc=w_acc,
            w_t_gyr=w_t_gyr,
            w_gyro_mags=w_gyro_mags
        )
        self.assertTrue(res.is_kinematically_valid)
        self.assertFalse(res.is_fallback_watch_only)
        self.assertEqual(res.runtime_mount_type, "BAT_HANDLE")

    def test_zero_g_detachment(self):
        t_impact = 10.0
        p_t_acc = np.linspace(9.0, 11.0, 846)
        p_acc = np.zeros((846, 3), dtype=np.float32)
        p_acc[:, 2] = 9.81
        # Sensor detaches: drops to 0.5 m/s^2 for 150 ms
        detach_mask = (p_t_acc >= 10.1) & (p_t_acc <= 10.25)
        p_acc[detach_mask, 2] = 0.5
        
        p_t_gyr = np.linspace(9.0, 11.0, 846)
        p_gyro = np.zeros((846, 3), dtype=np.float32)
        
        w_t_gyr = np.linspace(9.0, 11.0, 100)
        w_gyro_mags = np.zeros(100, dtype=np.float32)
        w_gyro_mags[50] = 8.0 # Top-hand watch completed a real stroke

        res = self.guard.evaluate_shot(
            t_impact=t_impact,
            p_t_acc=p_t_acc,
            p_acc=p_acc,
            p_t_gyr=p_t_gyr,
            p_gyro=p_gyro,
            w_t_gyr=w_t_gyr,
            w_gyro_mags=w_gyro_mags
        )
        self.assertFalse(res.is_kinematically_valid)
        self.assertTrue(res.is_fallback_watch_only)
        self.assertEqual(res.runtime_mount_type, "FAULTED_ANOMALY")
        self.assertIn("ZERO_G_FREE_FALL", res.anomaly_reason)

    def test_packet_gap_does_not_trigger_tumble(self):
        t_impact = 10.0
        p_t_acc = np.linspace(9.0, 11.0, 846)
        p_acc = np.zeros((846, 3), dtype=np.float32)
        p_acc[:, 2] = 9.81
        
        # Sporadic spin samples separated by 100ms BLE packet drops
        # Gaps of 100ms between 4 spin samples (total span 300ms, but zero continuous spin)
        t_base = np.linspace(9.0, 10.0, 423)
        t_sporadic = np.array([10.05, 10.15, 10.25, 10.35]) # 100ms gaps
        t_after = np.linspace(10.4, 11.0, 250)
        p_t_gyr = np.concatenate([t_base, t_sporadic, t_after])
        
        p_gyro = np.zeros((len(p_t_gyr), 3), dtype=np.float32)
        # Set high spin only on the sporadic samples
        for idx in range(len(t_base), len(t_base) + len(t_sporadic)):
            p_gyro[idx] = [25.0, 25.0, 5.0] # >= 12 rad/s on 2 axes, mag >= 20
            
        w_t_gyr = np.linspace(9.0, 11.0, 100)
        w_gyro_mags = np.zeros(100, dtype=np.float32)

        res = self.guard.evaluate_shot(
            t_impact=t_impact,
            p_t_acc=p_t_acc,
            p_acc=p_acc,
            p_t_gyr=p_t_gyr,
            p_gyro=p_gyro,
            w_t_gyr=w_t_gyr,
            w_gyro_mags=w_gyro_mags
        )
        # Because samples were interrupted by >15ms gaps, continuous tumble duration is 0ms
        self.assertTrue(res.is_kinematically_valid)
        self.assertEqual(res.anomaly_reason, "CLEAN")

    def test_true_ballistic_tumble(self):
        t_impact = 10.0
        p_t_acc = np.linspace(9.0, 11.0, 846)
        p_acc = np.zeros((846, 3), dtype=np.float32)
        p_acc[:, 2] = 9.81
        
        # 150 consecutive uninterrupted samples at 423 Hz (~354ms) spinning violently
        p_t_gyr = np.linspace(9.0, 11.0, 846)
        p_gyro = np.zeros((846, 3), dtype=np.float32)
        tumble_mask = (p_t_gyr >= 10.05) & (p_t_gyr <= 10.25) # 200ms contiguous
        p_gyro[tumble_mask] = [25.0, 25.0, 10.0]
        
        w_t_gyr = np.linspace(9.0, 11.0, 100)
        w_gyro_mags = np.zeros(100, dtype=np.float32)
        w_gyro_mags[50] = 8.0 # Watch recorded a swing peak of 8.0 rad/s at impact

        res = self.guard.evaluate_shot(
            t_impact=t_impact,
            p_t_acc=p_t_acc,
            p_acc=p_acc,
            p_t_gyr=p_t_gyr,
            p_gyro=p_gyro,
            w_t_gyr=w_t_gyr,
            w_gyro_mags=w_gyro_mags
        )
        self.assertFalse(res.is_kinematically_valid)
        self.assertTrue(res.is_fallback_watch_only)
        self.assertEqual(res.runtime_mount_type, "FAULTED_ANOMALY")
        self.assertIn("BALLISTIC_FREE_FLIGHT_TUMBLE", res.anomaly_reason)


class TestImpactQualityModel(unittest.TestCase):
    def test_polar_patch_and_onnx_scoring(self):
        from impact_quality_model import (
            extract_polar_patch_and_scalars,
            compute_log_mel_and_audio_scalars,
            score_session_shots_onnx,
            SAMPLE_RATE,
        )

        # Synthetic 423 Hz Polar swing: strong pre-impact rotation + 28% post-impact dip + sharp impact
        pt = np.linspace(9.5, 10.5, 423, dtype=np.float64)
        p_acc = np.zeros((423, 3), dtype=np.float32)
        p_acc[:, 2] = 9.81
        p_acc[211, 2] = 320.0
        p_gyro = np.zeros((423, 3), dtype=np.float32)
        pre = (pt >= 9.88) & (pt < 10.00)
        post = (pt > 10.00) & (pt <= 10.06)
        p_gyro[pre, 0] = 20.0
        p_gyro[post, 0] = 14.0

        pol_mat, scalars = extract_polar_patch_and_scalars(pt, p_acc, pt, p_gyro, t_c=10.0)
        self.assertEqual(pol_mat.shape, (8, 68))
        self.assertTrue(np.isfinite(pol_mat).all())
        self.assertIn("wide_dip_pct", scalars)
        self.assertGreater(scalars["wide_dip_pct"], 0.15)

        results = score_session_shots_onnx(
            [{"t_c": 10.0, "pol_mat": pol_mat, "scalars": scalars}],
            audio_path=None,
        )
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["impact_quality_source"], "POLAR")
        self.assertTrue(0.0 <= r["impact_quality_score"] <= 100.0)
        self.assertTrue(0.0 <= r["impact_edge_risk"] <= 1.0)
        self.assertGreater(r["polar_contact_dip_pct"], 15.0)

        # Audio scalar / log-mel extraction check
        bg = np.random.default_rng(42).normal(0, 0.002, int(0.20 * SAMPLE_RATE)).astype(np.float32)
        seg = np.random.default_rng(7).normal(0, 0.002, int(0.25 * SAMPLE_RATE)).astype(np.float32)
        c_idx = int(0.10 * SAMPLE_RATE)
        t_burst = np.arange(800, dtype=np.float32) / SAMPLE_RATE
        seg[c_idx:c_idx + 800] += 0.25 * np.exp(-t_burst * 60.0) * np.sin(2.0 * np.pi * 650.0 * t_burst)
        mel, aud_scalars = compute_log_mel_and_audio_scalars(seg, bg, scalars["g_pre_pk"])
        self.assertEqual(mel.shape, (24, 31))
        self.assertTrue(np.isfinite(mel).all())
        self.assertGreater(aud_scalars["aud_snr_db"], 5.0)


if __name__ == "__main__":
    unittest.main()
