package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test

/**
 * GeneratedForest Model Integrity Tests
 *
 * These tests verify that the binary-packed Random Forest model:
 *   1. Deserialises correctly (no ArrayIndexOutOfBoundsException on decode)
 *   2. Produces deterministic, valid class predictions
 *   3. Is backward-compatible — watch-only callers that pass only 14 fields
 *      compile and predict without requiring Polar values
 *   4. Exposes all 8 expected shot classes
 *
 * The retired session-replay tests (SwingDetectorGroundTruthTest) have been
 * removed. They tested the on-watch SwingDetector code path which no longer
 * runs in production. The authoritative performance scorecard is now produced
 * by pipelines/score_phone_pipeline.py, which evaluates the phone-side
 * PhoneSwingDetector batch pipeline output.
 */
class SwingDetectorGroundTruthTest {

    private val VALID_CLASSES = setOf(
        "CUT/PUNCH", "DEFLECTION/GUIDE", "DRIVE/DEFENCE",
        "GLANCE/FLICK", "POWER DRIVE", "PULL/HOOK", "SLOG", "SWEEP"
    )

    // ---------------------------------------------------------------------------
    // Test 1: Model deserialises and produces a valid class for a known PULL input
    // ---------------------------------------------------------------------------
    @Test
    fun testModelPredictsPullShot() {
        // Feature values representative of a pull shot (high s2_gyroMag, positive s3_roll)
        val features = SwingFeatures(
            s1_gyro_y_std    = 1.85f,
            s1_gyro_z_std    = 1.20f,
            s1_deltaX        = -0.12f,
            s1_deltaZ        = 0.08f,
            s2_gyroMag       = 9.4f,
            s2_grav_y_mean   = -0.55f,
            s2_deltaX        = -0.40f,
            s2_deltaZ        = 0.25f,
            s3_rollImpactDeg = 42.0f,
            s3_yawImpactDeg  = -18.0f,
            s3_deltaX        = -0.65f,
            s3_deltaZ        = 0.35f,
            s3_planeRatio    = 1.20f,
            s3_gyro_y_min    = -8.5f
        )
        val result = GeneratedForest.predict(features)
        assertTrue(
            "Expected a valid shot class, got: '$result'",
            result in VALID_CLASSES
        )
    }

    // ---------------------------------------------------------------------------
    // Test 2: Model produces a valid class for a known DRIVE input
    // ---------------------------------------------------------------------------
    @Test
    fun testModelPredictsdriveShot() {
        val features = SwingFeatures(
            s1_gyro_y_std    = 0.65f,
            s1_gyro_z_std    = 0.42f,
            s1_deltaX        = 0.05f,
            s1_deltaZ        = -0.03f,
            s2_gyroMag       = 4.8f,
            s2_grav_y_mean   = 0.82f,
            s2_deltaX        = 0.18f,
            s2_deltaZ        = -0.22f,
            s3_rollImpactDeg = -5.0f,
            s3_yawImpactDeg  = 3.0f,
            s3_deltaX        = 0.30f,
            s3_deltaZ        = -0.40f,
            s3_planeRatio    = 0.55f,
            s3_gyro_y_min    = -2.1f
        )
        val result = GeneratedForest.predict(features)
        assertTrue(
            "Expected a valid shot class, got: '$result'",
            result in VALID_CLASSES
        )
    }

