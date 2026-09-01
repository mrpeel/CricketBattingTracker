package com.mrpeel.cricketbattingtracker.ui.insights

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mrpeel.cricketbattingtracker.analytics.DiagnosticDiagnosisResult
import com.mrpeel.cricketbattingtracker.analytics.DiagnosticFaultReport
import com.mrpeel.cricketbattingtracker.analytics.LongitudinalAggregationResult
import com.mrpeel.cricketbattingtracker.analytics.MetricDistribution
import com.mrpeel.cricketbattingtracker.analytics.PrescriptionDrill
import com.mrpeel.cricketbattingtracker.analytics.ShotClassStatisticalProfile
import java.util.Locale
import kotlin.math.roundToInt

/**
 * Presentation state containing longitudinal aggregation and diagnostic analysis.
 */
data class LongitudinalInsightsUiState(
    val aggregation: LongitudinalAggregationResult,
    val diagnosis: DiagnosticDiagnosisResult,
    val isLoading: Boolean = false
)

/**
 * Player Insights & Trend Analytics Dashboard Screen.
 */
@Composable
fun InsightsDashboardScreen(
    insightsState: LongitudinalInsightsUiState,
    onStartDualSensorSession: () -> Unit = {}
) {
    val aggregation = insightsState.aggregation
    val diagnosis = insightsState.diagnosis
    val hasSufficientData = aggregation.totalShots >= 5 && aggregation.classProfiles.isNotEmpty()

    // Default to the highest-volume stroke class
    val defaultClass = remember(aggregation) {
        aggregation.classProfiles.keys.maxByOrNull {
            aggregation.classProfiles[it]?.sampleCount ?: 0
        } ?: aggregation.classProfiles.keys.firstOrNull()
    }
    var selectedShotClass by remember(defaultClass) { mutableStateOf(defaultClass) }

    val activeProfile = selectedShotClass?.let { aggregation.classProfiles[it] }
        ?: aggregation.classProfiles.values.firstOrNull()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF000C1B)),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // ── Top Repertoire Overview Header ──
        item {
            RepertoireOverviewHeader(
                totalShots = aggregation.totalShots,
                totalSessions = aggregation.totalSessionsAnalyzed,
                totalDualShots = aggregation.totalDualSensorShots,
                totalDualSessions = aggregation.totalDualSessionsAnalyzed,
                activeFamiliesCount = aggregation.classProfiles.size
            )
        }

        if (!hasSufficientData) {
            // Empty / Insufficient Data Onboarding State
            item {
                InsufficientDataCard(
                    totalShots = aggregation.totalShots,
                    insufficientClasses = aggregation.insufficientDataClasses,
                    onStartSession = onStartDualSensorSession
                )
            }
        } else {
            // ── Section 1: Shot Class Deep Dive (FIRST) ──
            item {
                ShotFamilySelectorCarousel(
                    families = aggregation.shotFamilyDistribution,
                    classProfiles = aggregation.classProfiles,
                    selectedClass = selectedShotClass ?: activeProfile?.shotClass ?: "",
                    onSelectClass = { selectedShotClass = it }
                )
            }

            // Detailed Deep Dive Card for Selected Stroke
            if (activeProfile != null) {
                item {
                    ShotClassDeepDiveCard(profile = activeProfile)
                }
            } else if (selectedShotClass != null && aggregation.insufficientDataClasses.containsKey(selectedShotClass)) {
                item {
                    CalibratingClassCard(
                        shotClass = selectedShotClass!!,
                        count = aggregation.insufficientDataClasses[selectedShotClass] ?: 0,
                        onStartSession = onStartDualSensorSession
                    )
                }
            }

            // ── Section 2: Systematic Flaws & Corrective Drills (LOWER DOWN) ──
            item {
                Spacer(modifier = Modifier.height(8.dp))
                SectionHeader(
                    title = "SYSTEMATIC FLAWS & CORRECTIVE DRILLS",
                    subtitle = "DETECTED WEAKNESS PATTERNS & TARGETED DRILL PRESCRIPTIONS"
                )
            }

            if (diagnosis.allDetectedFaults.isNotEmpty()) {
                items(diagnosis.allDetectedFaults) { faultReport ->
                    PrimaryFlawCard(faultReport = faultReport)
                }

                item {
                    SectionHeader(
                        title = "PRESCRIBED TRAINING DRILLS",
                        subtitle = "DETERMINISTIC CORRECTIVE DRILL CATALOGUE"
                    )
                }

                items(diagnosis.prescribedDrills) { drill ->
                    PrescribedDrillCard(drill = drill)
                }
            } else {
                item {
                    OptimalHealthCard()
                }
            }

            // Insufficient data footer if any classes have < 5 shots
            if (aggregation.insufficientDataClasses.isNotEmpty()) {
                item {
                    InsufficientClassesFooter(
                        insufficientClasses = aggregation.insufficientDataClasses
                    )
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Section 1 Components: Repertoire Header, Selector, Deep Dive Card
// ─────────────────────────────────────────────────────────────────────────────

@Composable
fun RepertoireOverviewHeader(
    totalShots: Int,
    totalSessions: Int,
    totalDualShots: Int,
    totalDualSessions: Int,
    activeFamiliesCount: Int
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D)),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.25f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Column {
                Text(
                    "BIOMECHANICAL INSIGHTS",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Black,
                    color = Color(0xFF58FF63),
                    letterSpacing = 1.5.sp
                )
                Text(
                    "Longitudinal Repertoire Analysis",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    color = Color.White
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color(0xFF00142B),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.08f)),
                    modifier = Modifier.weight(1f).padding(end = 6.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text("📊", fontSize = 14.sp)
                        Column {
                            Text(
                                "$totalShots TOTAL SHOTS",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Black,
                                color = Color(0xFF58FF63),
                                letterSpacing = 0.5.sp
                            )
                            Text(
                                "Across $totalSessions sessions",
                                fontSize = 9.sp,
                                color = Color(0xFFBCD2FE).copy(alpha = 0.8f)
                            )
                        }
                    }
                }

                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color(0xFF00142B),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.08f)),
                    modifier = Modifier.weight(1f).padding(start = 6.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text("🏏", fontSize = 14.sp)
                        Column {
                            Text(
                                "$activeFamiliesCount STROKE FAMILIES",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Black,
                                color = Color.White,
                                letterSpacing = 0.5.sp
                            )
                            Text(
                                if (totalDualShots > 0) "$totalDualShots dual ($totalDualSessions sess)" else "Watch single-sensor",
                                fontSize = 9.sp,
                                color = Color(0xFFBCD2FE).copy(alpha = 0.8f)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ShotFamilySelectorCarousel(
    families: Map<String, Int>,
    classProfiles: Map<String, ShotClassStatisticalProfile>,
    selectedClass: String,
    onSelectClass: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "SELECT STROKE FAMILY",
            fontSize = 9.sp,
            fontWeight = FontWeight.Bold,
            color = Color.Gray,
            letterSpacing = 1.sp
        )
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            val activeFamilies = families.entries
                .filter { it.value > 0 }
                .sortedByDescending { it.value }

            items(activeFamilies) { (shotClass, count) ->
                val isSelected = shotClass.equals(selectedClass, ignoreCase = true)
                val isCalibrated = classProfiles.containsKey(shotClass)
                val totalShots = families.values.sum().coerceAtLeast(1)
                val pct = (count.toFloat() / totalShots.toFloat()) * 100f

                Surface(
                    shape = RoundedCornerShape(12.dp),
                    color = when {
                        isSelected -> Color(0xFF002A5E)
                        isCalibrated -> Color(0xFF001B3D)
                        else -> Color(0xFF001020)
                    },
                    border = BorderStroke(
                        if (isSelected) 1.5.dp else 1.dp,
                        when {
                            isSelected -> Color(0xFF58FF63)
                            isCalibrated -> Color(0xFF58FF63).copy(alpha = 0.35f)
                            else -> Color.White.copy(alpha = 0.06f)
                        }
                    ),
                    modifier = Modifier.clickable { onSelectClass(shotClass) }
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            shotClass,
                            fontSize = 11.sp,
                            fontWeight = if (isSelected) FontWeight.Black else FontWeight.Bold,
                            color = if (isSelected) Color(0xFF58FF63) else if (isCalibrated) Color.White else Color.Gray
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            "$count shots (${pct.toInt()}%)",
                            fontSize = 9.sp,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                            color = if (isSelected) Color.White else if (isCalibrated) Color(0xFFBCD2FE).copy(alpha = 0.8f) else Color.Gray.copy(alpha = 0.6f)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ShotClassDeepDiveCard(profile: ShotClassStatisticalProfile) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D)),
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.3f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // ── Header: Shot Name + Volume + Fault Rate ──
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f).padding(end = 8.dp)) {
                    Text(
                        profile.shotClass,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.White
                    )
                    Text(
                        "${profile.sampleCount} shots evaluated (${profile.dualSensorSampleCount} dual-sensor) • ${profile.percentageOfRepertoire.toInt()}% of repertoire",
                        fontSize = 11.sp,
                        color = Color(0xFFBCD2FE).copy(alpha = 0.85f)
                    )
                }

                val warningColor = if (profile.amberFaultRate > 30f) Color(0xFFFFB020) else Color(0xFF58FF63)
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = warningColor.copy(alpha = 0.15f),
                    border = BorderStroke(1.dp, warningColor.copy(alpha = 0.4f))
                ) {
                    Text(
                        if (profile.amberFaultRate > 0f) "FAULT: ${profile.amberFaultRate.toInt()}%" else "OPTIMAL",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = warningColor
                    )
                }
            }

            // ── Speed & Efficiency KPI 2x2 Grid ──
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    KpiMetricTile(
                        modifier = Modifier.weight(1f),
                        title = "PEAK BAT SPEED",
                        value = "${profile.batSpeedMax.roundToInt()}",
                        unit = "km/h",
                        subtitle = "Fastest recorded",
                        valueColor = Color(0xFF58FF63)
                    )
                    KpiMetricTile(
                        modifier = Modifier.weight(1f),
                        title = "80P SPEED",
                        value = "${profile.batSpeedP80.roundToInt()}",
                        unit = "km/h",
                        subtitle = "Reliable delivery",
                        valueColor = Color(0xFF58FF63)
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    KpiMetricTile(
                        modifier = Modifier.weight(1f),
                        title = "80P EFFICIENCY",
                        value = "${profile.efficiencyP80.roundToInt()}%",
                        unit = "",
                        subtitle = "Impact quality",
                        valueColor = Color(0xFFBCD2FE)
                    )
                    KpiMetricTile(
                        modifier = Modifier.weight(1f),
                        title = "AVG EFFICIENCY",
                        value = "${profile.efficiencyMean.roundToInt()}%",
                        unit = "",
                        subtitle = "Mean contact",
                        valueColor = Color(0xFFBCD2FE)
                    )
                }
            }

            // ── Consistent Biomechanical Traits ──
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = Color(0xFF00142B),
                border = BorderStroke(1.dp, Color.White.copy(alpha = 0.06f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        "🎯 CONSISTENT BIOMECHANICAL TRAITS",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFF58FF63),
                        letterSpacing = 1.sp
                    )

                    TraitRow(icon = "🖐️", label = "Hand Dominance", trait = profile.angularTrait)
                    TraitRow(icon = "⏱️", label = "Timing Signature", trait = profile.timingTrait)
                    TraitRow(icon = "⚡", label = "Linear Force", trait = profile.linearTrait)
                }
            }

            // ── Key Technical Pattern Observation ──
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = Color(0xFF00224D).copy(alpha = 0.5f),
                border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.25f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.Top,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("📝", fontSize = 16.sp)
                    Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text(
                            "TECHNICAL PATTERN OBSERVATION",
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Black,
                            color = Color(0xFF58FF63),
                            letterSpacing = 1.sp
                        )
                        Text(
                            profile.keyTechnicalObservation,
                            fontSize = 11.sp,
                            color = Color.White,
                            lineHeight = 16.sp
                        )
                    }
                }
            }

            // ── Biomechanical Range Visualizers (If Dual Sensor Available) ──
            if (profile.hasSufficientDualData) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        "📊 KINEMATIC SPREAD VS COACHING TARGET ZONES",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.Gray,
                        letterSpacing = 1.sp
                    )

                    // 1. Time Lead Range Visualizer
                    val (timeTargetMin, timeTargetMax, timeMinAxis, timeMaxAxis) = getTimeLeadRanges(profile.shotClass)
                    MetricRangeVisualizer(
                        metricTitle = "Timing Lead (Δt = T_bottom - T_top)",
                        distribution = profile.timeLeadDistribution,
                        targetMin = timeTargetMin,
                        targetMax = timeTargetMax,
                        axisMin = timeMinAxis,
                        axisMax = timeMaxAxis,
                        formatValue = { val v = it.toInt(); if (v >= 0) "+${v}ms" else "${v}ms" }
                    )

                    // 2. Gyro Ratio Range Visualizer
                    val (gyroTargetMin, gyroTargetMax, gyroMinAxis, gyroMaxAxis) = getGyroRatioRanges(profile.shotClass)
                    MetricRangeVisualizer(
                        metricTitle = "Wrist Spin Ratio (ω_bottom / ω_top)",
                        distribution = profile.gyroRatioDistribution,
                        targetMin = gyroTargetMin,
                        targetMax = gyroTargetMax,
                        axisMin = gyroMinAxis,
                        axisMax = gyroMaxAxis,
                        formatValue = { String.format(Locale.US, "%.2fx", it) }
                    )

                    // 3. Acc Ratio Range Visualizer
                    val (accTargetMin, accTargetMax, accMinAxis, accMaxAxis) = getAccRatioRanges(profile.shotClass)
                    MetricRangeVisualizer(
                        metricTitle = "Linear Force Ratio (a_bottom / a_top)",
                        distribution = profile.accRatioDistribution,
                        targetMin = accTargetMin,
                        targetMax = accTargetMax,
                        axisMin = accMinAxis,
                        axisMax = accMaxAxis,
                        formatValue = { String.format(Locale.US, "%.2fx", it) }
                    )
                }
            }
        }
    }
}

