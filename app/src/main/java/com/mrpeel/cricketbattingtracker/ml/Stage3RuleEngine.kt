package com.mrpeel.cricketbattingtracker.ml

import android.content.Context
import org.json.JSONObject
import kotlin.math.*

/**
 * Stage3RuleEngine — Shared Stage 3 Post-Classification Rule Engine (Python <-> Kotlin Parity).
 *
 * Driven by `assets/models/stage3_rules_config.json` (synced with `pipelines/stage3_rules_config.json`).
 * Implements:
 *   1. Closed-form hierarchical probability recovery (`recoverHierarchicalProbs`) from the
 *      9-class Stage 2 TCN output vector `qMid`.
 *   2. Pre-AHRS candidate feature extraction (`extractPreAhrsFeatures`) from the 28-channel
 *      423 Hz sensorMatrix (using `sensorMatrix[14]` = `w_grav_z` for impact gravity Z).
 *   3. Pre-AHRS rule evaluation (`applyPreAhrsRules`) for `TcnModelRunner.kt` and Post-AHRS rule
 *      evaluation (`applyPostAhrsRules`) for `PhoneSwingDetector.kt`, plus unified `applyAllRules`
 *      matching `pipelines/stage3_rules.py::apply_stage3_rules`.
 */
object Stage3RuleEngine {

    data class HierarchicalProbs(
        val pNoShot: Float = 0f,
        val pIsShot: Float = 1f,
        val pFamVert: Float = 0f,
        val pFamCross: Float = 0f,
        val pFamSweep: Float = 0f,
        val pSub0Drive: Float = 0f,
        val pSub0Pd: Float = 0f,
        val pSub0Glance: Float = 0f,
        val pSub0Defl: Float = 0f,
        val pSub1Pull: Float = 0f,
        val pSub1Cut: Float = 0f
    )

    data class Stage3Features(
        val deltaGz: Float = 0f,
        val deltaPitch: Float = 0f,
        val omegaRoll: Float = 0f,
        val impGz: Float = 6.0f,
        val postImpactAccRatio: Float = 1.0f,
        val hasPolar: Boolean = false,
        val watchPitchDeg: Float? = null,
        val ahrsValid: Boolean = false,
        val ahrsBladePitchDeg: Float? = null,
        val ahrsFaceRollDeg: Float? = null,
        val ahrsSwingYawDeg: Float? = null,
        val batGzMin: Float = 0f,
        val bottomHandTimeLeadMs: Float = 0f
    )

    data class SweepDualPathGateConfig(
        val enabled: Boolean = true,
        val path1DeltaPitchDeg: Float = 10.0f,
        val path1DeltaGzMs2: Float = 1.2f,
        val path1MinProb: Float = 0.30f,
        val path2MinRollRads: Float = 1.6f,
        val path2MinProb: Float = 0.35f
    )

    data class NonBatSweepToGlanceConfig(
        val enabled: Boolean = false,
        val minSub0Glance: Float = 0.55f,
        val maxImpGzMs2: Float = 5.5f,
        val maxFamSweep: Float = 0.72f,
        val maxCrouchDeltaGzMs2: Float = 1.2f
    )

    data class BatVerticalGuardRule1Config(
        val enabled: Boolean = true,
        val minWatchPitchDeg: Float = 65.0f,
        val powerDrivePostRatio: Float = 1.35f
    )

    data class BatAhrsGlanceRule2Config(
        val enabled: Boolean = true,
        val yawDegPath1: Float = -17.0f,
        val batGzMinPath1: Float = -11.5f,
        val minSub0GlancePath1: Float = 0.35f,
        val yawDegPath2: Float = -50.0f,
        val minSub0GlancePath2: Float = 0.50f
    )

    data class S1AhrsFlatBatConfig(
        val enabled: Boolean = false,
        val maxBladePitchDeg: Float = 20.0f,
        val minPostImpactRatioPull: Float = 0.65f,
        val maxYawDegGlance: Float = -20.0f
    )

    data class S2PowerDriveVsPullConfig(
        val enabled: Boolean = false,
        val minFamCross: Float = 0.55f,
        val minSub1Pull: Float = 0.75f,
        val maxBladePitchDeg: Float = 35.0f
    )

