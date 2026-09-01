package com.mrpeel.cricketbattingtracker.analytics

import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.normalizeShotType
import com.mrpeel.cricketbattingtracker.ui.biomechanics.BiomechanicalUiMapper
import java.util.Locale
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * Statistical distribution container representing a single biomechanical metric array.
 */
data class MetricDistribution(
    val count: Int,
    val median: Float,        // P50
    val p25: Float,           // 25th percentile (Q1)
    val p75: Float,           // 75th percentile (Q3)
    val mean: Float,          // Arithmetic Mean (mu)
    val stdDev: Float,        // Standard Deviation (sigma)
    val min: Float,
    val max: Float
) {
    val iqr: Float get() = (p75 - p25).coerceAtLeast(0f)
}

/**
 * Statistical profile aggregated across all logged shots for a specific canonical shot class with N >= 5.
 */
data class ShotClassStatisticalProfile(
    val shotClass: String,
    val sampleCount: Int,               // Total shots evaluated across repertoire (e.g. 1,200)
    val dualSensorSampleCount: Int,     // Shots with dual-sensor telemetry (e.g. 850)
    val percentageOfRepertoire: Float,  // sampleCount / totalShots * 100f
    val batSpeedMax: Float,            // km/h
    val batSpeedP80: Float,            // 80th percentile km/h
    val batSpeedMedian: Float,         // P50 km/h
    val batSpeedMin: Float,            // km/h
    val efficiencyP80: Float,          // 80th percentile %
    val efficiencyMean: Float,         // %
    val efficiencyMedian: Float,       // %
    val timeLeadDistribution: MetricDistribution,
    val gyroRatioDistribution: MetricDistribution,
    val accRatioDistribution: MetricDistribution,
    val amberFaultRate: Float, // 0.0f - 100.0f (% of dual shots tripping execution fault conditions)
    val timingTrait: String,
    val angularTrait: String,
    val linearTrait: String,
    val keyTechnicalObservation: String,
    val rawTimeLeads: List<Float>,
    val rawGyroRatios: List<Float>,
    val rawAccRatios: List<Float>
) {
    val hasSufficientDualData: Boolean get() = dualSensorSampleCount >= BiomechanicsAggregator.MIN_SHOTS_PER_CLASS_THRESHOLD
}

/**
 * Complete longitudinal aggregation result across all stored sessions.
 */
data class LongitudinalAggregationResult(
    val totalShots: Int,
    val totalDualSensorShots: Int,
    val totalSessionsAnalyzed: Int,
    val totalDualSessionsAnalyzed: Int,
    val coordinationHealthScore: Int, // 0 to 100 weighted percentage matching optimal windows
    val classProfiles: Map<String, ShotClassStatisticalProfile>, // Classes with N >= 5
    val insufficientDataClasses: Map<String, Int>, // Classes with 1 <= N < 5 (class -> count)
    val shotFamilyDistribution: Map<String, Int>, // All canonical shot classes -> count
    val validDualSensorEvents: List<InningsEvent>
)

/**
 * Aggregates cross-sensor hand coordination metrics (timeLeadMs, gyroRatio, accRatio)
 * and speed/efficiency telemetry across all stored batting sessions.
 */
object BiomechanicsAggregator {

    const val MIN_SHOTS_PER_CLASS_THRESHOLD = 5

    val CANONICAL_TAXONOMY = listOf(
        "DRIVE/DEFENCE",
        "PULL/HOOK",
        "CUT/PUNCH",
        "GLANCE/FLICK",
        "DEFLECTION/GUIDE",
        "POWER DRIVE",
        "SLOG",
        "SWEEP"
    )

    /**
     * Determines whether an InningsEvent represents a valid batting stroke (excluding non-batting setup events).
     */
    fun isBattingShot(event: InningsEvent): Boolean {
        val shot = event.shotType
        if (shot.isNullOrBlank()) {
            return event.batSpeed != null && event.batSpeed > 0f
        }
        val lower = shot.lowercase()
        if (lower.contains("facing up") || lower.contains("no shot") || lower.contains("leave") ||
            lower.contains("session started") || lower.contains("session ended")) {
            return false
        }
        return true
    }

