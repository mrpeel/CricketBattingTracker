package com.mrpeel.cricketbattingtracker.analytics

import java.util.Locale

/**
 * Diagnostic fault identifiers.
 */
enum class DiagnosticFaultCode(val codeString: String) {
    FAULT_PULL_LAG("FAULT_PULL_LAG"),
    FAULT_PULL_POWER("FAULT_PULL_POWER"),
    FAULT_DRIVE_TAKEOVER("FAULT_DRIVE_TAKEOVER"),
    FAULT_CUT_ASYNC("FAULT_CUT_ASYNC"),
    FAULT_SWEEP_ARMS("FAULT_SWEEP_ARMS"),
    FAULT_FLICK_EARLY("FAULT_FLICK_EARLY")
}

/**
 * Prescriptive corrective training drill specification.
 */
data class PrescriptionDrill(
    val id: String,
    val name: String,
    val targetFaultCodes: List<DiagnosticFaultCode>,
    val setup: String,
    val execution: String,
    val biomechanicalFocus: String,
    val prescription: String
)

/**
 * Diagnostic fault report containing identified pattern, observed kinematics, quantified impact, and attached drill.
 */
data class DiagnosticFaultReport(
    val faultCode: DiagnosticFaultCode,
    val shotClass: String,
    val title: String,
    val identifiedPattern: String,
    val observedKinematics: String,
    val optimalTargetKinematics: String,
    val primaryTechnicalFlaw: String,
    val quantifiedImpact: String,
    val faultRate: Float, // % of shots in class tripping flaw condition
    val sampleCount: Int,
    val drill: PrescriptionDrill
)

/**
 * Complete diagnosis result from the [DiagnosticRulesEngine].
 */
data class DiagnosticDiagnosisResult(
    val allDetectedFaults: List<DiagnosticFaultReport>,
    val topPrimaryFlaws: List<DiagnosticFaultReport>, // Top 1-2 ranked by fault rate
    val prescribedDrills: List<PrescriptionDrill>     // Unique drills mapped to detected faults
)

/**
 * Deterministic, rule-based diagnostic engine that evaluates player-level aggregated distributions
 * against heuristic fault gates and prescribes corrective practice drills without invoking external LLMs.
 */
object DiagnosticRulesEngine {

    // ── Corrective Drill Catalogue ──

    val DRILL_PULL_TEE_SLAPS = PrescriptionDrill(
        id = "drill_pull_tee_slaps",
        name = "Single-Hand Trailing Arm Tee Slaps",
        targetFaultCodes = listOf(DiagnosticFaultCode.FAULT_PULL_LAG, DiagnosticFaultCode.FAULT_PULL_POWER),
        setup = "Batting tee placed at hip height on middle/leg stump line.",
        execution = "Grip handle with bottom hand only; start with open chest and drive the blade horizontally through the ball, exaggerating full arm extension and forearm pronation.",
        biomechanicalFocus = "Forces the bottom arm to accelerate through the hitting plane (accRatio >= 1.20) rather than acting as a passive passenger.",
        prescription = "3 sets of 12 reps before open net sessions."
    )

    val DRILL_DROP_DRIVES = PrescriptionDrill(
        id = "drill_drop_drives",
        name = "Split-Grip Top-Hand Drop Drives",
        targetFaultCodes = listOf(DiagnosticFaultCode.FAULT_DRIVE_TAKEOVER),
        setup = "Self-drop or gentle coach drop on off-stump half-volley length.",
        execution = "Position bottom hand with thumb and forefinger lightly resting against the top of the handle grip (loose \"O\" grip); execute high-elbow vertical drives down the ground.",
        biomechanicalFocus = "Neutralizes bottom-hand wrist takeover (gyroRatio target: 0.45 to 0.65) to ensure the top hand governs blade path.",
        prescription = "4 sets of 10 drives (focusing strictly on grounded straight/cover drives)."
    )