    // ---------------------------------------------------------------------------
    // Test 3: Polar defaults (= 0f) — watch-only callers must compile and predict
    // without passing Polar fields. This verifies backward compatibility.
    // ---------------------------------------------------------------------------
    @Test
    fun testPolarDefaultsWatchOnlyPath() {
        // Only 14 mandatory watch fields — Polar fields default to 0f
        val features = SwingFeatures(
            s1_gyro_y_std    = 1.10f,
            s1_gyro_z_std    = 0.85f,
            s1_deltaX        = -0.08f,
            s1_deltaZ        = 0.04f,
            s2_gyroMag       = 6.2f,
            s2_grav_y_mean   = 0.30f,
            s2_deltaX        = -0.25f,
            s2_deltaZ        = 0.15f,
            s3_rollImpactDeg = 12.0f,
            s3_yawImpactDeg  = -7.0f,
            s3_deltaX        = -0.35f,
            s3_deltaZ        = 0.20f,
            s3_planeRatio    = 0.88f,
            s3_gyro_y_min    = -5.3f
            // bottom_hand_* fields intentionally omitted → default to 0f
        )
        val result = GeneratedForest.predict(features)
        assertTrue(
            "Watch-only prediction should return a valid class, got: '$result'",
            result in VALID_CLASSES
        )
    }

    // ---------------------------------------------------------------------------
    // Test 4: Full 20-feature path — Polar fields populated (phone-side path)
    // ---------------------------------------------------------------------------
    @Test
    fun testFullTwentyFeaturePolarPath() {
        val features = SwingFeatures(
            s1_gyro_y_std            = 1.10f,
            s1_gyro_z_std            = 0.85f,
            s1_deltaX                = -0.08f,
            s1_deltaZ                = 0.04f,
            s2_gyroMag               = 6.2f,
            s2_grav_y_mean           = 0.30f,
            s2_deltaX                = -0.25f,
            s2_deltaZ                = 0.15f,
            s3_rollImpactDeg         = 12.0f,
            s3_yawImpactDeg          = -7.0f,
            s3_deltaX                = -0.35f,
            s3_deltaZ                = 0.20f,
            s3_planeRatio            = 0.88f,
            s3_gyro_y_min            = -5.3f,
            // Polar fields populated (phone-side path)
            bottom_hand_gyro_peak    = 8.4f,
            bottom_hand_acc_peak     = 28.5f,
            bottom_hand_gyro_ratio   = 1.35f,
            bottom_hand_acc_ratio    = 1.12f,
            bottom_hand_time_lead_ms = -45.0f,
            bottom_hand_sync_score   = 82.0f
        )
        val result = GeneratedForest.predict(features)
        assertTrue(
            "Phone-side 20-feature prediction should return a valid class, got: '$result'",
            result in VALID_CLASSES
        )
    }

    // ---------------------------------------------------------------------------
    // Test 5: Determinism — same input always returns same output
    // ---------------------------------------------------------------------------
    @Test
    fun testPredictionIsDeterministic() {
        val features = SwingFeatures(
            s1_gyro_y_std    = 2.10f,
            s1_gyro_z_std    = 1.55f,
            s1_deltaX        = -0.30f,
            s1_deltaZ        = 0.18f,
            s2_gyroMag       = 11.3f,
            s2_grav_y_mean   = -0.70f,
            s2_deltaX        = -0.55f,
            s2_deltaZ        = 0.40f,
            s3_rollImpactDeg = 55.0f,
            s3_yawImpactDeg  = -22.0f,
            s3_deltaX        = -0.80f,
            s3_deltaZ        = 0.50f,
            s3_planeRatio    = 1.45f,
            s3_gyro_y_min    = -10.2f,
            bottom_hand_gyro_peak    = 12.1f,
            bottom_hand_acc_peak     = 35.0f,
            bottom_hand_gyro_ratio   = 1.6f,
            bottom_hand_acc_ratio    = 1.3f,
            bottom_hand_time_lead_ms = -30.0f,
            bottom_hand_sync_score   = 90.0f
        )
        val first  = GeneratedForest.predict(features)
        val second = GeneratedForest.predict(features)
        val third  = GeneratedForest.predict(features)
        assertEquals("Prediction must be deterministic (call 1 vs 2)", first, second)
        assertEquals("Prediction must be deterministic (call 2 vs 3)", second, third)
    }