    /**
     * Determines whether an InningsEvent contains a valid dual-sensor (Watch + Polar) payload.
     * Single-hand / watch-only sessions where bottom-hand telemetry is absent or zeroed are filtered out.
     */
    fun hasDualSensor(event: InningsEvent): Boolean {
        val gyro = event.bottom_hand_gyro_ratio
        val acc = event.bottom_hand_acc_ratio
        val timeLead = event.bottom_hand_time_lead_ms

        if (gyro == null || acc == null || timeLead == null) return false
        // Exclude zeroed placeholders from watch-only sessions
        if (gyro == 0f && acc == 0f && timeLead == 0L) return false

        return true
    }

    /**
     * Aggregate all events across all sessions and produce a [LongitudinalAggregationResult].
     */
    fun aggregate(events: List<InningsEvent>): LongitudinalAggregationResult {
        val allBattingShots = events.filter { isBattingShot(it) }
        val dualSensorEvents = allBattingShots.filter { hasDualSensor(it) }
        val totalSessions = allBattingShots.map { it.inningsId }.distinct().size
        val dualSessions = dualSensorEvents.map { it.inningsId }.distinct().size

        if (allBattingShots.isEmpty()) {
            return LongitudinalAggregationResult(
                totalShots = 0,
                totalDualSensorShots = 0,
                totalSessionsAnalyzed = 0,
                totalDualSessionsAnalyzed = 0,
                coordinationHealthScore = 100,
                classProfiles = emptyMap(),
                insufficientDataClasses = emptyMap(),
                shotFamilyDistribution = CANONICAL_TAXONOMY.associateWith { 0 },
                validDualSensorEvents = emptyList()
            )
        }

        val totalShotsCount = allBattingShots.size
        val totalDualShotsCount = dualSensorEvents.size

        // Group shots by canonical biomechanical taxonomy
        val groupedByCanonical = allBattingShots.groupBy { normalizeShotType(it.shotType) }

        val shotFamilyDistribution = CANONICAL_TAXONOMY.associateWith { canonical ->
            groupedByCanonical[canonical]?.size ?: 0
        }

        val classProfiles = mutableMapOf<String, ShotClassStatisticalProfile>()
        val insufficientDataClasses = mutableMapOf<String, Int>()

        var totalAmberWarningShots = 0
        var totalEvaluatedDualShots = 0

        for ((shotClass, classEvents) in groupedByCanonical) {
            val count = classEvents.size
            if (count < MIN_SHOTS_PER_CLASS_THRESHOLD) {
                insufficientDataClasses[shotClass] = count
                continue
            }

            val dualClassEvents = classEvents.filter { hasDualSensor(it) }
            val dualCount = dualClassEvents.size

            // Bat speed metrics computed across ALL shots in this class
            val speeds = classEvents.mapNotNull { it.batSpeed }.filter { it > 0f }.sorted()
            val speedMax = if (speeds.isNotEmpty()) speeds.last() else 0f
            val speedP80 = if (speeds.isNotEmpty()) computePercentile(speeds, 0.80f) else 0f
            val speedMedian = if (speeds.isNotEmpty()) computePercentile(speeds, 0.50f) else 0f
            val speedMin = if (speeds.isNotEmpty()) speeds.first() else 0f

            // Efficiency metrics computed across ALL shots in this class
            val effs = classEvents.mapNotNull { it.efficiency }.filter { it > 0f }.sorted()
            val effP80 = if (effs.isNotEmpty()) computePercentile(effs, 0.80f) else 0f
            val effMean = if (effs.isNotEmpty()) effs.sum() / effs.size.toFloat() else 0f
            val effMedian = if (effs.isNotEmpty()) computePercentile(effs, 0.50f) else 0f

            val percentageOfRepertoire = (count.toFloat() / totalShotsCount.toFloat()) * 100f

            val timeLeads = dualClassEvents.mapNotNull { it.bottom_hand_time_lead_ms?.toFloat() }
            val gyroRatios = dualClassEvents.mapNotNull { it.bottom_hand_gyro_ratio }
            val accRatios = dualClassEvents.mapNotNull { it.bottom_hand_acc_ratio }

            val timeDist = computeDistribution(timeLeads) ?: MetricDistribution(0, 0f, 0f, 0f, 0f, 0f, 0f, 0f)
            val gyroDist = computeDistribution(gyroRatios) ?: MetricDistribution(0, 0f, 0f, 0f, 0f, 0f, 0f, 0f)
            val accDist = computeDistribution(accRatios) ?: MetricDistribution(0, 0f, 0f, 0f, 0f, 0f, 0f, 0f)

            var classWarnings = 0
            for (event in dualClassEvents) {
                val tl = event.bottom_hand_time_lead_ms?.toFloat() ?: 0f
                val gr = event.bottom_hand_gyro_ratio ?: 0f
                val ar = event.bottom_hand_acc_ratio ?: 0f
                if (BiomechanicalUiMapper.mapToUiState(shotClass, tl, gr, ar).displaysWarning) {
                    classWarnings++
                }
            }

            totalAmberWarningShots += classWarnings
            totalEvaluatedDualShots += dualCount
            val faultRate = if (dualCount > 0) (classWarnings.toFloat() / dualCount.toFloat()) * 100f else 0f

            val timingTrait = if (dualCount >= MIN_SHOTS_PER_CLASS_THRESHOLD) {
                determineTimingTrait(timeDist.median, timeDist.iqr)
            } else {
                "Dual-Sensor Tracking ($dualCount/5 calibrated)"
            }

            val angularTrait = if (dualCount >= MIN_SHOTS_PER_CLASS_THRESHOLD) {
                determineAngularTrait(gyroDist.median)
            } else {
                "Top-Hand Steer Tracked"
            }

            val linearTrait = if (dualCount >= MIN_SHOTS_PER_CLASS_THRESHOLD) {
                determineLinearTrait(accDist.median)
            } else {
                "Linear Force Tracked"
            }

            val technicalObservation = generateTechnicalObservation(
                shotClass = shotClass,
                sampleCount = count,
                batSpeedP80 = if (speedP80 > 0f) speedP80 else speedMax,
                efficiencyP80 = if (effP80 > 0f) effP80 else effMean,
                medianLead = if (dualCount > 0) timeDist.median else 0f,
                medianGyro = if (dualCount > 0) gyroDist.median else 0.5f,
                medianAcc = if (dualCount > 0) accDist.median else 1.0f
            )

            classProfiles[shotClass] = ShotClassStatisticalProfile(
                shotClass = shotClass,
                sampleCount = count,
                dualSensorSampleCount = dualCount,
                percentageOfRepertoire = percentageOfRepertoire,
                batSpeedMax = speedMax,
                batSpeedP80 = speedP80,
                batSpeedMedian = speedMedian,
                batSpeedMin = speedMin,
                efficiencyP80 = effP80,
                efficiencyMean = effMean,
                efficiencyMedian = effMedian,
                timeLeadDistribution = timeDist,
                gyroRatioDistribution = gyroDist,
                accRatioDistribution = accDist,
                amberFaultRate = faultRate,
                timingTrait = timingTrait,
                angularTrait = angularTrait,
                linearTrait = linearTrait,
                keyTechnicalObservation = technicalObservation,
                rawTimeLeads = timeLeads,
                rawGyroRatios = gyroRatios,
                rawAccRatios = accRatios
            )
        }

        val optimalShots = (totalEvaluatedDualShots - totalAmberWarningShots).coerceAtLeast(0)
        val healthScore = if (totalEvaluatedDualShots > 0) {
            ((optimalShots.toFloat() / totalEvaluatedDualShots.toFloat()) * 100f).roundToInt().coerceIn(0, 100)
        } else {
            100
        }

        return LongitudinalAggregationResult(
            totalShots = totalShotsCount,
            totalDualSensorShots = totalDualShotsCount,
            totalSessionsAnalyzed = totalSessions,
            totalDualSessionsAnalyzed = dualSessions,
            coordinationHealthScore = healthScore,
            classProfiles = classProfiles,
            insufficientDataClasses = insufficientDataClasses,
            shotFamilyDistribution = shotFamilyDistribution,
            validDualSensorEvents = dualSensorEvents
        )
    }