    val DRILL_WALL_PUNCH = PrescriptionDrill(
        id = "drill_wall_punch",
        name = "Lateral Isometric Wall Punch",
        targetFaultCodes = listOf(DiagnosticFaultCode.FAULT_CUT_ASYNC),
        setup = "Position stance sideways against a padded wall or firm tackle bag at point/cover-point line.",
        execution = "Take backlift and snap both wrists simultaneously into impact against the pad, holding an isometric wrist lock for 2 seconds upon contact.",
        biomechanicalFocus = "Calibrates simultaneous cross-wrist kinetic lock (synchronous -5ms <= Δt <= +5ms).",
        prescription = "3 sets of 8 holds."
    )

    val DRILL_CORE_SWEEPS = PrescriptionDrill(
        id = "drill_core_sweeps",
        name = "Medicine Ball / Heavy-Bat Core Sweeps",
        targetFaultCodes = listOf(DiagnosticFaultCode.FAULT_SWEEP_ARMS),
        setup = "Deep front-knee crouch on pitch.",
        execution = "Holding a light medicine ball or heavy training bat with both hands locked in front of torso, rotate core through the horizontal arc without letting arms extend independently.",
        biomechanicalFocus = "Couples dual-wrist movement to pelvis and thoracic rotational torque.",
        prescription = "3 sets of 10 sweeps per side."
    )

    val DRILL_PAD_CLEARANCE = PrescriptionDrill(
        id = "drill_pad_clearance",
        name = "Leading-Wrist Pad Clearance Drills",
        targetFaultCodes = listOf(DiagnosticFaultCode.FAULT_FLICK_EARLY),
        setup = "Coach drop or bowling machine on middle/leg stump half-volley.",
        execution = "Hold wrist cock until bat reaches front pad line before releasing bottom-wrist snap through mid-wicket.",
        biomechanicalFocus = "Delays wrist turnover until the exact impact plane (-15ms <= Δt <= -5ms) with active pronation (gyroRatio >= 1.00).",
        prescription = "3 sets of 12 flicks."
    )

    val ALL_CATALOGUE_DRILLS = listOf(
        DRILL_PULL_TEE_SLAPS,
        DRILL_DROP_DRIVES,
        DRILL_WALL_PUNCH,
        DRILL_CORE_SWEEPS,
        DRILL_PAD_CLEARANCE
    )

    /**
     * Evaluates all statistical profiles in the [LongitudinalAggregationResult] against the heuristic trigger matrix.
     */
    fun diagnose(aggregation: LongitudinalAggregationResult): DiagnosticDiagnosisResult {
        val detectedFaults = mutableListOf<DiagnosticFaultReport>()

        for ((shotClass, profile) in aggregation.classProfiles) {
            when (shotClass) {
                "PULL/HOOK" -> {
                    checkPullLag(profile)?.let { detectedFaults.add(it) }
                    checkPullPower(profile)?.let { detectedFaults.add(it) }
                }
                "DRIVE/DEFENCE" -> {
                    checkDriveTakeover(profile)?.let { detectedFaults.add(it) }
                }
                "CUT/PUNCH" -> {
                    checkCutAsync(profile)?.let { detectedFaults.add(it) }
                }
                "SWEEP" -> {
                    checkSweepArms(profile)?.let { detectedFaults.add(it) }
                }
                "GLANCE/FLICK" -> {
                    checkFlickEarly(profile)?.let { detectedFaults.add(it) }
                }
            }
        }

        // Rank detected faults by fault rate descending (severity)
        val sortedFaults = detectedFaults.sortedByDescending { it.faultRate }
        val topPrimaryFlaws = sortedFaults.take(2)

        // Deduplicate drills preserved in order of fault priority
        val prescribedDrills = sortedFaults.map { it.drill }.distinctBy { it.id }

        return DiagnosticDiagnosisResult(
            allDetectedFaults = sortedFaults,
            topPrimaryFlaws = topPrimaryFlaws,
            prescribedDrills = prescribedDrills
        )
    }