    data class S3CutPunchRecoveryConfig(
        val enabled: Boolean = false,
        val minSub1Cut: Float = 0.65f,
        val maxAbsTimeLeadMs: Float = 15.0f,
        val minFamCross: Float = 0.30f
    )

    data class Stage3Config(
        val version: String = "1.1.0",
        val sweepDualPathGate: SweepDualPathGateConfig = SweepDualPathGateConfig(),
        val nonBatSweepToGlance: NonBatSweepToGlanceConfig = NonBatSweepToGlanceConfig(),
        val batVerticalGuardRule1: BatVerticalGuardRule1Config = BatVerticalGuardRule1Config(),
        val batAhrsGlanceRule2: BatAhrsGlanceRule2Config = BatAhrsGlanceRule2Config(),
        val s1AhrsFlatBat: S1AhrsFlatBatConfig = S1AhrsFlatBatConfig(),
        val s2PowerDriveVsPull: S2PowerDriveVsPullConfig = S2PowerDriveVsPullConfig(),
        val s3CutPunchRecovery: S3CutPunchRecoveryConfig = S3CutPunchRecoveryConfig()
    )

    data class RuleEvalResult(
        val predictedShotType: String,
        val firedRules: List<String>
    )

    @Volatile
    private var cachedConfig: Stage3Config? = null

    fun loadConfig(context: Context? = null, rawJsonContent: String? = null): Stage3Config {
        if (rawJsonContent != null) {
            return parseConfigJson(rawJsonContent)
        }
        cachedConfig?.let { return it }
        try {
            val bytes = context?.assets?.open("models/stage3_rules_config.json")?.readBytes()
            if (bytes != null) {
                val parsed = parseConfigJson(String(bytes, Charsets.UTF_8))
                cachedConfig = parsed
                return parsed
            }
        } catch (_: Exception) {
        }
        return Stage3Config()
    }

    fun parseConfigJson(jsonStr: String): Stage3Config {
        return try {
            val map = parseSimpleJsonMap(jsonStr)
            parseConfigMap(map)
        } catch (_: Exception) {
            Stage3Config()
        }
    }

