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
        accRatio: Float?,
        polarMountMode: String? = null
    ): BiomechanicalUiState {
        val shotUpper = shotClass?.uppercase(Locale.ROOT) ?: ""
        val isBatHandle = polarMountMode?.equals("BAT_HANDLE", ignoreCase = true) == true
        
        // Handle watch-only mode or missing Polar telemetry gracefully
        if (timeLeadMs == null || gyroRatio == null || accRatio == null ||
            (timeLeadMs == 0f && gyroRatio == 0f && accRatio == 0f)
        ) {
            return BiomechanicalUiState(
                sequencingTitle = if (isBatHandle) "Lead Wrist Path" else "Top-Hand Path",
                sequencingDescription = if (isBatHandle) {
                    "Single-sensor tracking downswing path from your lead wrist."
                } else {
                    "Single-wrist lead tracking top-hand downswing path."
                },
                sequencingSliderVal = 0.70f,
                powerPatternTitle = if (isBatHandle) "Lead Wrist Speed" else "Lead Wrist Tracking",
                powerPatternDescription = if (isBatHandle) {
                    "Lead wrist sensor tracking swing speed and impact timing."
                } else {
                    "Top-hand sensor tracking swing speed and impact path."
                },
                powerSliderVal = 0.70f,
                coachingInsight = if (isBatHandle) {
                    "Attach second sensor to bat handle to enable bat swing timing and speed analysis."
                } else {
                    "Connect second sensor on trailing wrist for dual-hand coordination diagnostics."
                },
                displaysWarning = false
            )
        }

        if (isBatHandle) {
            return mapBatHandleDynamics(shotUpper, timeLeadMs, gyroRatio, accRatio)
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

    // ═══════════════════════════════════════════════════════════════════════════
    // BAT-MOUNTED SENSOR DYNAMICS (BAT_HANDLE)
    // Clear, understandable, actionable cricket coaching language with zero jargon
    // ═══════════════════════════════════════════════════════════════════════════

    private fun mapBatHandleDynamics(
        shotUpper: String,
        timeLeadMs: Float,
        gyroRatio: Float,
        accRatio: Float
    ): BiomechanicalUiState {
        return when {
            "PULL" in shotUpper || "HOOK" in shotUpper -> mapBatPullHook(timeLeadMs, gyroRatio, accRatio)
            "POWER" in shotUpper -> mapBatPowerDrive(timeLeadMs, gyroRatio, accRatio)
            "DRIVE" in shotUpper || "DEFENCE" in shotUpper || "BLOCK" in shotUpper -> mapBatDriveDefence(timeLeadMs, gyroRatio, accRatio)
            "GLANCE" in shotUpper || "FLICK" in shotUpper -> mapBatGlanceFlick(timeLeadMs, gyroRatio, accRatio)
            "CUT" in shotUpper || "PUNCH" in shotUpper -> mapBatCutPunch(timeLeadMs, gyroRatio, accRatio)
            "DEFLECTION" in shotUpper || "GUIDE" in shotUpper -> mapBatDeflectionGuide(timeLeadMs, gyroRatio, accRatio)
            "SLOG" in shotUpper -> mapBatSlog(timeLeadMs, gyroRatio, accRatio)
            "SWEEP" in shotUpper -> mapBatSweep(timeLeadMs, gyroRatio, accRatio)
            else -> mapBatGenericFallback(timeLeadMs, gyroRatio, accRatio)
        }
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatPullHook(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -25.0f..5.0f -> {
                actionText = "Action: Keep that aggressive hip turn and let the bat follow through over your shoulder."
                Triple(
                    "Fast Blade Whip",
                    "The bat whipped through the hitting zone with great timing, meeting the ball cleanly out in front.",
                    0.90f
                )
            }
            timeLeadMs > 5.0f -> {
                warning = true
                actionText = "Action: Commit your bat into the swing as you turn — let the bat head whip around your body."
                Triple(
                    "Bat Dragging Behind",
                    "Your body turned but the bat lagged behind your hands, causing you to slice or hit under the ball.",
                    0.20f
                )
            }
            else -> {
                actionText = "Action: Wait for the ball to reach chest height before pulling through."
                Triple(
                    "Early Swing",
                    "You swung the bat through too early before the ball arrived, hitting across the line.",
                    0.40f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.30f -> Triple(
                "Full Power Arc",
                "Fast, uninterrupted bat acceleration through the hitting zone.",
                0.90f
            )
            gyroRatio < 1.00f -> {
                if (!warning) {
                    actionText = "Action: Swing freely through the line without tightening your shoulders."
                }
                Triple(
                    "Checked Swing",
                    "You checked your swing, losing bat speed and power into contact.",
                    0.30f
                )
            }
            else -> Triple(
                "Controlled Swing",
                "Good steady bat speed through the horizontal arc.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatDriveDefence(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -15.0f..10.0f -> {
                actionText = "Action: Great shape. Keep that relaxed tempo and let the bat flow down the ground."
                Triple(
                    "Clean Pendulum Flow",
                    "The bat swung smoothly through the line of your hands, meeting the ball right under your eyes.",
                    0.85f
                )
            }
            timeLeadMs > 10.0f -> {
                warning = true
                actionText = "Action: Lead with your front elbow and let the bat follow down the line — don't push your hands out ahead."
                Triple(
                    "Bat Lagging Behind Hands",
                    "Your hands pushed out ahead of the bat, leaving the blade trailing behind and opening the face.",
                    0.25f
                )
            }
            else -> {
                actionText = "Action: Keep your top hand firm and wait for the ball to get under your eyes before swinging through."
                Triple(
                    "Early Wrist Flick",
                    "You flicked the bat out too early, closing the blade before reaching the ball.",
                    0.35f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.15f -> Triple(
                "Crisp Bat Flow",
                "Smooth bat acceleration through the line of the ball.",
                0.85f
            )
            gyroRatio < 0.95f -> {
                if (!warning) {
                    actionText = "Action: Relax your grip and shoulders so the bat swings freely like a pendulum."
                }
                Triple(
                    "Pushed with Stiff Arms",
                    "The shot was pushed with rigid arms rather than swung with smooth bat flow.",
                    0.30f
                )
            }
            else -> Triple(
                "Controlled Downswing",
                "Balanced bat speed through the vertical line.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatPowerDrive(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -15.0f..5.0f -> {
                actionText = "Action: Great power. Finish high into your follow-through to maximize distance."
                Triple(
                    "Power Loft Timing",
                    "Bat accelerated smoothly through the ball, creating natural lift and clean power.",
                    0.90f
                )
            }
            timeLeadMs > 5.0f -> {
                warning = true
                actionText = "Action: Swing up and through the line of the ball into a high follow-through."
                Triple(
                    "Stalled Lift",
                    "Hands reached forward without bat head speed, keeping the shot grounded or mistimed.",
                    0.25f
                )
            }
            else -> {
                actionText = "Action: Hold your shape slightly longer before accelerating up through contact."
                Triple(
                    "Early Power Release",
                    "Bat released early before reaching the hitting slot, losing peak velocity.",
                    0.45f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.30f -> Triple(
                "Explosive Blade Speed",
                "High bat acceleration lifting the ball cleanly with great carry.",
                0.90f
            )
            gyroRatio < 1.05f -> {
                if (!warning) {
                    actionText = "Action: Commit to hitting through the line with full arm extension."
                }
                Triple(
                    "Under-Powered",
                    "Swing lacked bat acceleration through the ball.",
                    0.30f
                )
            }
            else -> Triple(
                "Solid Drive Speed",
                "Good positive acceleration through impact.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatCutPunch(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -10.0f..10.0f -> {
                actionText = "Action: Excellent contact point. Keep hitting down on the ball through point."
                Triple(
                    "Crisp Square Slap",
                    "Bat and hands met the ball together with sharp timing, cutting down on the ball.",
                    0.85f
                )
            }
            timeLeadMs > 10.0f -> {
                warning = true
                actionText = "Action: Wait for the ball to get closer, then snap the bat down and through."
                Triple(
                    "Bat Trailing Hands",
                    "Hands pushed toward point before the bat got there, leaving the blade face open.",
                    0.20f
                )
            }
            else -> {
                actionText = "Action: Let the ball come to you before playing the cut."
                Triple(
                    "Early Reach",
                    "Reached out too early for the ball outside off stump.",
                    0.45f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.10f -> Triple(
                "Sharp Blade Snap",
                "Fast bat acceleration through the point boundary.",
                0.85f
            )
            gyroRatio < 0.90f -> {
                if (!warning) {
                    actionText = "Action: Get on your back foot and hit firmly down through the ball."
                }
                Triple(
                    "Guarded Push",
                    "Pushed gently rather than hitting firmly through the ball.",
                    0.30f
                )
            }
            else -> Triple(
                "Controlled Cut",
                "Steady bat speed through the square drive line.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatGlanceFlick(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -15.0f..0.0f -> {
                actionText = "Action: Clean deflection. Keep working the ball off your front pad into the gaps."
                Triple(
                    "Crisp Wrist Roll",
                    "Bat timed the ball off the pads cleanly, rolling the wrists over impact.",
                    0.90f
                )
            }
            timeLeadMs > 5.0f -> {
                warning = true
                actionText = "Action: Get your bat down earlier and meet the ball in front of your front pad."
                Triple(
                    "Late Blade",
                    "Bat arrived late to the ball, risking an inside edge onto the stumps.",
                    0.20f
                )
            }
            else -> {
                actionText = "Action: Wait for the ball to reach your pad before rolling your wrists."
                Triple(
                    "Early Flick",
                    "Closed the bat face too early before ball contact.",
                    0.40f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.10f -> Triple(
                "Sharp Deflection",
                "Quick bat acceleration working the ball into the leg-side gap.",
                0.85f
            )
            gyroRatio < 0.90f -> {
                if (!warning) {
                    actionText = "Action: Work the ball off your legs with a positive roll of the bat."
                }
                Triple(
                    "Passive Touch",
                    "Bat was stationary or pushed gently without active wrist snap.",
                    0.35f
                )
            }
            else -> Triple(
                "Controlled Glance",
                "Good touch working the ball off the pads.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatDeflectionGuide(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in 10.0f..35.0f -> {
                actionText = "Action: Perfect soft touch to run the ball down to third man."
                Triple(
                    "Soft-Hand Guide",
                    "Bat relaxed naturally behind the hands to run the ball off the open face.",
                    0.85f
                )
            }
            timeLeadMs < 5.0f -> {
                warning = true
                actionText = "Action: Soften your hands and let the pace of the ball deflect off the blade."
                Triple(
                    "Pushed Hard at Ball",
                    "Pushed the bat firmly into the ball instead of letting the ball glance off the face.",
                    0.25f
                )
            }
            else -> {
                actionText = "Action: Keep your hands relaxed right through contact."
                Triple(
                    "Late Glide",
                    "Steered the ball behind square with decent timing.",
                    0.55f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio <= 0.85f -> Triple(
                "Controlled Soft Hands",
                "Great soft touch, absorbing the ball's speed to drop it into the gap.",
                0.85f
            )
            gyroRatio > 1.15f -> {
                if (!warning) {
                    actionText = "Action: Relax your grip and play with softer hands down to third man."
                }
                Triple(
                    "Swung Too Hard",
                    "Swung into the ball instead of guiding it, risking an edge to the slips.",
                    0.25f
                )
            }
            else -> Triple(
                "Firm Deflection",
                "Controlled touch behind square.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatSlog(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -20.0f..5.0f -> {
                actionText = "Action: Great aggressive swing. Keep your head still and swing through the line."
                Triple(
                    "Full Arc Commitment",
                    "The bat swung through with maximum speed and clean timing right into contact.",
                    0.90f
                )
            }
            timeLeadMs > 5.0f -> {
                warning = true
                actionText = "Action: Commit to your swing path with a full, free-flowing swing."
                Triple(
                    "Hesitant Swing",
                    "Hands drifted forward and bat lagged, losing loft and power.",
                    0.25f
                )
            }
            else -> {
                actionText = "Action: Keep your eyes on the ball and swing through its full arc."
                Triple(
                    "Rushed Swing",
                    "Swung across the line too early before the ball arrived.",
                    0.45f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.40f -> Triple(
                "High Bat Speed",
                "Fast bat acceleration through the hitting zone.",
                0.95f
            )
            gyroRatio < 1.15f -> {
                if (!warning) {
                    actionText = "Action: Keep your arms extended and swing freely through the line."
                }
                Triple(
                    "Restricted Swing",
                    "Restricted swing arc, losing power.",
                    0.30f
                )
            }
            else -> Triple(
                "Solid Power",
                "Good bat speed through the arc.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatSweep(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        var warning = false
        var actionText: String

        val (seqTitle, seqDesc, seqVal) = when {
            timeLeadMs in -15.0f..5.0f -> {
                actionText = "Action: Keep your head over your front knee and follow through along the turf."
                Triple(
                    "Clean Low Sweep",
                    "The bat swung low and level across the front knee right on time.",
                    0.85f
                )
            }
            timeLeadMs > 5.0f -> {
                warning = true
                actionText = "Action: Bring the bat through with your head and shoulders as one unit."
                Triple(
                    "Bat Trailed Body",
                    "Torso turned but the bat was left behind, hitting across the top of the ball.",
                    0.25f
                )
            }
            else -> {
                actionText = "Action: Wait for the ball to pitch before committing your blade to the sweep."
                Triple(
                    "Early Sweep",
                    "Swept early before the ball pitched.",
                    0.45f
                )
            }
        }

        val (powerTitle, powerDesc, powerVal) = when {
            gyroRatio >= 1.10f -> Triple(
                "Full Sweep Flow",
                "Solid bat flow along the horizontal plane.",
                0.85f
            )
            gyroRatio < 0.90f -> {
                if (!warning) {
                    actionText = "Action: Get down low on your front knee and swing the blade in a wide, level arc."
                }
                Triple(
                    "Arm Poke",
                    "Poked with the arms rather than sweeping cleanly.",
                    0.30f
                )
            }
            else -> Triple(
                "Controlled Sweep",
                "Good horizontal blade path across the stumps.",
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
            coachingInsight = actionText,
            displaysWarning = warning
        )
    }

    @Suppress("UNUSED_PARAMETER")
    private fun mapBatGenericFallback(timeLeadMs: Float, gyroRatio: Float, accRatio: Float): BiomechanicalUiState {
        return BiomechanicalUiState(
            sequencingTitle = "Standard Bat Flow",
            sequencingDescription = "Bat swing execution within general timing parameters.",
            sequencingSliderVal = 0.60f,
            powerPatternTitle = "Balanced Bat Speed",
            powerPatternDescription = "Standard swing acceleration through impact.",
            powerSliderVal = 0.60f,
            coachingInsight = "Action: Maintain clean head position and watch the ball onto the face of the bat.",
            displaysWarning = false
        )
    }
}
