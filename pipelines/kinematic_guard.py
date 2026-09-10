#!/usr/bin/env python3
"""
pipelines/kinematic_guard.py — Kinematic Anomaly & Detachment Guard

Detects physical sensor detachment, ballistic free-fall, uncoupled impact shockwaves,
and hardware clipping artifacts during batting sessions. Routes faulted strokes to
the Watch-Only fallback pipeline to prevent dropping legitimate deliveries.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class GuardResult:
    is_kinematically_valid: bool
    is_fallback_watch_only: bool
    anomaly_reason: str
    runtime_mount_type: str


class KinematicGuard:
    """
    Evaluates physical plausibility of Polar IMU telemetry around impact.
    
    Tolerances and Thresholds:
      1. Zero-G Free Fall: ||a_polar|| < 2.5 m/s^2 for >= 80 ms in [T_impact, T_impact + 1.2s].
      2. Ballistic Tumble: ||omega_polar|| >= 20 rad/s across >= 2 axes for >= 120 ms.
      3. Uncoupled Shockwave: Polar > 45g (441.3 m/s^2) with Watch < 18 m/s^2 within +/- 100ms.
      4. Downswing Inversion: Step jump > 160 deg.
      5. Gravity Lock Plausibility: |||a_bar|| - 9.81| > 3.0 m/s^2.
    """
    def __init__(self, configured_mount_mode="BAT_HANDLE"):
        self.configured_mount_mode = configured_mount_mode.upper()

    def evaluate_shot(
        self,
        t_impact,
        p_t_acc,
        p_acc,
        p_t_gyr,
        p_gyro,
        w_t_acc=None,
        w_acc=None,
        w_t_gyr=None,
        w_gyro_mags=None,
        ahrs_result=None,
    ) -> GuardResult:
        """
        Evaluates delivery kinematics for physical anomalies.
        
        Returns:
            GuardResult indicating validity, fallback status, and reason.
        """
        p_acc_mags = np.linalg.norm(p_acc, axis=1)
        p_gyro_mags = np.linalg.norm(p_gyro, axis=1)

        # ---------------------------------------------------------------------
        # 1. Zero-G Free Fall Check: post-impact [T_impact, T_impact + 1.2s]
        # ---------------------------------------------------------------------
        post_mask = (p_t_acc >= t_impact) & (p_t_acc <= t_impact + 1.2)
        if np.any(post_mask):
            post_mags = p_acc_mags[post_mask]
            post_t = p_t_acc[post_mask]
            # Find contiguous zero-g frames (< 2.5 m/s^2)
            low_g_mask = post_mags < 2.5
            if np.any(low_g_mask):
                # Count consecutive run
                max_consec_duration = 0.0
                curr_start = None
                for idx, is_low in enumerate(low_g_mask):
                    if is_low:
                        if curr_start is None:
                            curr_start = post_t[idx]
                        dur = post_t[idx] - curr_start
                        if dur > max_consec_duration:
                            max_consec_duration = dur
                    else:
                        curr_start = None
                        
                if max_consec_duration >= 0.080: # >= 80ms zero-g free fall
                    return self._handle_anomaly(
                        reason=f"ZERO_G_FREE_FALL ({max_consec_duration*1000:.1f}ms < 2.5 m/s^2)",
                        t_impact=t_impact,
                        w_t_gyr=w_t_gyr,
                        w_gyro_mags=w_gyro_mags
                    )

        # ---------------------------------------------------------------------
        # 2. Ballistic Multi-Axis Free-Flight Tumble
        # ---------------------------------------------------------------------
        post_gyr_mask = (p_t_gyr >= t_impact) & (p_t_gyr <= t_impact + 1.2)
        if np.any(post_gyr_mask):
            post_g = p_gyro[post_gyr_mask]
            post_gt = p_t_gyr[post_gyr_mask]
            # Check if >= 2 axes exceed 12.0 rad/s simultaneously while magnitude >= 20.0 rad/s
            multi_axis_spin = (np.sum(np.abs(post_g) >= 12.0, axis=1) >= 2) & (np.linalg.norm(post_g, axis=1) >= 20.0)
            if np.any(multi_axis_spin):
                max_spin_dur = 0.0
                curr_start = None
                for idx, is_spin in enumerate(multi_axis_spin):
                    if is_spin:
                        if curr_start is None:
                            curr_start = post_gt[idx]
                        dur = post_gt[idx] - curr_start
                        if dur > max_spin_dur:
                            max_spin_dur = dur
                    else:
                        curr_start = None
                if max_spin_dur >= 0.120: # >= 120ms multi-axis tumble
                    return self._handle_anomaly(
                        reason=f"BALLISTIC_FREE_FLIGHT_TUMBLE ({max_spin_dur*1000:.1f}ms >= 20 rad/s multi-axis)",
                        t_impact=t_impact,
                        w_t_gyr=w_t_gyr,
                        w_gyro_mags=w_gyro_mags
                    )

        # ---------------------------------------------------------------------
        # 3. Uncoupled Extreme Shockwave Check
        # Polar shockwave > 45g (441.3 m/s^2) with Watch < 18 m/s^2 within +/- 100ms
        # ---------------------------------------------------------------------
        imp_mask_p = (p_t_acc >= t_impact - 0.10) & (p_t_acc <= t_impact + 0.10)
        if np.any(imp_mask_p):
            p_max_shock = np.max(p_acc_mags[imp_mask_p])
            if p_max_shock >= 441.3: # > 45g
                if w_t_acc is not None and w_acc is not None:
                    imp_mask_w = (w_t_acc >= t_impact - 0.10) & (w_t_acc <= t_impact + 0.10)
                    if np.any(imp_mask_w):
                        w_acc_mags = np.linalg.norm(w_acc[imp_mask_w], axis=1) if len(w_acc.shape) > 1 else w_acc[imp_mask_w]
                        w_max_shock = np.max(w_acc_mags)
                        if w_max_shock < 18.0:
                            return self._handle_anomaly(
                                reason=f"UNCOUPLED_SHOCKWAVE (Polar={p_max_shock/9.80665:.1f}g vs Watch={w_max_shock:.1f} m/s^2)",
                                t_impact=t_impact,
                                w_t_gyr=w_t_gyr,
                                w_gyro_mags=w_gyro_mags
                            )

        # ---------------------------------------------------------------------
        # 4. AHRS Metric Plausibility (Step jump / Gravity Lock)
        # ---------------------------------------------------------------------
        if ahrs_result is not None:
            max_jump = ahrs_result.get("max_step_jump_deg", 0.0)
            if max_jump > 160.0:
                return self._handle_anomaly(
                    reason=f"DISCONTINUOUS_INVERSION_JUMP ({max_jump:.1f} deg)",
                    t_impact=t_impact,
                    w_t_gyr=w_t_gyr,
                    w_gyro_mags=w_gyro_mags
                )
                
            g_dev = ahrs_result.get("gravity_deviation", 0.0)
            if g_dev > 3.0:
                return self._handle_anomaly(
                    reason=f"GRAVITY_LOCK_DEVIATION ({g_dev:.2f} m/s^2)",
                    t_impact=t_impact,
                    w_t_gyr=w_t_gyr,
                    w_gyro_mags=w_gyro_mags
                )

        # All checks passed cleanly
        return GuardResult(
            is_kinematically_valid=True,
            is_fallback_watch_only=False,
            anomaly_reason="CLEAN",
            runtime_mount_type=self.configured_mount_mode
        )

    def _handle_anomaly(self, reason, t_impact, w_t_gyr, w_gyro_mags) -> GuardResult:
        """
        Determines whether the top-hand watch experienced a genuine swing.
        If yes -> trigger Watch-Only Fallback.
        If no -> drop candidate completely (dropped bat / handling accident).
        """
        is_watch_swing = False
        if w_t_gyr is not None and w_gyro_mags is not None:
            w_win = (w_t_gyr >= t_impact - 0.50) & (w_t_gyr <= t_impact + 0.25)
            if np.any(w_win):
                w_peak = np.max(w_gyro_mags[w_win])
                if w_peak >= 3.5: # Valid top-hand swing peak
                    is_watch_swing = True
                    
        return GuardResult(
            is_kinematically_valid=False,
            is_fallback_watch_only=is_watch_swing,
            anomaly_reason=reason,
            runtime_mount_type="FAULTED_ANOMALY"
        )
