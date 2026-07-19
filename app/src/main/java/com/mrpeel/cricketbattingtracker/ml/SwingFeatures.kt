package com.mrpeel.cricketbattingtracker.ml

/**
 * Extracted kinematic swing features for machine learning models.
 * Exposes 14 watch-side fields and 6 Polar Sense (bottom hand) fields.
 * Polar fields have default values of 0f so watch-only inference works seamlessly.
 */
data class SwingFeatures(
    // 14 watch features (always populated)
    val s1_gyro_y_std: Float,
    val s1_gyro_z_std: Float,
    val s1_deltaX: Float,
    val s1_deltaZ: Float,
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
    // 6 Polar bottom-hand features (default 0f when Polar absent)
    val bottom_hand_gyro_peak: Float = 0f,
    val bottom_hand_acc_peak: Float = 0f,
    val bottom_hand_gyro_ratio: Float = 0f,
    val bottom_hand_acc_ratio: Float = 0f,
    val bottom_hand_time_lead_ms: Float = 0f,
    val bottom_hand_sync_score: Float = 0f
)