    fun parseConfigMap(map: Map<String, Any?>): Stage3Config {
        return try {
            val version = (map["version"] as? String) ?: "1.1.0"
            @Suppress("UNCHECKED_CAST")
            val rules = (map["rules"] as? Map<String, Any?>) ?: emptyMap()

            @Suppress("UNCHECKED_CAST")
            fun ruleMap(key: String): Map<String, Any?>? = rules[key] as? Map<String, Any?>
            fun Map<String, Any?>.bool(k: String, def: Boolean): Boolean = (this[k] as? Boolean) ?: def
            fun Map<String, Any?>.flt(k: String, def: Float): Float = (this[k] as? Number)?.toFloat() ?: def

            val sg = ruleMap("sweep_dual_path_gate")
            val nb = ruleMap("non_bat_sweep_to_glance")
            val r1 = ruleMap("bat_vertical_guard_rule1")
            val r2 = ruleMap("bat_ahrs_glance_rule2")
            val s1 = ruleMap("s1_ahrs_flat_bat")
            val s2 = ruleMap("s2_power_drive_vs_pull")
            val s3 = ruleMap("s3_cut_punch_recovery")

            Stage3Config(
                version = version,
                sweepDualPathGate = if (sg != null) SweepDualPathGateConfig(
                    enabled = sg.bool("enabled", true),
                    path1DeltaPitchDeg = sg.flt("path1_delta_pitch_deg", 10.0f),
                    path1DeltaGzMs2 = sg.flt("path1_delta_gz_ms2", 1.2f),
                    path1MinProb = sg.flt("path1_min_prob", 0.30f),
                    path2MinRollRads = sg.flt("path2_min_roll_rads", 1.6f),
                    path2MinProb = sg.flt("path2_min_prob", 0.35f)
                ) else SweepDualPathGateConfig(),
                nonBatSweepToGlance = if (nb != null) NonBatSweepToGlanceConfig(
                    enabled = nb.bool("enabled", false),
                    minSub0Glance = nb.flt("min_sub0_glance", 0.55f),
                    maxImpGzMs2 = nb.flt("max_imp_gz_ms2", 5.5f),
                    maxFamSweep = nb.flt("max_fam_sweep", 0.72f),
                    maxCrouchDeltaGzMs2 = if (nb.containsKey("max_crouch_delta_gz_ms2") && nb["max_crouch_delta_gz_ms2"] == null) 999.0f else nb.flt("max_crouch_delta_gz_ms2", 1.2f)
                ) else NonBatSweepToGlanceConfig(),
                batVerticalGuardRule1 = if (r1 != null) BatVerticalGuardRule1Config(
                    enabled = r1.bool("enabled", true),
                    minWatchPitchDeg = r1.flt("min_watch_pitch_deg", 65.0f),
                    powerDrivePostRatio = r1.flt("power_drive_post_ratio", 1.35f)
                ) else BatVerticalGuardRule1Config(),
                batAhrsGlanceRule2 = if (r2 != null) BatAhrsGlanceRule2Config(
                    enabled = r2.bool("enabled", true),
                    yawDegPath1 = r2.flt("yaw_deg_path1", -17.0f),
                    batGzMinPath1 = r2.flt("bat_gz_min_path1", -11.5f),
                    minSub0GlancePath1 = r2.flt("min_sub0_glance_path1", 0.35f),
                    yawDegPath2 = r2.flt("yaw_deg_path2", -50.0f),
                    minSub0GlancePath2 = r2.flt("min_sub0_glance_path2", 0.50f)
                ) else BatAhrsGlanceRule2Config(),
                s1AhrsFlatBat = if (s1 != null) S1AhrsFlatBatConfig(
                    enabled = s1.bool("enabled", false),
                    maxBladePitchDeg = s1.flt("max_blade_pitch_deg", 20.0f),
                    minPostImpactRatioPull = s1.flt("min_post_impact_ratio_pull", 0.65f),
                    maxYawDegGlance = s1.flt("max_yaw_deg_glance", -20.0f)
                ) else S1AhrsFlatBatConfig(),
                s2PowerDriveVsPull = if (s2 != null) S2PowerDriveVsPullConfig(
                    enabled = s2.bool("enabled", false),
                    minFamCross = s2.flt("min_fam_cross", 0.55f),
                    minSub1Pull = s2.flt("min_sub1_pull", 0.75f),
                    maxBladePitchDeg = s2.flt("max_blade_pitch_deg", 35.0f)
                ) else S2PowerDriveVsPullConfig(),
                s3CutPunchRecovery = if (s3 != null) S3CutPunchRecoveryConfig(
                    enabled = s3.bool("enabled", false),
                    minSub1Cut = s3.flt("min_sub1_cut", 0.65f),
                    maxAbsTimeLeadMs = s3.flt("max_abs_time_lead_ms", 15.0f),
                    minFamCross = s3.flt("min_fam_cross", 0.30f)
                ) else S3CutPunchRecoveryConfig()
            )
        } catch (_: Exception) {
            Stage3Config()
        }
    }