    /**
     * Compute statistical distribution (Median, P25, P75, Mean, StdDev, Min, Max).
     */
    fun computeDistribution(values: List<Float>): MetricDistribution? {
        if (values.isEmpty()) return null
        val sorted = values.sorted()
        val n = sorted.size

        val median = computePercentile(sorted, 0.50f)
        val p25 = computePercentile(sorted, 0.25f)
        val p75 = computePercentile(sorted, 0.75f)

        val mean = sorted.sum() / n.toFloat()
        val variance = sorted.map { val diff = it - mean; diff * diff }.sum() / n.toFloat()
        val stdDev = sqrt(variance)

        return MetricDistribution(
            count = n,
            median = median,
            p25 = p25,
            p75 = p75,
            mean = mean,
            stdDev = stdDev,
            min = sorted.first(),
            max = sorted.last()
        )
    }

    /**
     * Compute percentile with linear interpolation on a sorted list.
     */
    fun computePercentile(sorted: List<Float>, percentile: Float): Float {
        if (sorted.isEmpty()) return 0f
        if (sorted.size == 1) return sorted[0]
        if (percentile <= 0f) return sorted.first()
        if (percentile >= 1f) return sorted.last()

        val index = percentile * (sorted.size - 1)
        val lowerIndex = index.toInt()
        val upperIndex = (lowerIndex + 1).coerceAtMost(sorted.size - 1)
        val fraction = index - lowerIndex

        return sorted[lowerIndex] + fraction * (sorted[upperIndex] - sorted[lowerIndex])
    }

