package com.mrpeel.cricketbattingtracker.ml

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.*

class BladeAndLaunchAngleTest {

    private fun classifyBlade(angle: Float): String {
        return when {
            angle <= -15.0f -> "OPEN"
            angle >= 15.0f -> "CLOSED"
            else -> "FULL_FACE"
        }
    }

    private fun classifyLaunch(angle: Float): String {
        return when {
            angle < -45.0f -> "HIGH_LOFT"
            angle < -35.0f -> "POWER_ZONE"
            angle < -15.0f -> "LOFTED"
            angle < 0.0f -> "FLAT"
            else -> "INTO_GROUND"
        }
    }

    private fun classifyLaunchSummary(angle: Float): String {
        return when {
            angle < -1.5f -> "Lofted"
            angle > 1.5f -> "Ground"
            else -> "Flat"
        }
    }

    @Test
    fun testBladeClassificationBoundaries() {
        assertEquals("OPEN", classifyBlade(-15.1f))
        assertEquals("OPEN", classifyBlade(-15.0f))
        assertEquals("FULL_FACE", classifyBlade(-14.9f))
        assertEquals("FULL_FACE", classifyBlade(0.0f))
        assertEquals("FULL_FACE", classifyBlade(14.9f))
        assertEquals("CLOSED", classifyBlade(15.0f))
        assertEquals("CLOSED", classifyBlade(15.1f))
    }

    @Test
    fun testLaunchClassificationBoundaries() {
        assertEquals("HIGH_LOFT", classifyLaunch(-46.0f))
        assertEquals("POWER_ZONE", classifyLaunch(-40.0f))
        assertEquals("LOFTED", classifyLaunch(-20.0f))
        assertEquals("FLAT", classifyLaunch(-5.0f))
        assertEquals("INTO_GROUND", classifyLaunch(0.0f))
        assertEquals("INTO_GROUND", classifyLaunch(25.0f))
    }

    @Test
    fun testLaunchSummaryClassification() {
        assertEquals("Lofted", classifyLaunchSummary(-18.0f))
        assertEquals("Lofted", classifyLaunchSummary(-2.0f))
        assertEquals("Flat", classifyLaunchSummary(0.0f))
        assertEquals("Flat", classifyLaunchSummary(1.0f))
        assertEquals("Ground", classifyLaunchSummary(2.0f))
        assertEquals("Ground", classifyLaunchSummary(25.0f))
    }

    @Test
    fun testAngleNormalizationWraparound() {
        fun normalizeAngle(angle: Float): Float {
            return ((angle + 180f) % 360f + 360f) % 360f - 180f
        }

        assertEquals(0f, normalizeAngle(0f), 1e-4f)
        assertEquals(-170f, normalizeAngle(190f), 1e-4f)
        assertEquals(170f, normalizeAngle(-190f), 1e-4f)
        assertEquals(45f, normalizeAngle(405f), 1e-4f)
        assertEquals(-45f, normalizeAngle(-405f), 1e-4f)
    }

    @Test
    fun testTargetYawMappingAcrossShotClasses() {
        fun getTargetYaw(shotType: String): Float {
            return when {
                shotType.contains("COVER", ignoreCase = true) -> -45f
                shotType.contains("ON DRIVE", ignoreCase = true) -> 15f
                shotType.contains("CUT", ignoreCase = true) -> 40f
                shotType.contains("PULL", ignoreCase = true) || shotType.contains("SLOG", ignoreCase = true) -> 55f
                shotType.contains("SWEEP", ignoreCase = true) -> 65f
                shotType.contains("GLANCE", ignoreCase = true) || shotType.contains("FLICK", ignoreCase = true) -> 75f
                else -> 0f
            }
        }

        assertEquals(-45f, getTargetYaw("COVER DRIVE"), 1e-4f)
        assertEquals(0f, getTargetYaw("DRIVE/DEFENCE"), 1e-4f)
        assertEquals(0f, getTargetYaw("STRAIGHT DRIVE"), 1e-4f)
        assertEquals(15f, getTargetYaw("ON DRIVE"), 1e-4f)
        assertEquals(40f, getTargetYaw("CUT/PUNCH"), 1e-4f)
        assertEquals(55f, getTargetYaw("PULL/HOOK"), 1e-4f)
        assertEquals(55f, getTargetYaw("SLOG"), 1e-4f)
        assertEquals(65f, getTargetYaw("SWEEP"), 1e-4f)
        assertEquals(75f, getTargetYaw("GLANCE/FLICK"), 1e-4f)
    }
}