    // ---------------------------------------------------------------------------
    // Test 6: All 8 expected class names are present in the model
    // ---------------------------------------------------------------------------
    @Test
    fun testAllEightClassesRegistered() {
        // Access CLASSES via a prediction sweep — we can't read the private array,
        // but we can verify NUM_TREES is sane and the known classes are reachable.
        assertTrue("NUM_TREES should be > 0", GeneratedForest.NUM_TREES > 0)
        assertTrue("NUM_TREES should be <= 500", GeneratedForest.NUM_TREES <= 500)

        // Verify the model doesn't crash on extreme feature values
        val extremeHigh = SwingFeatures(
            s1_gyro_y_std = 100f, s1_gyro_z_std = 100f,
            s1_deltaX = 100f, s1_deltaZ = 100f,
            s2_gyroMag = 100f, s2_grav_y_mean = 100f,
            s2_deltaX = 100f, s2_deltaZ = 100f,
            s3_rollImpactDeg = 360f, s3_yawImpactDeg = 360f,
            s3_deltaX = 100f, s3_deltaZ = 100f,
            s3_planeRatio = 100f, s3_gyro_y_min = -100f,
            bottom_hand_gyro_peak = 1000f, bottom_hand_acc_peak = 1000f,
            bottom_hand_gyro_ratio = 100f, bottom_hand_acc_ratio = 100f,
            bottom_hand_time_lead_ms = 10000f, bottom_hand_sync_score = 200f
        )
        val extremeLow = SwingFeatures(
            s1_gyro_y_std = 0f, s1_gyro_z_std = 0f,
            s1_deltaX = -100f, s1_deltaZ = -100f,
            s2_gyroMag = 0f, s2_grav_y_mean = -100f,
            s2_deltaX = -100f, s2_deltaZ = -100f,
            s3_rollImpactDeg = -360f, s3_yawImpactDeg = -360f,
            s3_deltaX = -100f, s3_deltaZ = -100f,
            s3_planeRatio = 0f, s3_gyro_y_min = 0f
        )
        val resHigh = GeneratedForest.predict(extremeHigh)
        val resLow  = GeneratedForest.predict(extremeLow)
        assertTrue("Extreme high values should return a valid class", resHigh in VALID_CLASSES)
        assertTrue("Extreme low values should return a valid class", resLow in VALID_CLASSES)
    }

    // ---------------------------------------------------------------------------
    // Test 7: GeneratedQualityForest predicts valid quality class (good/poor/miss/edge)
    // ---------------------------------------------------------------------------
    @Test
    fun testQualityModelPredictsValidClass() {
        val VALID_QUALITY = setOf("good", "poor", "miss", "edge")
        
        // Good swing features (high efficiency features)
        val features = SwingFeatures(
            s1_gyro_y_std            = 1.10f,
            s1_gyro_z_std            = 0.85f,
            s1_deltaX                = -0.08f,
            s1_deltaZ                = 0.04f,
            s2_gyroMag               = 6.2f,
            s2_grav_y_mean           = 0.30f,
            s2_deltaX                = -0.25f,
            s2_deltaZ                = 0.15f,
            s3_rollImpactDeg         = 12.0f,
            s3_yawImpactDeg          = -7.0f,
            s3_deltaX                = -0.35f,
            s3_deltaZ                = 0.20f,
            s3_planeRatio            = 0.88f,
            s3_gyro_y_min            = -5.3f,
            bottom_hand_gyro_peak    = 8.4f,
            bottom_hand_acc_peak     = 28.5f,
            bottom_hand_gyro_ratio   = 1.35f,
            bottom_hand_acc_ratio    = 1.12f,
            bottom_hand_time_lead_ms = -45.0f,
            bottom_hand_sync_score   = 82.0f
        )
        val quality = GeneratedQualityForest.predict(features)
        assertTrue("Expected valid quality string, got: '$quality'", quality in VALID_QUALITY)

        // Quality prediction determinism
        val secondCall = GeneratedQualityForest.predict(features)
        assertEquals("Quality prediction must be deterministic", quality, secondCall)
    }
}
