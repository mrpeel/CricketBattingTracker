package com.mrpeel.cricketbattingtracker.ml

import kotlin.math.*

/**
 * OrientationAhrs — State-Gated AHRS Orientation Estimator for Cricket Batting.
 *
 * Reconstructs 3D bat and wrist orientation (spatial attitude, blade inclination,
 * face roll angle, swing path yaw, and relative wrist angle) from 423 Hz Polar Verity Sense
 * IMU telemetry anchored to Galaxy Watch static orientation vectors.
 */
class OrientationAhrs(val mountLocation: String = "BAT_HANDLE") {

    data class OrientationResult(
        val bladePitchDeg: Float,
        val faceAngleDeg: Float,
        val swingYawDeg: Float,
        val relativeWristAngleDeg: Float,
        val azimuthDeviationDeg: Float,
        val gravityDeviation: Float,
        val maxStepJumpDeg: Float,
        val peakAccMag: Float,
        val tPeakSec: Double,
        val tStillSec: Double,
        val tFreezeSec: Double,
        val qFreeze: FloatArray, // [x, y, z, w]
        val isKinematicallyValid: Boolean = true
    )

    companion object {
        const val GRAVITY_STANDARD = 9.80665f

        fun quatMult(q1: FloatArray, q2: FloatArray): FloatArray {
            val x1 = q1[0]; val y1 = q1[1]; val z1 = q1[2]; val w1 = q1[3]
            val x2 = q2[0]; val y2 = q2[1]; val z2 = q2[2]; val w2 = q2[3]
            return floatArrayOf(
                w1*x2 + x1*w2 + y1*z2 - z1*y2,
                w1*y2 - x1*z2 + y1*w2 + z1*x2,
                w1*z2 + x1*y2 - y1*x2 + z1*w2,
                w1*w2 - x1*x2 - y1*y2 - z1*z2
            )
        }

        fun quatConjugate(q: FloatArray): FloatArray {
            return floatArrayOf(-q[0], -q[1], -q[2], q[3])
        }

        fun quatRotate(q: FloatArray, v: FloatArray): FloatArray {
            val p = floatArrayOf(v[0], v[1], v[2], 0.0f)
            val qConj = quatConjugate(q)
            val res = quatMult(quatMult(q, p), qConj)
            return floatArrayOf(res[0], res[1], res[2])
        }

        fun quatFromTwoVectors(u: FloatArray, v: FloatArray): FloatArray {
            val uNorm = normalize3(u)
            val vNorm = normalize3(v)
            val dot = uNorm[0]*vNorm[0] + uNorm[1]*vNorm[1] + uNorm[2]*vNorm[2]
            if (dot < -0.999999f) {
                val ortho = if (abs(uNorm[0]) < 0.9f) floatArrayOf(1f, 0f, 0f) else floatArrayOf(0f, 1f, 0f)
                val axis = normalize3(cross3(uNorm, ortho))
                return floatArrayOf(axis[0], axis[1], axis[2], 0f)
            }
            val xyz = cross3(uNorm, vNorm)
            val w = 1.0f + dot
            val q = floatArrayOf(xyz[0], xyz[1], xyz[2], w)
            return normalize4(q)
        }

        fun quatExpMap(omega: FloatArray, dt: Float): FloatArray {
            val omegaMag = sqrt(omega[0]*omega[0] + omega[1]*omega[1] + omega[2]*omega[2])
            val theta = omegaMag * dt
            return if (theta > 1e-6f) {
                val halfTheta = theta * 0.5f
                val s = sin(halfTheta) / omegaMag
                val c = cos(halfTheta)
                floatArrayOf(omega[0]*s, omega[1]*s, omega[2]*s, c)
            } else {
                val halfDt = 0.5f * dt
                floatArrayOf(omega[0]*halfDt, omega[1]*halfDt, omega[2]*halfDt, 1.0f)
            }
        }

        fun quatToEulerZYX(q: FloatArray): FloatArray {
            // Returns [yaw, pitch, roll] in degrees
            val x = q[0]; val y = q[1]; val z = q[2]; val w = q[3]

            // Roll (x-axis rotation)
            val sinrCosp = 2f * (w * x + y * z)
            val cosrCosp = 1f - 2f * (x * x + y * y)
            val roll = Math.toDegrees(atan2(sinrCosp.toDouble(), cosrCosp.toDouble())).toFloat()

            // Pitch (y-axis rotation)
            val sinp = 2f * (w * y - z * x)
            val pitch = if (abs(sinp) >= 1f) {
                Math.toDegrees(java.lang.Math.copySign(PI / 2.0, sinp.toDouble())).toFloat()
            } else {
                Math.toDegrees(asin(sinp.toDouble())).toFloat()
            }

            // Yaw (z-axis rotation)
            val sinyCosp = 2f * (w * z + x * y)
            val cosyCosp = 1f - 2f * (y * y + z * z)
            val yaw = Math.toDegrees(atan2(sinyCosp.toDouble(), cosyCosp.toDouble())).toFloat()

            return floatArrayOf(yaw, pitch, roll)
        }

        fun quatMagnitudeDeg(q: FloatArray): FloatArray {
            val w = q[3].coerceIn(-1.0f, 1.0f)
            val angleRad = 2.0 * acos(abs(w).toDouble())
            return floatArrayOf(Math.toDegrees(angleRad).toFloat())
        }

        private fun normalize3(v: FloatArray): FloatArray {
            val mag = sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]) + 1e-12f
            return floatArrayOf(v[0]/mag, v[1]/mag, v[2]/mag)
        }

        private fun normalize4(q: FloatArray): FloatArray {
            val mag = sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]) + 1e-12f
            return floatArrayOf(q[0]/mag, q[1]/mag, q[2]/mag, q[3]/mag)
        }

        private fun cross3(a: FloatArray, b: FloatArray): FloatArray {
            return floatArrayOf(
                a[1]*b[2] - a[2]*b[1],
                a[2]*b[0] - a[0]*b[2],
                a[0]*b[1] - a[1]*b[0]
            )
        }
    }

    /**
     * Evaluates 3D orientation for a detected impact event.
     */
    fun evaluateShot(
        tImpactSec: Double,
        pTimesSec: DoubleArray,
        pAcc: Array<FloatArray>, // [3][N]
        pGyro: Array<FloatArray>, // [3][N]
        wTimesSec: DoubleArray,
        wGyroMag: FloatArray,
        wRotTimesSec: DoubleArray,
        wRot: Array<FloatArray> // [4][M] (qx, qy, qz, qw)
    ): OrientationResult? {
        val numPolar = pTimesSec.size
        if (numPolar < 100 || pAcc[0].size != numPolar || pGyro[0].size != numPolar) return null

        val pAccMags = FloatArray(numPolar) { i ->
            val ax = pAcc[0][i]; val ay = pAcc[1][i]; val az = pAcc[2][i]
            sqrt(ax*ax + ay*ay + az*az)
        }
        val pGyroMags = FloatArray(numPolar) { i ->
            val gx = pGyro[0][i]; val gy = pGyro[1][i]; val gz = pGyro[2][i]
            sqrt(gx*gx + gy*gy + gz*gz)
        }

        // 1. Locate shockwave peak within +/- 350ms of target
        val tMin = tImpactSec - 0.35
        val tMax = tImpactSec + 0.35
        var peakAcc = 0f
        var peakIdx = -1
        for (i in 0 until numPolar) {
            val t = pTimesSec[i]
            if (t in tMin..tMax && pAccMags[i] > peakAcc) {
                peakAcc = pAccMags[i]
                peakIdx = i
            }
        }
        if (peakIdx == -1) return null
        val tPeak = pTimesSec[peakIdx]
        val tFreeze = tPeak - 0.002

        // 2. Dual Stillness Lock: search [tPeak - 1.5s, tPeak - 0.35s]
        val searchStart = tPeak - 1.5
        val searchEnd = tPeak - 0.35
        var bestScore = Float.MAX_VALUE
        var bestTc = -1.0
        var bestABar = floatArrayOf(0f, 0f, 0f)

        var tc = searchStart
        while (tc <= searchEnd) {
            val tcEnd = tc + 0.20
            var countA = 0
            var axSum = 0f; var aySum = 0f; var azSum = 0f
            var countG = 0
            var bgSum = 0f

            for (i in 0 until numPolar) {
                val t = pTimesSec[i]
                if (t in tc..tcEnd) {
                    axSum += pAcc[0][i]; aySum += pAcc[1][i]; azSum += pAcc[2][i]
                    countA++
                    bgSum += pGyroMags[i]
                    countG++
                }
            }

            if (countA > 5 && countG > 5) {
                val aBar = floatArrayOf(axSum / countA, aySum / countA, azSum / countA)
                val aBarMag = sqrt(aBar[0]*aBar[0] + aBar[1]*aBar[1] + aBar[2]*aBar[2])
                val gDev = abs(aBarMag - GRAVITY_STANDARD)
                val bOmega = bgSum / countG

                // Watch gyro during tc..tcEnd
                var wOmega = 0f
                var countW = 0
                for (j in 0 until wTimesSec.size) {
                    val wt = wTimesSec[j]
                    if (wt in tc..tcEnd) {
                        wOmega += wGyroMag[j]
                        countW++
                    }
                }
                if (countW > 0) wOmega /= countW

                val score = bOmega + wOmega + 0.5f * gDev
                if (score < bestScore) {
                    bestScore = score
                    bestTc = tc
                    bestABar = aBar
                }
            }
            tc += 0.02
        }

        if (bestTc < 0.0) return null
        val tStill = bestTc + 0.10
        val aBarMag = sqrt(bestABar[0]*bestABar[0] + bestABar[1]*bestABar[1] + bestABar[2]*bestABar[2])
        val gravityDev = abs(aBarMag - GRAVITY_STANDARD)

        // 3. Attitude & Yaw Seeding (q0)
        val gSensor = floatArrayOf(bestABar[0]/aBarMag, bestABar[1]/aBarMag, bestABar[2]/aBarMag)
        val vVert = floatArrayOf(0f, 0f, 1f)
        val qTilt = quatFromTwoVectors(gSensor, vVert)

        // Find watch orientation nearest tStill
        var nearestWIdx = 0
        var minDt = Double.MAX_VALUE
        for (j in 0 until wRotTimesSec.size) {
            val dt = abs(wRotTimesSec[j] - tStill)
            if (dt < minDt) {
                minDt = dt
                nearestWIdx = j
            }
        }
        val qWatchStill = floatArrayOf(
            wRot[0][nearestWIdx], wRot[1][nearestWIdx], wRot[2][nearestWIdx], wRot[3][nearestWIdx]
        )
        val eulerWatch = quatToEulerZYX(qWatchStill)
        val psiWatchRad = Math.toRadians(eulerWatch[0].toDouble()).toFloat()

        val halfPsi = psiWatchRad * 0.5f
        val qYaw = floatArrayOf(0f, 0f, sin(halfPsi), cos(halfPsi))
        val q0 = normalize4(quatMult(qYaw, qTilt))

        // 4. Dynamic Gated Gyroscope Integration
        var qCurr = q0.clone()
        var maxStepJumpDeg = 0f
        var lastT = -1.0
        var lastOmega = floatArrayOf(0f, 0f, 0f)

        for (i in 0 until numPolar) {
            val t = pTimesSec[i]
            if (t in tStill..tFreeze) {
                val omega = floatArrayOf(pGyro[0][i], pGyro[1][i], pGyro[2][i])
                if (lastT > 0.0) {
                    val dt = (t - lastT).toFloat()
                    if (dt in 0.0001f..0.02f) {
                        val omegaMid = floatArrayOf(
                            0.5f * (omega[0] + lastOmega[0]),
                            0.5f * (omega[1] + lastOmega[1]),
                            0.5f * (omega[2] + lastOmega[2])
                        )
                        val dq = quatExpMap(omegaMid, dt)
                        val qNext = normalize4(quatMult(qCurr, dq))

                        val stepDiff = quatMult(quatConjugate(qCurr), qNext)
                        val stepDeg = quatMagnitudeDeg(stepDiff)[0]
                        if (stepDeg > maxStepJumpDeg) {
                            maxStepJumpDeg = stepDeg
                        }
                        qCurr = qNext
                    }
                }
                lastT = t
                lastOmega = omega
            }
        }

        val qFreeze = qCurr.clone()

        // 5. Metric Extraction
        val longAxis = floatArrayOf(0f, 1f, 0f)
        val vWorld = quatRotate(qFreeze, longAxis)
        val pitchDeg = Math.toDegrees(asin(abs(vWorld[2]).coerceIn(0f, 1f).toDouble())).toFloat()

        val qRel = quatMult(quatConjugate(q0), qFreeze)
        val eulerRel = quatToEulerZYX(qRel)
        val faceRollDeg = eulerRel[2]
        val swingYawDeg = eulerRel[0]

        // Relative wrist angle to watch at impact freeze
        var freezeWIdx = 0
        var minFreezeDt = Double.MAX_VALUE
        for (j in 0 until wRotTimesSec.size) {
            val dt = abs(wRotTimesSec[j] - tFreeze)
            if (dt < minFreezeDt) {
                minFreezeDt = dt
                freezeWIdx = j
            }
        }
        val qWatchFreeze = floatArrayOf(
            wRot[0][freezeWIdx], wRot[1][freezeWIdx], wRot[2][freezeWIdx], wRot[3][freezeWIdx]
        )
        val qRelWrist = quatMult(quatConjugate(qWatchFreeze), qFreeze)
        val relWristDeg = quatMagnitudeDeg(qRelWrist)[0]

        val eulerWFreeze = quatToEulerZYX(qWatchFreeze)
        val eulerFreeze = quatToEulerZYX(qFreeze)
        val azimDevDeg = ((eulerFreeze[0] - eulerWFreeze[0] + 180f) % 360f) - 180f

        return OrientationResult(
            bladePitchDeg = pitchDeg,
            faceAngleDeg = faceRollDeg,
            swingYawDeg = swingYawDeg,
            relativeWristAngleDeg = relWristDeg,
            azimuthDeviationDeg = azimDevDeg,
            gravityDeviation = gravityDev,
            maxStepJumpDeg = maxStepJumpDeg,
            peakAccMag = peakAcc,
            tPeakSec = tPeak,
            tStillSec = tStill,
            tFreezeSec = tFreeze,
            qFreeze = qFreeze,
            isKinematicallyValid = true
        )
    }
}