    /**
     * FAULT_PULL_LAG: Chronically Dragged Blade on Pull
     * Trigger: PULL/HOOK: Median timeLeadMs > +10ms OR >40% shots with timeLeadMs > 0ms
     */
    fun checkPullLag(profile: ShotClassStatisticalProfile): DiagnosticFaultReport? {
        val medianLead = profile.timeLeadDistribution.median
        val positiveLagCount = profile.rawTimeLeads.count { it > 0f }
        val positiveLagRate = (positiveLagCount.toFloat() / profile.sampleCount.toFloat()) * 100f

        val isTriggered = medianLead > 10f || positiveLagRate > 40f
        if (!isTriggered) return null

        val faultRate = if (medianLead > 10f) {
            val trippedCount = profile.rawTimeLeads.count { it > 10f }
            ((trippedCount.toFloat() / profile.sampleCount.toFloat()) * 100f).coerceAtLeast(positiveLagRate)
        } else {
            positiveLagRate
        }

        val observedStr = if (medianLead >= 0) "+${medianLead.toInt()}ms" else "${medianLead.toInt()}ms"
        val observedKinematics = "Median Lag: $observedStr ($positiveLagRate.toInt()% of shots lagging > 0ms)"

        return DiagnosticFaultReport(
            faultCode = DiagnosticFaultCode.FAULT_PULL_LAG,
            shotClass = profile.shotClass,
            title = "Chronically Dragged Blade on Pull",
            identifiedPattern = "Persistent Dragged Blade on Pull Shots",
            observedKinematics = observedKinematics,
            optimalTargetKinematics = "Optimal Hand Timing: -30ms to -10ms active snap lead",
            primaryTechnicalFlaw = "Bat face trails shoulders; bottom hand fails to clear arc ahead of turnover.",
            quantifiedImpact = "+12 to 18 km/h bat speed & lower aerial mistime risk by snapping into [-30ms, -10ms] window.",
            faultRate = faultRate,
            sampleCount = profile.sampleCount,
            drill = DRILL_PULL_TEE_SLAPS
        )
    }

    /**
     * FAULT_PULL_POWER: Insufficient Bottom-Hand Linear Punch
     * Trigger: PULL/HOOK: Median accRatio < 1.00
     */
    fun checkPullPower(profile: ShotClassStatisticalProfile): DiagnosticFaultReport? {
        val medianAcc = profile.accRatioDistribution.median
        if (medianAcc >= 1.00f) return null

        val subOneCount = profile.rawAccRatios.count { it < 1.00f }
        val faultRate = (subOneCount.toFloat() / profile.sampleCount.toFloat()) * 100f

        val observedKinematics = String.format(Locale.US, "Median Accel Ratio: %.2fx (Optimal >= 1.20x)", medianAcc)

        return DiagnosticFaultReport(
            faultCode = DiagnosticFaultCode.FAULT_PULL_POWER,
            shotClass = profile.shotClass,
            title = "Insufficient Bottom-Hand Linear Punch",
            identifiedPattern = "Passive Trailing Bottom Arm on Pull Shots",
            observedKinematics = observedKinematics,
            optimalTargetKinematics = "Optimal Acceleration Ratio: >= 1.20x linear punch",
            primaryTechnicalFlaw = "Trailing arm fails to punch horizontally through contact.",
            quantifiedImpact = "+15% exit velocity via active linear arm punch (a_ratio >= 1.20).",
            faultRate = faultRate,
            sampleCount = profile.sampleCount,
            drill = DRILL_PULL_TEE_SLAPS
        )
    }