    /**
     * Pure-Kotlin recursive JSON parser that works identically on Android runtime and host JVM
     * unit tests (where `android.jar` stubs `org.json.JSONObject`).
     */
    @Suppress("UNCHECKED_CAST")
    fun parseSimpleJsonMap(json: String): Map<String, Any?> {
        var idx = 0
        val n = json.length

        fun skipWs() {
            while (idx < n && json[idx].isWhitespace()) idx++
        }

        fun parseString(): String {
            idx++ // skip opening '"'
            val sb = StringBuilder()
            while (idx < n && json[idx] != '"') {
                if (json[idx] == '\\' && idx + 1 < n) {
                    idx++
                    when (val esc = json[idx]) {
                        '"', '\\', '/' -> sb.append(esc)
                        'n' -> sb.append('\n')
                        'r' -> sb.append('\r')
                        't' -> sb.append('\t')
                        else -> sb.append(esc)
                    }
                } else {
                    sb.append(json[idx])
                }
                idx++
            }
            if (idx < n && json[idx] == '"') idx++
            return sb.toString()
        }

        fun parseValue(): Any? {
            skipWs()
            if (idx >= n) return null
            return when (val ch = json[idx]) {
                '"' -> parseString()
                '{' -> {
                    idx++
                    val map = LinkedHashMap<String, Any?>()
                    skipWs()
                    if (idx < n && json[idx] == '}') {
                        idx++
                        return map
                    }
                    while (idx < n) {
                        skipWs()
                        val key = parseString()
                        skipWs()
                        if (idx < n && json[idx] == ':') idx++
                        val v = parseValue()
                        map[key] = v
                        skipWs()
                        if (idx < n && json[idx] == ',') {
                            idx++
                        } else if (idx < n && json[idx] == '}') {
                            idx++
                            break
                        } else {
                            break
                        }
                    }
                    map
                }
                '[' -> {
                    idx++
                    val list = ArrayList<Any?>()
                    skipWs()
                    if (idx < n && json[idx] == ']') {
                        idx++
                        return list
                    }
                    while (idx < n) {
                        list.add(parseValue())
                        skipWs()
                        if (idx < n && json[idx] == ',') {
                            idx++
                        } else if (idx < n && json[idx] == ']') {
                            idx++
                            break
                        } else {
                            break
                        }
                    }
                    list
                }
                't', 'f' -> {
                    val start = idx
                    while (idx < n && json[idx].isLetter()) idx++
                    json.substring(start, idx).toBooleanStrictOrNull() ?: false
                }
                'n' -> {
                    val start = idx
                    while (idx < n && json[idx].isLetter()) idx++
                    null
                }
                else -> {
                    if (ch == '-' || ch.isDigit()) {
                        val start = idx
                        while (idx < n && (json[idx].isDigit() || json[idx] in "-+.eE")) idx++
                        json.substring(start, idx).toDoubleOrNull() ?: 0.0
                    } else {
                        idx++
                        null
                    }
                }
            }
        }

        return (parseValue() as? Map<String, Any?>) ?: emptyMap()
    }

    /**
     * Closed-form hierarchical probability recovery from the 9-class TCN output vector qMid.
     * Matches `pipelines/stage3_rules.py::recover_hierarchical_probs`.
     */
    fun recoverHierarchicalProbs(qMid: FloatArray): HierarchicalProbs {
        if (qMid.size < 9) return HierarchicalProbs()
        val q0 = qMid[0].toDouble()
        val q2 = qMid[2].toDouble()
        val q3 = qMid[3].toDouble()
        val q4 = qMid[4].toDouble()
        val q5 = qMid[5].toDouble()
        val q6 = qMid[6].toDouble()
        val q7 = qMid[7].toDouble()
        val q8 = qMid[8].toDouble()

        val kVert = q3 + q4 + q6
        val a1Cross = q2 + q5
        val a2Sweep = q8
        val bCoef = kVert + q7 - 0.85 * a1Cross
        val disc = max(0.0, bCoef * bCoef + 3.4 * a1Cross * kVert)
        val a0Vert = 0.5 * (bCoef + sqrt(disc))

        val denomFam = a0Vert + a1Cross + a2Sweep + 1e-12
        val pFamVert = (a0Vert / denomFam).toFloat()
        val pFamCross = (a1Cross / denomFam).toFloat()
        val pFamSweep = (a2Sweep / denomFam).toFloat()

        val pSub0Drive = (q3 / (a0Vert + 1e-12)).toFloat()
        val pSub0Pd = (q7 / (a0Vert + 0.85 * a1Cross + 1e-12)).toFloat()
        val pSub0Glance = (q4 / (a0Vert + 1e-12)).toFloat()
        val pSub0Defl = (q6 / (a0Vert + 1e-12)).toFloat()

        val pSub1Pull = (q2 / (a1Cross + 1e-12)).toFloat()
        val pSub1Cut = (q5 / (a1Cross + 1e-12)).toFloat()

        return HierarchicalProbs(
            pNoShot = q0.toFloat(),
            pIsShot = (1.0 - q0).toFloat(),
            pFamVert = pFamVert,
            pFamCross = pFamCross,
            pFamSweep = pFamSweep,
            pSub0Drive = pSub0Drive,
            pSub0Pd = pSub0Pd,
            pSub0Glance = pSub0Glance,
            pSub0Defl = pSub0Defl,
            pSub1Pull = pSub1Pull,
            pSub1Cut = pSub1Cut
        )
    }