@Composable
fun KpiMetricTile(
    modifier: Modifier = Modifier,
    title: String,
    value: String,
    unit: String,
    subtitle: String,
    valueColor: Color
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = Color(0xFF00142B),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.06f))
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.Start
        ) {
            Text(
                title,
                fontSize = 8.sp,
                fontWeight = FontWeight.Bold,
                color = Color.Gray,
                letterSpacing = 0.5.sp
            )
            Spacer(modifier = Modifier.height(2.dp))
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    value,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Black,
                    color = valueColor,
                    lineHeight = 26.sp
                )
                if (unit.isNotEmpty()) {
                    Spacer(modifier = Modifier.width(3.dp))
                    Text(
                        unit,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Gray
                    )
                }
            }
            Text(
                subtitle,
                fontSize = 9.sp,
                color = Color(0xFFBCD2FE).copy(alpha = 0.7f)
            )
        }
    }
}

@Composable
fun TraitRow(icon: String, label: String, trait: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(icon, fontSize = 12.sp)
            Text(
                label,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color(0xFFBCD2FE).copy(alpha = 0.8f)
            )
        }
        Text(
            trait,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = Color.White
        )
    }
}

@Composable
fun CalibratingClassCard(
    shotClass: String,
    count: Int,
    onStartSession: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D)),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.08f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("🏏", fontSize = 32.sp)
            Text(
                "$shotClass CALIBRATING ($count/5 shots)",
                fontSize = 12.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFF58FF63),
                letterSpacing = 1.sp
            )
            Text(
                "Log ${5 - count} more $shotClass shots to unlock full speed, efficiency, and kinematic distribution analysis.",
                fontSize = 11.sp,
                color = Color(0xFFBCD2FE).copy(alpha = 0.8f),
                textAlign = TextAlign.Center,
                lineHeight = 15.sp
            )
            Button(
                onClick = onStartSession,
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF58FF63),
                    contentColor = Color(0xFF000C1B)
                ),
                shape = RoundedCornerShape(10.dp)
            ) {
                Text("RECORD SESSION", fontSize = 10.sp, fontWeight = FontWeight.Black)
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Section 2 Components: Primary Flaw Cards & Prescribed Drills
// ─────────────────────────────────────────────────────────────────────────────

@Composable
fun PrimaryFlawCard(faultReport: DiagnosticFaultReport) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1400)),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, Color(0xFFFFB020).copy(alpha = 0.6f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Header: Warning Badge + Fault Code
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text("⚠️", fontSize = 14.sp)
                    Text(
                        faultReport.faultCode.codeString,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFFFFB020),
                        letterSpacing = 1.sp
                    )
                }
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFFFB020).copy(alpha = 0.15f),
                    border = BorderStroke(1.dp, Color(0xFFFFB020).copy(alpha = 0.3f))
                ) {
                    Text(
                        "${faultReport.faultRate.toInt()}% AFFECTED",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFFFB020)
                    )
                }
            }

            // Identified Pattern Title
            Text(
                faultReport.identifiedPattern,
                fontSize = 15.sp,
                fontWeight = FontWeight.Black,
                color = Color.White
            )

            // Technical Flaw Description
            Text(
                faultReport.primaryTechnicalFlaw,
                fontSize = 12.sp,
                color = Color(0xFFBCD2FE).copy(alpha = 0.9f),
                lineHeight = 17.sp
            )

            // Observed Kinematics vs Optimal Target
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFF100B00),
                border = BorderStroke(1.dp, Color(0xFFFFB020).copy(alpha = 0.2f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        "OBSERVED: ${faultReport.observedKinematics}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFFFB020)
                    )
                    Text(
                        "TARGET: ${faultReport.optimalTargetKinematics}",
                        fontSize = 10.sp,
                        color = Color(0xFF58FF63).copy(alpha = 0.9f)
                    )
                }
            }

            // Quantified Impact Projection
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFF00224D).copy(alpha = 0.6f),
                border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.3f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("📈", fontSize = 16.sp)
                    Column {
                        Text(
                            "QUANTIFIED IMPACT",
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Black,
                            color = Color(0xFF58FF63),
                            letterSpacing = 1.sp
                        )
                        Text(
                            faultReport.quantifiedImpact,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun PrescribedDrillCard(drill: PrescriptionDrill) {
    var isExpanded by remember { mutableStateOf(false) }

    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D)),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, Color(0xFFBCD2FE).copy(alpha = 0.2f)),
        modifier = Modifier
            .fillMaxWidth()
            .animateContentSize(animationSpec = tween(300))
            .clickable { isExpanded = !isExpanded }
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        "CORRECTIVE DRILL",
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFF58FF63),
                        letterSpacing = 1.sp
                    )
                    Text(
                        drill.name,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Black,
                        color = Color.White
                    )
                }
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFF002A5E),
                    border = BorderStroke(1.dp, Color(0xFFBCD2FE).copy(alpha = 0.3f))
                ) {
                    Text(
                        if (isExpanded) "COLLAPSE ▲" else "VIEW SETUP ▼",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFBCD2FE)
                    )
                }
            }

            // Prescription badge always visible
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = Color(0xFF00142B),
                border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.25f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("🔄", fontSize = 12.sp)
                    Text(
                        "Prescription: ${drill.prescription}",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF58FF63)
                    )
                }
            }

            // Expanded Detail View
            if (isExpanded) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    // Setup
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("📍 SETUP", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color.Gray, letterSpacing = 1.sp)
                        Text(drill.setup, fontSize = 12.sp, color = Color.White, lineHeight = 16.sp)
                    }

                    // Execution
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("⚡ EXECUTION", fontSize = 9.sp, fontWeight = FontWeight.Bold, color = Color.Gray, letterSpacing = 1.sp)
                        Text(drill.execution, fontSize = 12.sp, color = Color(0xFFBCD2FE), lineHeight = 16.sp)
                    }

                    // Biomechanical Focus
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = Color(0xFF00224D).copy(alpha = 0.4f),
                        border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.15f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(10.dp)) {
                            Text("🎯 BIOMECHANICAL FOCUS", fontSize = 8.sp, fontWeight = FontWeight.Black, color = Color(0xFF58FF63), letterSpacing = 1.sp)
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(drill.biomechanicalFocus, fontSize = 11.sp, color = Color.White, lineHeight = 15.sp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun OptimalHealthCard() {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF002812)),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.4f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(20.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text("✅", fontSize = 28.sp)
            Column {
                Text(
                    "BIOMECHANICS IN HARMONY",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Black,
                    color = Color(0xFF58FF63),
                    letterSpacing = 1.sp
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    "No chronic hand coordination faults detected across your aggregated strokes. Wrist release timing and force ratios are operating within optimal coaching windows.",
                    fontSize = 11.sp,
                    color = Color.White.copy(alpha = 0.8f),
                    lineHeight = 16.sp
                )
            }
        }
    }
}

