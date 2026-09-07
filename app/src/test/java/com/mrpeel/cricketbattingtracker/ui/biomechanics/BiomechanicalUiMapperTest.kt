package com.mrpeel.cricketbattingtracker.ui.biomechanics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BiomechanicalUiMapperTest {

    @Test
    fun testPullHookPerfectSnapAndExplosivePunch() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "PULL/HOOK",
            timeLeadMs = -20.0f,
            gyroRatio = 0.15f,
            accRatio = 1.30f
        )

        assertEquals("Perfect Snap", state.sequencingTitle)
        assertEquals("Explosive Punch", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
        assertTrue(state.coachingInsight.contains("Rotate hips early"))
    }

    @Test
    fun testPullHookDraggedBladeTriggersWarning() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "PULL/HOOK",
            timeLeadMs = 45.0f,
            gyroRatio = 0.20f,
            accRatio = 1.00f
        )

        assertEquals("Dragged Blade", state.sequencingTitle)
        assertTrue(state.displaysWarning)
    }

    @Test
    fun testDriveDefenceCleanExtensionAndHardBottomHand() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DRIVE/DEFENCE",
            timeLeadMs = 10.0f,
            gyroRatio = 0.95f,
            accRatio = 0.50f
        )

        assertEquals("Clean Extension", state.sequencingTitle)
        assertEquals("Hard Bottom Hand", state.powerPatternTitle)
        assertTrue(state.displaysWarning)
    }

    @Test
    fun testDriveDefenceTopHandControl() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DRIVE/DEFENCE",
            timeLeadMs = 12.0f,
            gyroRatio = 0.55f,
            accRatio = 0.50f
        )

        assertEquals("Clean Extension", state.sequencingTitle)
        assertEquals("Top-Hand Control", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testGlanceFlickPerfectTimingAndDynamicSnap() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "GLANCE/FLICK",
            timeLeadMs = -10.0f,
            gyroRatio = 1.30f,
            accRatio = 1.10f
        )

        assertEquals("Perfect Timing", state.sequencingTitle)
        assertEquals("Dynamic Wrist Snap", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testCutPunchSynchronousAndBalanced() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "CUT/PUNCH",
            timeLeadMs = 0.0f,
            gyroRatio = 1.00f,
            accRatio = 1.00f
        )

        assertEquals("Synchronous Wrist Lock", state.sequencingTitle)
        assertEquals("Balanced Punch", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testDeflectionGuideIntentionalLag() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DEFLECTION/GUIDE",
            timeLeadMs = 25.0f,
            gyroRatio = 0.25f,
            accRatio = 0.20f
        )

        assertEquals("Intentional Lag", state.sequencingTitle)
        assertEquals("Loose Grip Deflection", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testPowerDriveExplosiveRelease() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "POWER DRIVE",
            timeLeadMs = -5.0f,
            gyroRatio = 1.20f,
            accRatio = 1.25f
        )

        assertEquals("Explosive Release", state.sequencingTitle)
        assertEquals("Lofted Drive Acceleration", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testSlogCoExplosiveSnap() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "SLOG",
            timeLeadMs = -15.0f,
            gyroRatio = 1.80f,
            accRatio = 1.60f
        )

        assertEquals("Co-Explosive Snap", state.sequencingTitle)
        assertEquals("Maximum Release", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testSweepPhaseLockedTorque() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "SWEEP",
            timeLeadMs = 0.0f,
            gyroRatio = 1.15f,
            accRatio = 1.05f
        )

        assertEquals("Phase-Locked Torque", state.sequencingTitle)
        assertEquals("Torso-Linked Sweep", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testWatchOnlyModeNullTelemetry() {
        val stateNull = BiomechanicalUiMapper.mapToUiState(
            shotClass = "PULL/HOOK",
            timeLeadMs = null,
            gyroRatio = null,
            accRatio = null
        )

        assertEquals("Top-Hand Path", stateNull.sequencingTitle)
        assertEquals("Lead Wrist Tracking", stateNull.powerPatternTitle)
        assertFalse(stateNull.displaysWarning)

        val stateZero = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DRIVE/DEFENCE",
            timeLeadMs = 0f,
            gyroRatio = 0f,
            accRatio = 0f
        )

        assertEquals("Top-Hand Path", stateZero.sequencingTitle)
        assertFalse(stateZero.displaysWarning)
    }

    @Test
    fun testNormalizeShotTypeGroundTruthMappings() {
        val normalize = { s: String? -> com.mrpeel.cricketbattingtracker.normalizeShotType(s) }

        // Verify that Title Case / narration strings map to canonical 8 classes
        assertEquals("POWER DRIVE", normalize("Power drive"))
        assertEquals("POWER DRIVE", normalize("power drive"))
        assertEquals("POWER DRIVE", normalize("POWER DRIVE"))
        assertEquals("POWER DRIVE", normalize("Power drive "))
        assertEquals("POWER DRIVE", normalize("Lofted drive"))

        assertEquals("DEFLECTION/GUIDE", normalize("Guide"))
        assertEquals("DEFLECTION/GUIDE", normalize("guide"))
        assertEquals("DEFLECTION/GUIDE", normalize("DEFLECTION/GUIDE"))
        assertEquals("DEFLECTION/GUIDE", normalize("Deflection"))
        assertEquals("DEFLECTION/GUIDE", normalize("Glide"))

        assertEquals("PULL/HOOK", normalize("Pull shot"))
        assertEquals("PULL/HOOK", normalize("pull"))
        assertEquals("PULL/HOOK", normalize("PULL/HOOK"))
        assertEquals("PULL/HOOK", normalize("Hook"))

        assertEquals("GLANCE/FLICK", normalize("Flick shot"))
        assertEquals("GLANCE/FLICK", normalize("flick"))
        assertEquals("GLANCE/FLICK", normalize("GLANCE/FLICK"))
        assertEquals("GLANCE/FLICK", normalize("Glance"))

        assertEquals("DRIVE/DEFENCE", normalize("Forward defense"))
        assertEquals("DRIVE/DEFENCE", normalize("On drive"))
        assertEquals("DRIVE/DEFENCE", normalize("Cover drive"))
        assertEquals("DRIVE/DEFENCE", normalize("Straight drive"))
        assertEquals("DRIVE/DEFENCE", normalize("DRIVE/DEFENCE"))

        assertEquals("CUT/PUNCH", normalize("Cut shot"))
        assertEquals("CUT/PUNCH", normalize("Punch"))
        assertEquals("CUT/PUNCH", normalize("CUT/PUNCH"))

        assertEquals("SLOG", normalize("Slog"))
        assertEquals("SLOG", normalize("SLOG"))

        assertEquals("SWEEP", normalize("Sweep"))
        assertEquals("SWEEP", normalize("SWEEP"))
    }

    @Test
    fun testPullHookBatHandleCleanWhip() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "PULL/HOOK",
            timeLeadMs = -10.0f,
            gyroRatio = 1.40f,
            accRatio = 1.20f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Fast Blade Whip", state.sequencingTitle)
        assertEquals("Full Power Arc", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
        assertTrue(state.coachingInsight.startsWith("Action: "))
        assertTrue(state.coachingInsight.contains("let the bat follow through over your shoulder"))
    }

    @Test
    fun testPullHookBatHandleBatDraggingBehindTriggersWarning() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "PULL/HOOK",
            timeLeadMs = 15.0f,
            gyroRatio = 1.20f,
            accRatio = 1.00f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Bat Dragging Behind", state.sequencingTitle)
        assertTrue(state.displaysWarning)
        assertTrue(state.coachingInsight.contains("Commit your bat into the swing"))
    }

    @Test
    fun testDriveDefenceBatHandleCleanPendulum() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DRIVE/DEFENCE",
            timeLeadMs = 0.0f,
            gyroRatio = 1.25f,
            accRatio = 1.10f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Clean Pendulum Flow", state.sequencingTitle)
        assertEquals("Crisp Bat Flow", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
        assertTrue(state.coachingInsight.contains("let the bat flow down the ground"))
    }

    @Test
    fun testDriveDefenceBatHandleLaggingAndStiffArms() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DRIVE/DEFENCE",
            timeLeadMs = 15.0f,
            gyroRatio = 0.85f,
            accRatio = 0.90f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Bat Lagging Behind Hands", state.sequencingTitle)
        assertEquals("Pushed with Stiff Arms", state.powerPatternTitle)
        assertTrue(state.displaysWarning)
        assertTrue(state.coachingInsight.contains("Lead with your front elbow"))
    }

    @Test
    fun testDeflectionGuideBatHandleSoftHands() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "DEFLECTION/GUIDE",
            timeLeadMs = 20.0f,
            gyroRatio = 0.75f,
            accRatio = 0.60f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Soft-Hand Guide", state.sequencingTitle)
        assertEquals("Controlled Soft Hands", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
        assertTrue(state.coachingInsight.contains("run the ball down to third man"))
    }

    @Test
    fun testCutPunchBatHandleCrispAndTrailing() {
        val cleanState = BiomechanicalUiMapper.mapToUiState(
            shotClass = "CUT/PUNCH",
            timeLeadMs = 0.0f,
            gyroRatio = 1.20f,
            accRatio = 1.00f,
            polarMountMode = "BAT_HANDLE"
        )
        assertEquals("Crisp Square Slap", cleanState.sequencingTitle)
        assertEquals("Sharp Blade Snap", cleanState.powerPatternTitle)
        assertFalse(cleanState.displaysWarning)

        val trailingState = BiomechanicalUiMapper.mapToUiState(
            shotClass = "CUT/PUNCH",
            timeLeadMs = 15.0f,
            gyroRatio = 1.00f,
            accRatio = 1.00f,
            polarMountMode = "BAT_HANDLE"
        )
        assertEquals("Bat Trailing Hands", trailingState.sequencingTitle)
        assertTrue(trailingState.displaysWarning)
        assertTrue(trailingState.coachingInsight.contains("snap the bat down and through"))
    }

    @Test
    fun testPowerDriveBatHandlePowerLoft() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "POWER DRIVE",
            timeLeadMs = -5.0f,
            gyroRatio = 1.40f,
            accRatio = 1.30f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Power Loft Timing", state.sequencingTitle)
        assertEquals("Explosive Blade Speed", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testSlogBatHandleFullArcCommitment() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "SLOG",
            timeLeadMs = -10.0f,
            gyroRatio = 1.50f,
            accRatio = 1.40f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Full Arc Commitment", state.sequencingTitle)
        assertEquals("High Bat Speed", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testSweepBatHandleCleanLowSweep() {
        val state = BiomechanicalUiMapper.mapToUiState(
            shotClass = "SWEEP",
            timeLeadMs = -5.0f,
            gyroRatio = 1.20f,
            accRatio = 1.00f,
            polarMountMode = "BAT_HANDLE"
        )

        assertEquals("Clean Low Sweep", state.sequencingTitle)
        assertEquals("Full Sweep Flow", state.powerPatternTitle)
        assertFalse(state.displaysWarning)
    }

    @Test
    fun testJargonFreeAuditAcrossAllBatHandleStates() {
        val forbiddenJargon = listOf(
            "choked",
            "lever transfer",
            "kinetic chain",
            "rotational downswing",
            "pronation",
            "supination",
            "isometric",
            "bottom hand",
            "trailing arm",
            "bottom wrist",
            "multi-wrist"
        )

        val shots = listOf(
            "PULL/HOOK",
            "DRIVE/DEFENCE",
            "POWER DRIVE",
            "CUT/PUNCH",
            "GLANCE/FLICK",
            "DEFLECTION/GUIDE",
            "SLOG",
            "SWEEP",
            "UNKNOWN"
        )

        val timings = listOf(-35f, -15f, 0f, 15f, 35f)
        val gyroRatios = listOf(0.6f, 0.9f, 1.2f, 1.6f)
        val accRatios = listOf(0.5f, 1.0f, 1.5f)

        for (shot in shots) {
            for (t in timings) {
                for (gr in gyroRatios) {
                    for (ar in accRatios) {
                        val state = BiomechanicalUiMapper.mapToUiState(
                            shotClass = shot,
                            timeLeadMs = t,
                            gyroRatio = gr,
                            accRatio = ar,
                            polarMountMode = "BAT_HANDLE"
                        )

                        val combinedText = "${state.sequencingTitle} ${state.sequencingDescription} " +
                                "${state.powerPatternTitle} ${state.powerPatternDescription} ${state.coachingInsight}"
                        val lowerCombined = combinedText.lowercase(java.util.Locale.ROOT)

                        for (jargon in forbiddenJargon) {
                            assertFalse(
                                "Found forbidden jargon '$jargon' in bat-mode text for $shot (t=$t, gr=$gr, ar=$ar):\n$combinedText",
                                lowerCombined.contains(jargon)
                            )
                        }

                        assertTrue(
                            "Coaching insight for $shot should start with 'Action: ':\n${state.coachingInsight}",
                            state.coachingInsight.startsWith("Action: ")
                        )
                    }
                }
            }
        }
    }
}
