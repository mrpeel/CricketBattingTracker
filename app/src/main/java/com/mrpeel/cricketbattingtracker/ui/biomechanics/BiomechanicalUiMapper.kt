package com.mrpeel.cricketbattingtracker.ui.biomechanics

import java.util.Locale

/**
 * Maps raw IMU cross-correlation telemetry and TCN classification outputs into human-readable,
 * qualitative biomechanical coaching metrics anchored strictly to batting_dual_hand_biomechanics.md.
 */
object BiomechanicalUiMapper {

    /**
     * Map raw shot metrics into a [BiomechanicalUiState].
     *
     * @param shotClass The classified shot name (e.g., "PULL/HOOK", "DRIVE/DEFENCE", "GLANCE/FLICK").
     * @param timeLeadMs Time delta in milliseconds (bottom-hand peak time minus top-hand impact time).
     * @param gyroRatio Ratio of bottom-hand gyro magnitude to top-hand watch gyro magnitude.
     * @param accRatio Ratio of bottom-hand acceleration peak to top-hand acceleration peak.
     */
    fun mapToUiState(
        shotClass: String?,
        timeLeadMs: Float?,
        gyroRatio: Float?,
        accRatio: Float?
    ): BiomechanicalUiState {
        val shotUpper = shotClass?.uppercase(Locale.ROOT) ?: ""
        
        // Handle watch-only mode or missing Polar telemetry gracefully
        if (timeLeadMs == null || gyroRatio == null || accRatio == null ||
            (timeLeadMs == 0f && gyroRatio == 0f && accRatio == 0f)
        ) {
            return BiomechanicalUiState(
                sequencingTitle = "Top-Hand Path",
                sequencingDescription = "Single-wrist lead tracking top-hand rotational downswing.",
                sequencingSliderVal = 0.70f,
                powerPatternTitle = "Lead Wrist Tracking",
                powerPatternDescription = "Top-hand IMU tracking angular velocity and swing slot plane.",
                powerSliderVal = 0.70f,
                coachingInsight = "Connect Polar Verity Sense on trailing forearm for dual-wrist biomechanical diagnostics.",
                displaysWarning = false
            )
        }

        return when {
            "PULL" in shotUpper || "HOOK" in shotUpper -> mapPullHook(timeLeadMs, gyroRatio, accRatio)
            "POWER" in shotUpper -> mapPowerDrive(timeLeadMs, gyroRatio, accRatio)
            "DRIVE" in shotUpper || "DEFENCE" in shotUpper || "BLOCK" in shotUpper -> mapDriveDefence(timeLeadMs, gyroRatio, accRatio)
            "GLANCE" in shotUpper || "FLICK" in shotUpper -> mapGlanceFlick(timeLeadMs, gyroRatio, accRatio)
            "CUT" in shotUpper || "PUNCH" in shotUpper -> mapCutPunch(timeLeadMs, gyroRatio, accRatio)
            "DEFLECTION" in shotUpper || "GUIDE" in shotUpper -> mapDeflectionGuide(timeLeadMs, gyroRatio, accRatio)
            "SLOG" in shotUpper -> mapSlog(timeLeadMs, gyroRatio, accRatio)
            "SWEEP" in shotUpper -> mapSweep(timeLeadMs, gyroRatio, accRatio)
            else -> mapGenericFallback(timeLeadMs, gyroRatio, accRatio)
        }
    }