    /**
     * FAULT_DRIVE_TAKEOVER: Bottom-Hand Takeover on Drives
     * Trigger: DRIVE/DEFENCE: Median gyroRatio > 0.75 OR >30% shots with gyroRatio > 0.85
     */
    fun checkDriveTakeover(profile: ShotClassStatisticalProfile): DiagnosticFaultReport? {
        val medianGyro = profile.gyroRatioDistribution.median
        val highGyroCount = profile.rawGyroRatios.count { it > 0.85f }
        val highGyroRate = (highGyroCount.toFloat() / profile.sampleCount.toFloat()) * 100f

        val isTriggered = medianGyro > 0.75f || highGyroRate > 30f
        if (!isTriggered) return null

        val faultRate = if (medianGyro > 0.75f) {
            val tripped = profile.rawGyroRatios.count { it > 0.75f }
            ((tripped.toFloat() / profile.sampleCount.toFloat()) * 100f).coerceAtLeast(highGyroRate)
        } else {
            highGyroRate
        }

        val observedKinematics = String.format(
            Locale.US,
            "Median Gyro Ratio: %.2fx (%.0f%% shots choking > 0.85x)",
            medianGyro,
            highGyroRate
        )

        return DiagnosticFaultReport(
            faultCode = DiagnosticFaultCode.FAULT_DRIVE_TAKEOVER,
            shotClass = profile.shotClass,
            title = "Bottom-Hand Takeover on Drives",
            identifiedPattern = "Dominant Bottom Wrist Overpowering Vertical Drives",
            observedKinematics = observedKinematics,
            optimalTargetKinematics = "Optimal Gyro Ratio: 0.45x to 0.65x (Passive Top-Hand Guide)",
            primaryTechnicalFlaw = "Bottom hand chokes downswing, forcing closed face and high aerial risk.",
            quantifiedImpact = "Increases grounded wagon-wheel placement control by +25%; stabilizes vertical downswing plane.",
            faultRate = faultRate,
            sampleCount = profile.sampleCount,
            drill = DRILL_DROP_DRIVES
        )
    }

    /**
     * FAULT_CUT_ASYNC: Delayed Bottom-Wrist Lock on Cut
     * Trigger: CUT/PUNCH: Median timeLeadMs > +10ms OR accRatio < 0.75
     */
    fun checkCutAsync(profile: ShotClassStatisticalProfile): DiagnosticFaultReport? {
        val medianLead = profile.timeLeadDistribution.median
        val medianAcc = profile.accRatioDistribution.median

        val isTriggered = medianLead > 10f || medianAcc < 0.75f
        if (!isTriggered) return null

        val trippedCount = profile.rawTimeLeads.indices.count { idx ->
            profile.rawTimeLeads[idx] > 10f || profile.rawAccRatios[idx] < 0.75f
        }
        val faultRate = (trippedCount.toFloat() / profile.sampleCount.toFloat()) * 100f

        val leadStr = if (medianLead >= 0) "+${medianLead.toInt()}ms" else "${medianLead.toInt()}ms"
        val observedKinematics = String.format(
            Locale.US,
            "Median Lag: %s, Accel Ratio: %.2fx (Optimal: ±5ms, >= 0.85x)",
            leadStr,
            medianAcc
        )

        return DiagnosticFaultReport(
            faultCode = DiagnosticFaultCode.FAULT_CUT_ASYNC,
            shotClass = profile.shotClass,
            title = "Delayed Bottom-Wrist Lock on Cut",
            identifiedPattern = "Asynchronous Dual-Wrist Lock on Cut Shots",
            observedKinematics = observedKinematics,
            optimalTargetKinematics = "Optimal Timing: -5ms to +5ms synchronous lock (accRatio >= 0.85x)",
            primaryTechnicalFlaw = "Hands disconnect at impact; blade face trails lateral punch plane.",
            quantifiedImpact = "Prevents open-face edges; increases square punching power by +10 km/h.",
            faultRate = faultRate,
            sampleCount = profile.sampleCount,
            drill = DRILL_WALL_PUNCH
        )
    }