    /**
     * Extracts pre-AHRS features from the 28-channel 423 Hz sensorMatrix at anchorF.
     * Note: `sensorMatrix[14]` is `w_grav_z` (matching `channels_12[:, 8]` in Python).
     */
    fun extractPreAhrsFeatures(
        sensorMatrix: Array<FloatArray>,
        anchorF: Int,
        numFrames: Int
    ): Stage3Features {
        val fStart = max(0, anchorF - 211)
        var minGz = Float.MAX_VALUE
        var maxGz = -Float.MAX_VALUE
        var minPitch = Float.MAX_VALUE
        var maxPitch = -Float.MAX_VALUE
        var maxRollVel = 0f

        for (k in fStart..anchorF) {
            val gx = sensorMatrix[12][k]
            val gy = sensorMatrix[13][k]
            val gz = sensorMatrix[14][k]

            if (gz < minGz) minGz = gz
            if (gz > maxGz) maxGz = gz

            val denom = sqrt((gx * gx + gy * gy + 1e-6).toDouble()).toFloat()
            val pitchDeg = Math.toDegrees(atan2(gz.toDouble(), denom.toDouble())).toFloat()
            if (!pitchDeg.isNaN()) {
                if (pitchDeg < minPitch) minPitch = pitchDeg
                if (pitchDeg > maxPitch) maxPitch = pitchDeg
            }

            val roll = abs(sensorMatrix[3][k])
            if (!roll.isNaN() && roll > maxRollVel) maxRollVel = roll
        }

        val deltaGz = if (maxGz.isNaN() || minGz.isNaN() || minGz > maxGz) 0f else maxGz - minGz
        val deltaPitch = if (maxPitch.isNaN() || minPitch.isNaN() || minPitch > maxPitch) 0f else maxPitch - minPitch

        // Impact gravity Z mean over [anchorF - 20 .. anchorF + 19] using sensorMatrix[14] (w_grav_z)
        val impS = max(0, anchorF - 20)
        val impE = min(numFrames - 1, anchorF + 19)
        var sumImpGz = 0f
        var cntImpGz = 0
        for (k in impS..impE) {
            val wGz = sensorMatrix[14][k]
            if (!wGz.isNaN()) {
                sumImpGz += wGz
                cntImpGz++
            }
        }
        val impGz = if (cntImpGz > 0) sumImpGz / cntImpGz else 6.0f

        val postImpactRatio = sensorMatrix[26][anchorF]
        val hasPolar = sensorMatrix[25][anchorF] > 0.5f

        var watchPitchDeg: Float? = null
        val qx = sensorMatrix[15][anchorF]
        val qy = sensorMatrix[16][anchorF]
        val qz = sensorMatrix[17][anchorF]
        val qw = sensorMatrix[18][anchorF]
        val qMag = qx * qx + qy * qy + qz * qz + qw * qw
        if (!qMag.isNaN() && qMag > 0.5f) {
            val vz = 2.0f * (qy * qz - qx * qw)
            if (!vz.isNaN()) {
                val clampedVz = abs(vz).coerceIn(0f, 1f)
                val pDeg = Math.toDegrees(asin(clampedVz.toDouble())).toFloat()
                if (!pDeg.isNaN()) {
                    watchPitchDeg = pDeg
                }
            }
        }

        return Stage3Features(
            deltaGz = deltaGz,
            deltaPitch = deltaPitch,
            omegaRoll = maxRollVel,
            impGz = impGz,
            postImpactAccRatio = postImpactRatio,
            hasPolar = hasPolar,
            watchPitchDeg = watchPitchDeg
        )
    }