    /**
     * Qualitative timing signature classification.
     */
    fun determineTimingTrait(medianLead: Float, iqr: Float): String {
        val consistencyTag = if (iqr in 0.01f..25f) " • High Consistency" else ""
        return when {
            medianLead < -15f -> "Early Bottom-Hand Lead (${medianLead.toInt()}ms)$consistencyTag"
            medianLead in -15f..15f -> "Synchronous Two-Hand Lock (${if (medianLead >= 0) "+" else ""}${medianLead.toInt()}ms)$consistencyTag"
            medianLead in 15.01f..60f -> "Controlled Trailing Hand (+${medianLead.toInt()}ms)$consistencyTag"
            else -> "Lagged Bottom-Hand Entry (+${medianLead.toInt()}ms)$consistencyTag"
        }
    }

    /**
     * Qualitative wrist angular rotation dominance classification.
     */
    fun determineAngularTrait(medianGyro: Float): String {
        return when {
            medianGyro < 0.25f -> String.format(Locale.US, "Strong Top-Hand Lever (%.2fx)", medianGyro)
            medianGyro in 0.25f..0.75f -> String.format(Locale.US, "Top-Hand Controlled Steer (%.2fx)", medianGyro)
            medianGyro in 0.7501f..1.20f -> String.format(Locale.US, "Balanced Two-Hand Rotation (%.2fx)", medianGyro)
            else -> String.format(Locale.US, "Bottom-Hand Dominated Whip (%.2fx)", medianGyro)
        }
    }

    /**
     * Qualitative linear acceleration punch classification.
     */
    fun determineLinearTrait(medianAcc: Float): String {
        return when {
            medianAcc >= 1.25f -> String.format(Locale.US, "Explosive Bottom-Hand Punch (%.2fx)", medianAcc)
            medianAcc in 0.75f..1.249f -> String.format(Locale.US, "Balanced Linear Drive (%.2fx)", medianAcc)
            else -> String.format(Locale.US, "Lead-Arm Steer (%.2fx)", medianAcc)
        }
    }