    /**
     * FAULT_SWEEP_ARMS: Arm-Dominated Sweep Rotation
     * Trigger: SWEEP: Median accRatio < 0.80 OR timeLeadMs > +12ms
     */
    fun checkSweepArms(profile: ShotClassStatisticalProfile): DiagnosticFaultReport? {
        val medianAcc = profile.accRatioDistribution.median
        val medianLead = profile.timeLeadDistribution.median

        val isTriggered = medianAcc < 0.80f || medianLead > 12f
        if (!isTriggered) return null

        val trippedCount = profile.rawAccRatios.indices.count { idx ->
            profile.rawAccRatios[idx] < 0.80f || profile.rawTimeLeads[idx] > 12f
        }
        val faultRate = (trippedCount.toFloat() / profile.sampleCount.toFloat()) * 100f

        val leadStr = if (medianLead >= 0) "+${medianLead.toInt()}ms" else "${medianLead.toInt()}ms"
        val observedKinematics = String.format(
            Locale.US,
            "Median Accel Ratio: %.2fx, Lag: %s (Optimal: 0.90x–1.20x, <= +5ms)",
            medianAcc,
            leadStr
        )

        return DiagnosticFaultReport(
            faultCode = DiagnosticFaultCode.FAULT_SWEEP_ARMS,
            shotClass = profile.shotClass,
            title = "Arm-Dominated Sweep Rotation",
            identifiedPattern = "Uncoupled Arm Drag on Sweep Strokes",
            observedKinematics = observedKinematics,
            optimalTargetKinematics = "Optimal Rotation: Accel Ratio >= 0.90x linked to torso torque",
            primaryTechnicalFlaw = "Arms dragging independently rather than linking to core torso turn.",
            quantifiedImpact = "Enhances ball-striking consistency and placement torque across front knee.",
            faultRate = faultRate,
            sampleCount = profile.sampleCount,
            drill = DRILL_CORE_SWEEPS
        )
    }

    /**
     * FAULT_FLICK_EARLY: Premature Wrist Roll on Flick
     * Trigger: GLANCE/FLICK: Median timeLeadMs < -20ms OR gyroRatio < 1.00
     */
    fun checkFlickEarly(profile: ShotClassStatisticalProfile): DiagnosticFaultReport? {
        val medianLead = profile.timeLeadDistribution.median
        val medianGyro = profile.gyroRatioDistribution.median

        val isTriggered = medianLead < -20f || medianGyro < 1.00f
        if (!isTriggered) return null

        val trippedCount = profile.rawTimeLeads.indices.count { idx ->
            profile.rawTimeLeads[idx] < -20f || profile.rawGyroRatios[idx] < 1.00f
        }
        val faultRate = (trippedCount.toFloat() / profile.sampleCount.toFloat()) * 100f

        val leadStr = "${medianLead.toInt()}ms"
        val observedKinematics = String.format(
            Locale.US,
            "Median Lead: %s, Gyro Ratio: %.2fx (Optimal: -15ms to -5ms, >= 1.20x)",
            leadStr,
            medianGyro
        )

        return DiagnosticFaultReport(
            faultCode = DiagnosticFaultCode.FAULT_FLICK_EARLY,
            shotClass = profile.shotClass,
            title = "Premature Wrist Roll on Flick",
            identifiedPattern = "Early Wrist Roll Closing Blade on Pad Flicks",
            observedKinematics = observedKinematics,
            optimalTargetKinematics = "Optimal Timing: -15ms to -5ms wrist snap (gyroRatio >= 1.20x)",
            primaryTechnicalFlaw = "Premature wrist roll closing blade before impact line.",
            quantifiedImpact = "Sharpens pad-clearance angle; eliminates leading-edge risks to mid-on.",
            faultRate = faultRate,
            sampleCount = profile.sampleCount,
            drill = DRILL_PAD_CLEARANCE
        )
    }
}