    /**
     * Evaluates pre-AHRS Stage 3 rules inside `TcnModelRunner.kt`:
     *   - Sweep Dual-Path Gate (`SWEEP` -> `"no_shot"` if rejected)
     *   - Non-Bat Sweep -> Glance Mitigation
     *   - Bat Vertical Guard Rule 1 (`w_rot` watch pitch >= 65 deg)
     */
    fun applyPreAhrsRules(
        rawPredCls: String,
        topProb: Float,
        hierProbs: HierarchicalProbs,
        features: Stage3Features,
        polarMountMode: String,
        config: Stage3Config = Stage3Config()
    ): RuleEvalResult {
        var predCls = rawPredCls
        val fired = mutableListOf<String>()

        if (predCls == "SWEEP") {
            val sg = config.sweepDualPathGate
            if (sg.enabled) {
                val isPath1 = (features.deltaPitch >= sg.path1DeltaPitchDeg || features.deltaGz >= sg.path1DeltaGzMs2) &&
                    (topProb >= sg.path1MinProb)
                val isPath2 = (features.omegaRoll >= sg.path2MinRollRads) && (topProb >= sg.path2MinProb)
                if (!isPath1 && !isPath2) {
                    predCls = "no_shot"
                    fired.add("sweep_dual_path_reject")
                }
            }

            if (predCls == "SWEEP" && polarMountMode != "BAT_HANDLE") {
                val nb = config.nonBatSweepToGlance
                if (nb.enabled) {
                    val crouchOk = features.deltaGz < nb.maxCrouchDeltaGzMs2
                    if (hierProbs.pSub0Glance >= nb.minSub0Glance &&
                        features.impGz < nb.maxImpGzMs2 &&
                        hierProbs.pFamSweep < nb.maxFamSweep &&
                        crouchOk
                    ) {
                        predCls = "GLANCE/FLICK"
                        fired.add("non_bat_sweep_to_glance")
                    }
                }
            }
        }

        if (polarMountMode == "BAT_HANDLE" && predCls != "no_shot" && predCls != "NO_SHOT") {
            val r1 = config.batVerticalGuardRule1
            if (r1.enabled) {
                val wpitch = features.watchPitchDeg
                if (wpitch != null && wpitch >= r1.minWatchPitchDeg &&
                    (predCls == "PULL/HOOK/SLOG" || predCls == "CUT/PUNCH")
                ) {
                    predCls = if (features.postImpactAccRatio >= r1.powerDrivePostRatio) {
                        "POWER DRIVE"
                    } else {
                        "DRIVE/DEFENCE"
                    }
                    fired.add("bat_vertical_guard_rule1")
                }
            }
        }

        return RuleEvalResult(predCls, fired)
    }