/**
 * Custom range visualizer displaying user IQR [P25, P75] and Median (P50) overlaid onto target green coaching zone.
 */
@Composable
fun MetricRangeVisualizer(
    metricTitle: String,
    distribution: MetricDistribution,
    targetMin: Float,
    targetMax: Float,
    axisMin: Float,
    axisMax: Float,
    formatValue: (Float) -> String
) {
    val axisSpan = (axisMax - axisMin).coerceAtLeast(1f)

    // Normalize coordinates (0.0f - 1.0f)
    fun norm(v: Float) = ((v - axisMin) / axisSpan).coerceIn(0.02f, 0.98f)

    val targetStartNorm = norm(targetMin)
    val targetEndNorm = norm(targetMax)
    val p25Norm = norm(distribution.p25)
    val p75Norm = norm(distribution.p75)
    val medianNorm = norm(distribution.median)

    val isMedianInTarget = distribution.median in targetMin..targetMax

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                metricTitle,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
            Text(
                "P50: ${formatValue(distribution.median)}",
                fontSize = 11.sp,
                fontWeight = FontWeight.Black,
                color = if (isMedianInTarget) Color(0xFF58FF63) else Color(0xFFFFB020)
            )
        }

        // Visualizer Canvas Bar
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(28.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0xFF000C1B))
                .border(1.dp, Color.White.copy(alpha = 0.06f), RoundedCornerShape(8.dp))
        ) {
            BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
                val totalWidth = maxWidth

                // 1. Green Target Coaching Zone
                val targetLeft = totalWidth * targetStartNorm
                val targetWidth = totalWidth * (targetEndNorm - targetStartNorm).coerceAtLeast(0.04f)

                Box(
                    modifier = Modifier
                        .offset(x = targetLeft)
                        .width(targetWidth)
                        .fillMaxHeight()
                        .background(Color(0xFF58FF63).copy(alpha = 0.18f))
                        .border(1.dp, Color(0xFF58FF63).copy(alpha = 0.45f))
                )

                // 2. User IQR Bar [P25 - P75]
                val iqrLeft = totalWidth * p25Norm
                val iqrWidth = totalWidth * (p75Norm - p25Norm).coerceAtLeast(0.03f)

                val userBarColor = if (isMedianInTarget) Color(0xFFBCD2FE).copy(alpha = 0.7f) else Color(0xFFFFB020).copy(alpha = 0.7f)

                Box(
                    modifier = Modifier
                        .offset(x = iqrLeft)
                        .width(iqrWidth)
                        .height(10.dp)
                        .align(Alignment.CenterStart)
                        .clip(RoundedCornerShape(3.dp))
                        .background(userBarColor)
                )

                // 3. User Median Indicator Line (P50)
                val medianLeft = totalWidth * medianNorm

                Box(
                    modifier = Modifier
                        .offset(x = medianLeft - 2.dp)
                        .width(4.dp)
                        .height(18.dp)
                        .align(Alignment.CenterStart)
                        .clip(RoundedCornerShape(2.dp))
                        .background(if (isMedianInTarget) Color(0xFF58FF63) else Color(0xFFFFB020))
                )
            }
        }

        // Subtext showing Target Range vs User IQR
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                "Target: ${formatValue(targetMin)} to ${formatValue(targetMax)}",
                fontSize = 9.sp,
                color = Color(0xFF58FF63).copy(alpha = 0.8f)
            )
            Text(
                "IQR [P25-P75]: ${formatValue(distribution.p25)} to ${formatValue(distribution.p75)}",
                fontSize = 9.sp,
                color = Color.Gray
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Generic Section Headers & Utilities
// ─────────────────────────────────────────────────────────────────────────────

@Composable
fun SectionHeader(title: String, subtitle: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 4.dp, bottom = 2.dp)
    ) {
        Text(
            text = title,
            fontSize = 13.sp,
            fontWeight = FontWeight.Black,
            color = Color.White,
            letterSpacing = 1.sp
        )
        Text(
            text = subtitle,
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color(0xFFBCD2FE).copy(alpha = 0.7f),
            letterSpacing = 0.5.sp
        )
    }
}

