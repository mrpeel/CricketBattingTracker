package com.mrpeel.cricketbattingtracker.services

data class ShotData(
    val speedKmh: Float,
    val isHit: Boolean,
    val peakAccel: Float,
    val sweetSpot: String, // "Excellent", "Good", "Poor", or "N/A"
    val efficiency: Float,
    val impactTimeMs: Long,
    val backliftAngle: Float,
    val followThroughAngle: Float,
    val shotType: String,
    val wristRollDeg: Float = 0f,
    val bladeAngle: Float = 0f,
    val bladeClass: String = "N/A",
    val launchAngle: Float = 0f,
    val launchClass: String = "N/A",
    // SwingFeatures for phone-side storage (future re-classification)
    val s1GyroYStd: Float = 0f,
    val s1GyroZStd: Float = 0f,
    val s1DeltaX: Float = 0f,
    val s1DeltaZ: Float = 0f,
    val s2GyroMag: Float = 0f,
    val s2GravYMean: Float = 0f,
    val s2DeltaX: Float = 0f,
    val s2DeltaZ: Float = 0f,
    val s3RollImpactDeg: Float = 0f,
    val s3YawImpactDeg: Float = 0f,
    val s3DeltaX: Float = 0f,
    val s3DeltaZ: Float = 0f,
    val s3PlaneRatio: Float = 0f,
    val s3GyroYMin: Float = 0f
)