    /**
     * Evaluates post-AHRS Stage 3 rules inside `PhoneSwingDetector.kt` after 3D AHRS and dual-sensor
     * feature extraction:
     *   - Bat AHRS Glance Rule 2 (`swing_yaw_deg` + `bat_gz_min` + `p_sub0_glance`)
     *   - Candidate Rules S1, S2, S3 (when enabled in `stage3_rules_config.json`)
     */
    fun applyPostAhrsRules(
        currentPredCls: String,
        hierProbs: HierarchicalProbs,
        features: Stage3Features,
        polarMountMode: String,
        config: Stage3Config = Stage3Config(),
        priorFiredRules: List<String> = emptyList()
    ): RuleEvalResult {
        var predCls = currentPredCls
        val fired = priorFiredRules.toMutableList()

        if (predCls == "no_shot" || predCls == "NO_SHOT") {
            return RuleEvalResult(predCls, fired)
        }

        // Rule 2: 3D Bat AHRS Swing Yaw + Handle Axial Roll Glance/Flick Disambiguation
        if (polarMountMode == "BAT_HANDLE") {
            val r2 = config.batAhrsGlanceRule2
            if (r2.enabled && (predCls == "DRIVE/DEFENCE" || predCls == "POWER DRIVE")) {
                val yawDeg = features.ahrsSwingYawDeg
                if (features.ahrsValid && yawDeg != null) {
                    val path1 = yawDeg <= r2.yawDegPath1 &&
                        features.batGzMin <= r2.batGzMinPath1 &&
                        hierProbs.pSub0Glance >= r2.minSub0GlancePath1
                    val path2 = yawDeg <= r2.yawDegPath2 &&
                        hierProbs.pSub0Glance >= r2.minSub0GlancePath2
                    if (path1 || path2) {
                        predCls = "GLANCE/FLICK"
                        fired.add("bat_ahrs_glance_rule2")
                    }
                }
            }
        }

        // Candidate Rule S1: 3D AHRS Flat-Bat Conflict (BAT_HANDLE only)
        val s1 = config.s1AhrsFlatBat
        if (s1.enabled && polarMountMode == "BAT_HANDLE") {
            val bpitch = features.ahrsBladePitchDeg
            if (features.ahrsValid && bpitch != null && bpitch < s1.maxBladePitchDeg &&
                (predCls == "DRIVE/DEFENCE" || predCls == "POWER DRIVE" || predCls == "GLANCE/FLICK")
            ) {
                val syaw = features.ahrsSwingYawDeg ?: 0f
                if (features.postImpactAccRatio >= s1.minPostImpactRatioPull) {
                    predCls = "PULL/HOOK/SLOG"
                    fired.add("s1_ahrs_flat_bat")
                } else if (syaw <= s1.maxYawDegGlance) {
                    predCls = "GLANCE/FLICK"
                    fired.add("s1_ahrs_flat_bat")
                }
            }
        }

        // Candidate Rule S2: Power Drive vs Pull/Hook/Slog Arbitrator
        val s2 = config.s2PowerDriveVsPull
        if (s2.enabled && predCls == "POWER DRIVE") {
            if (hierProbs.pFamCross >= s2.minFamCross && hierProbs.pSub1Pull >= s2.minSub1Pull) {
                val bpitch = features.ahrsBladePitchDeg
                val pitchOk = if (polarMountMode == "BAT_HANDLE" && features.ahrsValid && bpitch != null) {
                    bpitch <= s2.maxBladePitchDeg
                } else {
                    true
                }
                if (pitchOk) {
                    predCls = "PULL/HOOK/SLOG"
                    fired.add("s2_power_drive_vs_pull")
                }
            }
        }

        // Candidate Rule S3: Cut/Punch Dual-Wrist Lock Recovery
        val s3 = config.s3CutPunchRecovery
        if (s3.enabled && (predCls == "DRIVE/DEFENCE" || predCls == "POWER DRIVE" || predCls == "PULL/HOOK/SLOG")) {
            if (features.hasPolar && polarMountMode == "WRIST") {
                val tLead = abs(features.bottomHandTimeLeadMs)
                if (hierProbs.pSub1Cut >= s3.minSub1Cut &&
                    hierProbs.pFamCross >= s3.minFamCross &&
                    tLead <= s3.maxAbsTimeLeadMs
                ) {
                    predCls = "CUT/PUNCH"
                    fired.add("s3_cut_punch_recovery")
                }
            }
        }

        return RuleEvalResult(predCls, fired)
    }

    /**
     * Full Stage 3 evaluation combining pre-AHRS and post-AHRS rules in exact sequence,
     * matching `pipelines/stage3_rules.py::apply_stage3_rules`.
     */
    fun applyAllRules(
        rawPredCls: String,
        topProb: Float,
        hierProbs: HierarchicalProbs,
        features: Stage3Features,
        polarMountMode: String,
        config: Stage3Config = Stage3Config()
    ): RuleEvalResult {
        val pre = applyPreAhrsRules(rawPredCls, topProb, hierProbs, features, polarMountMode, config)
        if (pre.predictedShotType == "no_shot" || pre.predictedShotType == "NO_SHOT") {
            val normalizedNoShot = if (rawPredCls == "NO_SHOT" || pre.predictedShotType == "no_shot") "NO_SHOT" else pre.predictedShotType
            return RuleEvalResult(normalizedNoShot, pre.firedRules)
        }
        return applyPostAhrsRules(pre.predictedShotType, hierProbs, features, polarMountMode, config, pre.firedRules)
    }
}
