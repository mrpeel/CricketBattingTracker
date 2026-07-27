package com.mrpeel.cricketbattingtracker.ml

/**
 * Extracted kinematic swing features for machine learning models.
 * Exposes 18 watch-side fields and 14 Polar Sense (bottom hand) fields (32 total).
 * Polar fields have default values of 0f so watch-only inference works seamlessly.
 *
 * Linear acceleration features (s1_acc_mag, s3_acc_peak, s1_bottom_acc_mag,
 * s3_bottom_acc_peak) were added to support the accelerometer-centric force model.
 * Via F=ma, linear acc is a direct proxy for kinetic force — unlike gyroscope (rotation),
 * which measures wrist technique rather than punch power.
 */
data class SwingFeatures(
    // ── Watch / top-hand features (18 fields, always populated) ──
    val s1_gyro_y_std: Float,
    val s1_gyro_z_std: Float,
    val s1_deltaX: Float,
    val s1_deltaZ: Float,
    val s1_acc_mag: Float,          // Peak linear acceleration magnitude in backswing [m/s²]
    val s2_gyroMag: Float,
    val s2_grav_y_mean: Float,
    val s2_deltaX: Float,
    val s2_deltaZ: Float,
    val s3_rollImpactDeg: Float,
    val s3_yawImpactDeg: Float,
    val s3_deltaX: Float,
    val s3_deltaZ: Float,
    val s3_planeRatio: Float,
    val s3_gyro_y_min: Float,
    val s3_acc_peak: Float,         // Peak linear acceleration magnitude at impact [m/s²]
    // ── Polar / bottom-hand features (14 fields, default 0f when Polar absent) ──
    val bottom_hand_gyro_peak: Float = 0f,
    val bottom_hand_acc_peak: Float = 0f,
    val bottom_hand_gyro_ratio: Float = 0f,
    val bottom_hand_acc_ratio: Float = 0f,
    val bottom_hand_time_lead_ms: Float = 0f,
    val bottom_hand_sync_score: Float = 0f,
    val s1_bottom_gyro_mag: Float = 0f,
    val s1_bottom_deltaZ: Float = 0f,
    val s1_bottom_acc_mag: Float = 0f,  // Peak Polar acc magnitude in backswing [m/s²]
    val s2_bottom_acc_mean: Float = 0f,
    val s2_dynamic_ratio_slope: Float = 0f,
    val s3_bottom_pronation_deg: Float = 0f,
    val s3_bottom_gyro_y_min: Float = 0f,
    val s3_bottom_acc_peak: Float = 0f  // Peak Polar acc magnitude at impact [m/s²]
)
