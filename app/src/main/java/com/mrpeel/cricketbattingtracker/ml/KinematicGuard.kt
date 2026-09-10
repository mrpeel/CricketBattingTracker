package com.mrpeel.cricketbattingtracker.ml

import kotlin.math.sqrt

/**
 * KinematicGuard — Kinematic Detachment and Physical Anomaly Guard.
 *
 * Detects physical sensor detachment, ballistic free-fall, uncoupled impact shockwaves,
 * and hardware clipping artifacts during batting sessions. Routes faulted strokes to
 * the Watch-Only fallback pipeline.
 */
class KinematicGuard(val configuredMountMode: String = "BAT_HANDLE") {

    data class GuardResult(
        val isKinematicallyValid: Boolean,
        val isFallbackWatchOnly: Boolean,
        val anomalyReason: String,
        val runtimeMountType: String
    )

    fun evaluateShot(
        tImpactSec: Double,
        pTimesSec: DoubleArray,
        pAcc: Array<FloatArray>, // [3][N]
        pGyro: Array<FloatArray>, // [3][N]
        wTimesSec: DoubleArray? = null,
        wAcc: Array<FloatArray>? = null,
        wGyrTimesSec: DoubleArray? = null,
        wGyroMag: FloatArray? = null,
        ahrsResult: OrientationAhrs.OrientationResult? = null
    ): GuardResult {
        val numPolar = pTimesSec.size
        if (numPolar == 0 || pAcc.size < 3 || pGyro.size < 3 || pAcc[0].size < numPolar || pGyro[0].size < numPolar) {
            return GuardResult(
                isKinematicallyValid = false,
                isFallbackWatchOnly = false,
                anomalyReason = "NO_POLAR_TELEMETRY",
                runtimeMountType = "FAULTED_ANOMALY"
            )
        }

        val pAccMags = FloatArray(numPolar) { i ->
            val ax = pAcc[0][i]; val ay = pAcc[1][i]; val az = pAcc[2][i]
            sqrt(ax*ax + ay*ay + az*az)
        }

        // 1. Zero-G Free Fall Check: post-impact [tImpact, tImpact + 1.2s]
        var maxConsecZeroGDur = 0.0
        var zeroGStart = -1.0
        for (i in 0 until numPolar) {
            val t = pTimesSec[i]
            if (t in tImpactSec..(tImpactSec + 1.2)) {
                if (pAccMags[i] < 2.5f) {
                    // Reset if contiguous frames were interrupted by BLE packet loss (> 15ms)
                    if (i > 0 && (t - pTimesSec[i - 1]) > 0.015) {
                        zeroGStart = t
                    } else if (zeroGStart < 0.0) {
                        zeroGStart = t
                    }
                    val dur = t - zeroGStart
                    if (dur > maxConsecZeroGDur) maxConsecZeroGDur = dur
                } else {
                    zeroGStart = -1.0
                }
            }
        }
        if (maxConsecZeroGDur >= 0.080) { // >= 80ms zero-g free fall
            return handleAnomaly("ZERO_G_FREE_FALL (${(maxConsecZeroGDur*1000).toInt()}ms < 2.5 m/s2)", tImpactSec, wGyrTimesSec, wGyroMag)
        }

        // 2. Ballistic Multi-Axis Free-Flight Tumble
        var maxSpinDur = 0.0
        var spinStart = -1.0
        for (i in 0 until numPolar) {
            val t = pTimesSec[i]
            if (t in tImpactSec..(tImpactSec + 1.2)) {
                val gx = kotlin.math.abs(pGyro[0][i])
                val gy = kotlin.math.abs(pGyro[1][i])
                val gz = kotlin.math.abs(pGyro[2][i])
                val gMag = sqrt(gx*gx + gy*gy + gz*gz)

                var axesOver12 = 0
                if (gx >= 12f) axesOver12++
                if (gy >= 12f) axesOver12++
                if (gz >= 12f) axesOver12++

                if (axesOver12 >= 2 && gMag >= 20f) {
                    // Reset if contiguous frames were interrupted by BLE packet loss (> 15ms)
                    if (i > 0 && (t - pTimesSec[i - 1]) > 0.015) {
                        spinStart = t
                    } else if (spinStart < 0.0) {
                        spinStart = t
                    }
                    val dur = t - spinStart
                    if (dur > maxSpinDur) maxSpinDur = dur
                } else {
                    spinStart = -1.0
                }
            }
        }
        if (maxSpinDur >= 0.120) {
            return handleAnomaly("BALLISTIC_FREE_FLIGHT_TUMBLE (${(maxSpinDur*1000).toInt()}ms >= 20 rad/s)", tImpactSec, wGyrTimesSec, wGyroMag)
        }

        // 3. Uncoupled Extreme Shockwave
        // Polar > 45g (441.3 m/s2) with Watch < 18 m/s2 within +/- 100ms
        var polarPeakInWin = 0f
        for (i in 0 until numPolar) {
            val t = pTimesSec[i]
            if (t in (tImpactSec - 0.10)..(tImpactSec + 0.10)) {
                if (pAccMags[i] > polarPeakInWin) polarPeakInWin = pAccMags[i]
            }
        }
        if (polarPeakInWin >= 441.3f && wTimesSec != null && wAcc != null && wAcc.size >= 3 && wAcc[0].size >= wTimesSec.size) {
            var watchPeakInWin = 0f
            for (j in 0 until wTimesSec.size) {
                val t = wTimesSec[j]
                if (t in (tImpactSec - 0.10)..(tImpactSec + 0.10)) {
                    val wax = wAcc[0][j]; val way = wAcc[1][j]; val waz = wAcc[2][j]
                    val wMag = sqrt(wax*wax + way*way + waz*waz)
                    if (wMag > watchPeakInWin) watchPeakInWin = wMag
                }
            }
            if (watchPeakInWin < 18.0f) {
                return handleAnomaly("UNCOUPLED_SHOCKWAVE (Polar=${(polarPeakInWin/9.81f).toInt()}g vs Watch=${watchPeakInWin.toInt()} m/s2)", tImpactSec, wGyrTimesSec, wGyroMag)
            }
        }

        // 4. AHRS Metric Checks
        if (ahrsResult != null) {
            if (ahrsResult.maxStepJumpDeg > 160f) {
                return handleAnomaly("DISCONTINUOUS_INVERSION_JUMP (${ahrsResult.maxStepJumpDeg.toInt()} deg)", tImpactSec, wGyrTimesSec, wGyroMag)
            }
            if (ahrsResult.gravityDeviation > 3.0f) {
                return handleAnomaly("GRAVITY_LOCK_DEVIATION (${ahrsResult.gravityDeviation} m/s2)", tImpactSec, wGyrTimesSec, wGyroMag)
            }
        }

        return GuardResult(
            isKinematicallyValid = true,
            isFallbackWatchOnly = false,
            anomalyReason = "CLEAN",
            runtimeMountType = configuredMountMode
        )
    }

    private fun handleAnomaly(
        reason: String,
        tImpactSec: Double,
        wGyrTimesSec: DoubleArray?,
        wGyroMag: FloatArray?
    ): GuardResult {
        var isWatchSwing = false
        if (wGyrTimesSec != null && wGyroMag != null) {
            for (i in 0 until wGyrTimesSec.size) {
                val t = wGyrTimesSec[i]
                if (t in (tImpactSec - 0.50)..(tImpactSec + 0.25)) {
                    if (wGyroMag[i] >= 3.5f) {
                        isWatchSwing = true
                        break
                    }
                }
            }
        }
        return GuardResult(
            isKinematicallyValid = false,
            isFallbackWatchOnly = isWatchSwing,
            anomalyReason = reason,
            runtimeMountType = "FAULTED_ANOMALY"
        )
    }
}