    private fun mapPullHook(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -30.0f..-10.0f -> Triple(
                "Perfect Snap",
                "The bottom hand cleared the arc beautifully ahead of the wrist turnover.",
                0.85f
            )
            timeLeadMs > 40.0f -> {
                warning = true
                Triple(
                    "Dragged Blade",
                    "The bottom hand severely lagged behind the rotation of your shoulders, leaving the bat face trailing.",
                    0.15f
                )
            }
            timeLeadMs > 0.0f -> Triple(
                "Late Release",
                "Hands pushed along a linear path late instead of snapping smoothly through the arc.",
                0.35f
            )
            else -> Triple(
                "Slight Lag",
                "Bottom hand snap initiated slightly outside optimal timing window.",
                0.50f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            accRatio >= 1.20f && gyroRatio <= 0.22f -> Triple(
                "Explosive Punch",
                "High linear handle acceleration. Clean, optimal force application through a cross-bat shot.",
                0.90f
            )
            accRatio < 0.80f -> Triple(
                "Weak Bottom Hand",
                "The shot lacked punching power; trailing arm failed to drive through the horizontal plane.",
                0.25f
            )
            else -> Triple(
                "Moderate Drive",
                "Standard power application across the horizontal plane.",
                0.60f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Rotate hips early and ensure bottom wrist snaps through the arc before contact for maximum pull shot power.",
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapDriveDefence(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in 5.0f..20.0f -> Triple(
                "Clean Extension",
                "Top hand completely dominated the vertical path, keeping the downswing tracking down the slot.",
                0.80f
            )
            timeLeadMs < 0.0f -> Triple(
                "Early Wrist Snap",
                "The bottom hand closed the bat face prematurely before reaching the line of the ball.",
                0.20f
            )
            else -> {
                warning = true
                Triple(
                    "Dragged Blade",
                    "The bottom hand severely lagged behind the rotation of your shoulders, leaving the bat face trailing.",
                    0.30f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio > 0.85f -> {
                warning = true
                Triple(
                    "Hard Bottom Hand",
                    "The bottom hand choked the handle mid-downswing, risking a closed blade and an airborne mistiming.",
                    0.15f
                )
            }
            gyroRatio in 0.45f..0.70f -> Triple(
                "Top-Hand Control",
                "Perfect passive hinge behavior, keeping the ball grounded on a vertical drive.",
                0.85f
            )
            else -> Triple(
                "Sub-optimal Grip",
                "Grip balance deviated slightly from ideal vertical drive control.",
                0.50f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Keep your bottom hand grip light to maintain top-hand control down the slot and prevent closing the face.",
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapGlanceFlick(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -15.0f..-5.0f -> Triple(
                "Perfect Timing",
                "The bottom hand cleared the arc beautifully ahead of the wrist turnover.",
                0.90f
            )
            timeLeadMs > 10.0f -> {
                warning = true
                Triple(
                    "Delayed Snap",
                    "Bottom-hand wrist snap occurred too late after ball contact.",
                    0.20f
                )
            }
            else -> Triple(
                "Early Flick",
                "Wrist closed ahead of ball contact line.",
                0.40f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.20f -> Triple(
                "Dynamic Wrist Snap",
                "High gyro velocity spike leading right before contact.",
                0.85f
            )
            else -> Triple(
                "Passive Deflection",
                "Lacked sharp wrist pronation; ball deflected without active flick.",
                0.35f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Time the bottom wrist pronation precisely at impact line to glance off pads cleanly.",
            displaysWarning = warning
        )
    }

    private fun mapCutPunch(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -5.0f..5.0f -> Triple(
                "Synchronous Wrist Lock",
                "Both wrists locked and fired symmetrically to slap the ball laterally.",
                0.85f
            )
            timeLeadMs > 20.0f -> {
                warning = true
                Triple(
                    "Lagging Cut Face",
                    "Bottom hand trailed the rotational plane, leaving the face open under contact.",
                    0.20f
                )
            }
            else -> Triple(
                "Asynchronous Release",
                "Hand timing deviated from synchronous 0ms lock.",
                0.45f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio in 0.90f..1.10f && accRatio in 0.85f..1.15f -> Triple(
                "Balanced Punch",
                "Symmetrical force application with perfectly overlapping acceleration profiles.",
                0.90f
            )
            accRatio < 0.70f -> Triple(
                "Weak Lateral Drive",
                "Lacked cross-body punching force; wrists did not lock rigidly.",
                0.30f
            )
            else -> Triple(
                "Uneven Power Split",
                "Asymmetrical force delivery across hands.",
                0.50f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Maintain an isometric rigid wrist lock across both hands through impact for a square, controlled cut.",
            displaysWarning = warning
        )
    }

    private fun mapDeflectionGuide(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in 15.0f..40.0f -> Triple(
                "Intentional Lag",
                "Top hand independently supinated late while bottom hand maintained passive lag.",
                0.85f
            )
            timeLeadMs < 10.0f -> Triple(
                "Rushed Blade Face",
                "Bottom hand pushed early instead of allowing top hand to steer late.",
                0.30f
            )
            else -> Triple(
                "Extended Lag",
                "Bottom hand lag slightly out of target deflection window.",
                0.50f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio in 0.15f..0.40f && accRatio <= 0.25f -> Triple(
                "Loose Grip Deflection",
                "Finger-only control on trailing hand offered minimal resistance for late angle.",
                0.85f
            )
            gyroRatio > 0.50f -> {
                warning = true
                Triple(
                    "Overactive Trailing Hand",
                    "Bottom hand grabbed handle tight, spoiling the soft deflected glide.",
                    0.20f
                )
            }
            else -> Triple(
                "Passive Support",
                "Soft grip force with subtle trailing control.",
                0.60f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Keep bottom hand grip tension loose (finger-only) to let top hand flex blade angle open late.",
            displaysWarning = warning
        )
    }

    private fun mapPowerDrive(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -10.0f..0.0f -> Triple(
                "Explosive Release",
                "Top hand pulled down the slot before bottom hand fired an explosive impact burst.",
                0.90f
            )
            timeLeadMs > 15.0f -> {
                warning = true
                Triple(
                    "Stalled Extension",
                    "Downswing stalled before impact, losing vertical loft momentum.",
                    0.25f
                )
            }
            else -> Triple(
                "Slight Timing Drift",
                "Release window slightly off peak acceleration alignment.",
                0.50f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.10f && accRatio >= 1.10f -> Triple(
                "Lofted Drive Acceleration",
                "Explosive upward linear acceleration driving upward to loft and elevate the ball.",
                0.90f
            )
            accRatio < 0.90f -> Triple(
                "Insufficient Vertical Lift",
                "Bottom hand failed to accelerate through hitting zone for power loft.",
                0.30f
            )
            else -> Triple(
                "Solid Drive Acceleration",
                "Good force generation through impact arc.",
                0.65f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Drive upward with bottom-hand linear acceleration through the hitting zone into full follow-through extension.",
            displaysWarning = warning
        )
    }

    private fun mapSlog(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -25.0f..-5.0f -> Triple(
                "Co-Explosive Snap",
                "Both hands applied maximum force almost simultaneously right from backswing transition.",
                0.90f
            )
            timeLeadMs > 0.0f -> {
                warning = true
                Triple(
                    "Hesitant Arc",
                    "Lagging bottom release choked angular acceleration through the hitting arc.",
                    0.25f
                )
            }
            else -> Triple(
                "Unbalanced Release",
                "Timing lead outside peak slog arc release window.",
                0.45f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.75f && accRatio >= 1.50f -> Triple(
                "Maximum Release",
                "Violent bottom-wrist release driving absolute angular acceleration across all axes.",
                0.95f
            )
            gyroRatio < 1.30f -> Triple(
                "Restricted Arc Power",
                "Wrist action restricted swing radius and peak angular velocity.",
                0.30f
            )
            else -> Triple(
                "High Arc Velocity",
                "Strong bottom-hand angular acceleration.",
                0.70f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Unleash continuous bottom-hand wrist snap from top of backswing through an unrestricted hitting arc.",
            displaysWarning = warning
        )
    }

    private fun mapSweep(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -10.0f..5.0f -> Triple(
                "Phase-Locked Torque",
                "Hands operated as a coupled extension of core torso rotation low to ground.",
                0.85f
            )
            timeLeadMs > 15.0f -> {
                warning = true
                Triple(
                    "Uncoupled Rotation",
                    "Bottom arm disconnected from core torso rotation, dragging behind the horizontal arc.",
                    0.25f
                )
            }
            else -> Triple(
                "Asymmetrical Sweep Arc",
                "Minor timing variance across horizontal sweeping plane.",
                0.50f
            )
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio in 1.05f..1.30f && accRatio in 0.90f..1.20f -> Triple(
                "Torso-Linked Sweep",
                "Continuous, coupled force profiles extending low across front knee.",
                0.85f
            )
            accRatio < 0.70f -> {
                warning = true
                Triple(
                    "Arm-Only Sweep",
                    "Relied on arm pull rather than driving torso rotation through the ball.",
                    0.25f
                )
            }
            else -> Triple(
                "Guided Horizontal Sweep",
                "Adequate horizontal plane force coupling.",
                0.60f
            )
        }

        return BiomechanicalUiState(
            sequencingTitle = seqTitle,
            sequencingDescription = seqDesc,
            sequencingSliderVal = seqVal,
            powerPatternTitle = powerTitle,
            powerPatternDescription = powerDesc,
            powerSliderVal = powerVal,
            coachingInsight = "Crouch low over front knee and drive sweep arc using torso rotational torque rather than arm-only pulling.",
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapGenericFallback(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        return BiomechanicalUiState(
            sequencingTitle = "Standard Sequencing",
            sequencingDescription = "Swing execution within general timing parameters.",
            sequencingSliderVal = 0.60f,
            powerPatternTitle = "Balanced Force",
            powerPatternDescription = "Standard multi-wrist force generation.",
            powerSliderVal = 0.60f,
            coachingInsight = "Maintain clean head position and balanced grip pressure throughout the stroke.",
            displaysWarning = false
        )
    }
}