    /**
     * Generates a concrete, human-readable takeaway summarizing what was observed across all shots in this stroke family.
     */
    fun generateTechnicalObservation(
        shotClass: String,
        sampleCount: Int,
        batSpeedP80: Float,
        efficiencyP80: Float,
        medianLead: Float,
        medianGyro: Float,
        medianAcc: Float
    ): String {
        return when (shotClass) {
            "DRIVE/DEFENCE" -> {
                if (medianGyro <= 0.75f) {
                    String.format(
                        Locale.US,
                        "Top-hand dominant steering (%.2fx wrist ratio) with high downswing consistency. Produces grounded wagon-wheel placement with %d km/h 80th-percentile bat speed and %d%% efficiency.",
                        medianGyro, batSpeedP80.roundToInt(), efficiencyP80.roundToInt()
                    )
                } else {
                    String.format(
                        Locale.US,
                        "Bottom-hand takeover pattern (%.2fx wrist ratio). High power throughput (%d km/h P80 speed), but elevated risk of pushing downswing plane into aerial loft.",
                        medianGyro, batSpeedP80.roundToInt()
                    )
                }
            }
            "PULL/HOOK" -> {
                if (medianLead <= 0f) {
                    String.format(
                        Locale.US,
                        "Explosive rotational power with early bottom-hand punch (%.2fx force ratio). Generates high exit velocity with %d km/h 80th-percentile speed.",
                        medianAcc, batSpeedP80.roundToInt()
                    )
                } else {
                    String.format(
                        Locale.US,
                        "Strong top-hand lever (%.2fx wrist ratio), but trailing bottom hand lags by +%dms into impact. Linking the bottom-hand punch earlier unlocks higher exit velocity.",
                        medianGyro, medianLead.toInt()
                    )
                }
            }
            "CUT/PUNCH" -> {
                String.format(
                    Locale.US,
                    "Square blade presentation with balanced force ratio (%.2fx). Delivers %d km/h 80th-percentile speed and %d%% efficiency across lateral back-foot punches.",
                    medianAcc, batSpeedP80.roundToInt(), efficiencyP80.roundToInt()
                )
            }
            "GLANCE/FLICK" -> {
                String.format(
                    Locale.US,
                    "Snappy wrist roll with %d km/h 80th-percentile bat speed and %d%% efficiency across pad-line deflections.",
                    batSpeedP80.roundToInt(), efficiencyP80.roundToInt()
                )
            }
            "DEFLECTION/GUIDE" -> {
                String.format(
                    Locale.US,
                    "Soft-hands steering with controlled guide speed (%d km/h P80) and disciplined blade damping.",
                    batSpeedP80.roundToInt()
                )
            }
            "POWER DRIVE" -> {
                String.format(
                    Locale.US,
                    "Aggressive two-hand acceleration delivering %d km/h peak bat speed with %d%% 80th-percentile contact efficiency.",
                    batSpeedP80.roundToInt(), efficiencyP80.roundToInt()
                )
            }
            "SWEEP" -> {
                if (medianAcc < 0.80f || medianLead > 12f) {
                    String.format(
                        Locale.US,
                        "Arm-dominated sweep extension with %d km/h bat speed. Driving rotational torque from the core rather than isolated arms increases ball placement power.",
                        batSpeedP80.roundToInt()
                    )
                } else {
                    String.format(
                        Locale.US,
                        "Torso-connected sweep rotation with %d km/h 80th-percentile bat speed and balanced linear force (%.2fx).",
                        medianAcc, batSpeedP80.roundToInt()
                    )
                }
            }
            "SLOG" -> {
                String.format(
                    Locale.US,
                    "Maximum velocity stroke with %d km/h peak bat speed and explosive bottom-hand rotational release.",
                    batSpeedP80.roundToInt()
                )
            }
            else -> {
                String.format(
                    Locale.US,
                    "Consistent stroke delivery across %d tracked shots with %d km/h 80th-percentile bat speed.",
                    sampleCount, batSpeedP80.roundToInt()
                )
            }
        }
    }
}