@Composable
fun InsufficientClassesFooter(insufficientClasses: Map<String, Int>) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D).copy(alpha = 0.5f)),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.05f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                "ADDITIONAL STROKES CALIBRATING (N < 5)",
                fontSize = 9.sp,
                fontWeight = FontWeight.Black,
                color = Color(0xFFBCD2FE),
                letterSpacing = 1.sp
            )
            insufficientClasses.forEach { (shotClass, count) ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(shotClass, fontSize = 11.sp, color = Color.White)
                    Text("$count/5 shots", fontSize = 10.sp, color = Color.Gray)
                }
            }
        }
    }
}

@Composable
fun InsufficientDataCard(
    totalShots: Int,
    insufficientClasses: Map<String, Int>,
    onStartSession: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001B3D).copy(alpha = 0.6f)),
        shape = RoundedCornerShape(22.dp),
        border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.2f)),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Text("📊", fontSize = 44.sp)
            Text(
                "CALIBRATING REPERTOIRE BASELINE",
                fontSize = 13.sp,
                fontWeight = FontWeight.Black,
                color = Color.White,
                letterSpacing = 1.sp,
                textAlign = TextAlign.Center
            )
            Text(
                "The Longitudinal Insights Engine requires at least 5 logged shots per stroke family to generate statistical distributions and technical insights.",
                fontSize = 12.sp,
                color = Color(0xFFBCD2FE).copy(alpha = 0.8f),
                textAlign = TextAlign.Center,
                lineHeight = 17.sp
            )

            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFF00142B),
                border = BorderStroke(1.dp, Color.White.copy(alpha = 0.06f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        "CALIBRATION PROGRESS ($totalShots/5 total shots)",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFF58FF63),
                        letterSpacing = 1.sp
                    )
                    LinearProgressIndicator(
                        progress = { (totalShots / 5f).coerceIn(0f, 1f) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = Color(0xFF58FF63),
                        trackColor = Color(0xFF00224D)
                    )
                    if (insufficientClasses.isNotEmpty()) {
                        Text(
                            "Logged so far: " + insufficientClasses.entries.joinToString(", ") { "${it.key} (${it.value}/5)" },
                            fontSize = 10.sp,
                            color = Color(0xFFBCD2FE).copy(alpha = 0.9f)
                        )
                    }
                    Text(
                        "Record net sessions to build your longitudinal repertoire and unlock deep stroke insights.",
                        fontSize = 10.sp,
                        color = Color.Gray,
                        lineHeight = 14.sp
                    )
                }
            }

            Button(
                onClick = onStartSession,
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF58FF63),
                    contentColor = Color(0xFF000C1B)
                ),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth().height(44.dp)
            ) {
                Text(
                    "RECORD SESSION",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = 1.sp
                )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ── Kinematic Coaching Target Ranges Mapping
// ─────────────────────────────────────────────────────────────────────────────

data class TargetRangeQuadruple(val targetMin: Float, val targetMax: Float, val minAxis: Float, val maxAxis: Float)

fun getTimeLeadRanges(shotClass: String): TargetRangeQuadruple {
    return when (shotClass) {
        "PULL/HOOK" -> TargetRangeQuadruple(-30f, -10f, -60f, +60f)
        "DRIVE/DEFENCE" -> TargetRangeQuadruple(+5f, +20f, -30f, +120f)
        "GLANCE/FLICK" -> TargetRangeQuadruple(-15f, -5f, -40f, +40f)
        "CUT/PUNCH" -> TargetRangeQuadruple(-5f, +5f, -30f, +40f)
        "DEFLECTION/GUIDE" -> TargetRangeQuadruple(+15f, +40f, -10f, +80f)
        "POWER DRIVE" -> TargetRangeQuadruple(-10f, 0f, -40f, +50f)
        "SLOG" -> TargetRangeQuadruple(-25f, -5f, -60f, +40f)
        "SWEEP" -> TargetRangeQuadruple(-10f, +5f, -40f, +50f)
        else -> TargetRangeQuadruple(-15f, +15f, -50f, +50f)
    }
}

fun getGyroRatioRanges(shotClass: String): TargetRangeQuadruple {
    return when (shotClass) {
        "PULL/HOOK" -> TargetRangeQuadruple(0.05f, 0.22f, 0.0f, 0.60f)
        "DRIVE/DEFENCE" -> TargetRangeQuadruple(0.45f, 0.70f, 0.0f, 1.20f)
        "GLANCE/FLICK" -> TargetRangeQuadruple(1.00f, 1.60f, 0.40f, 2.00f)
        "CUT/PUNCH" -> TargetRangeQuadruple(0.90f, 1.10f, 0.40f, 1.60f)
        "DEFLECTION/GUIDE" -> TargetRangeQuadruple(0.15f, 0.40f, 0.0f, 0.80f)
        "POWER DRIVE" -> TargetRangeQuadruple(1.10f, 1.60f, 0.50f, 2.00f)
        "SLOG" -> TargetRangeQuadruple(1.75f, 2.50f, 0.80f, 3.00f)
        "SWEEP" -> TargetRangeQuadruple(1.05f, 1.30f, 0.50f, 1.80f)
        else -> TargetRangeQuadruple(0.50f, 1.50f, 0.0f, 2.00f)
    }
}

fun getAccRatioRanges(shotClass: String): TargetRangeQuadruple {
    return when (shotClass) {
        "PULL/HOOK" -> TargetRangeQuadruple(1.20f, 2.00f, 0.50f, 2.50f)
        "DRIVE/DEFENCE" -> TargetRangeQuadruple(0.30f, 0.60f, 0.0f, 1.20f)
        "GLANCE/FLICK" -> TargetRangeQuadruple(0.80f, 1.30f, 0.40f, 1.80f)
        "CUT/PUNCH" -> TargetRangeQuadruple(0.85f, 1.15f, 0.40f, 1.60f)
        "DEFLECTION/GUIDE" -> TargetRangeQuadruple(0.10f, 0.25f, 0.0f, 0.60f)
        "POWER DRIVE" -> TargetRangeQuadruple(1.10f, 1.80f, 0.50f, 2.20f)
        "SLOG" -> TargetRangeQuadruple(1.50f, 2.20f, 0.80f, 2.80f)
        "SWEEP" -> TargetRangeQuadruple(0.90f, 1.20f, 0.40f, 1.60f)
        else -> TargetRangeQuadruple(0.50f, 1.50f, 0.0f, 2.00f)
    }
}
