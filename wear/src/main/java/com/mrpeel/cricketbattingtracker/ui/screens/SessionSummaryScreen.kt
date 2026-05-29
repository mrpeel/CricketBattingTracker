package com.mrpeel.cricketbattingtracker.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Sync
import androidx.compose.runtime.Composable
import androidx.compose.animation.core.*
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.material.*
import androidx.activity.compose.BackHandler

@Composable
fun SessionSummaryScreen(
    avgSpeed: Float,
    maxSpeed: Float,
    shotCount: Int,
    excellent: Int,
    good: Int,
    poor: Int,
    lastSpeed: Float,
    lastRating: String,
    lastEfficiency: Float,
    lastType: String,
    lastImpactTimeMs: Long,
    lastFollowThroughAngle: Float,
    lastWristRollDeg: Float,
    isFacingUp: Boolean,
    onBackPressed: () -> Unit
) {
    // Intercept physical bottom watch button press
    BackHandler(enabled = true) {
        onBackPressed()
    }

    // Brand Colors
    val neonGreen = Color(0xFF58FF63)
    val iceBlue = Color(0xFFBCD2FE)
    val navySurface = Color(0xFF001B3D)

    // Map Rating to Color
    val ratingColor = when (lastRating) {
        "Excellent" -> neonGreen
        "Good" -> Color(0xFF2196F3)
        "Poor" -> Color(0xFFFF5252)
        else -> iceBlue
    }

    // Pulse animation for Facing Up indicator
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val alphaPulse by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "alpha"
    )

    // ---- PAGE 1: Last shot glanceable view ----
    // Layout is a single Box that fills the circle.
    // Designed to show everything without scrolling.
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        contentAlignment = Alignment.Center
    ) {
        // ── 1. Top Section: Shot Type / Facing Up Status ──────────────────
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 10.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(
                    if (isFacingUp) neonGreen.copy(alpha = alphaPulse)
                    else ratingColor.copy(alpha = 0.2f)
                )
                .padding(horizontal = 10.dp, vertical = 2.dp)
        ) {
            Text(
                text = if (isFacingUp) "FACING UP" else lastType.uppercase(),
                color = if (isFacingUp) Color.Black else ratingColor,
                fontSize = 10.sp,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = 1.sp
            )
        }

        // ── 2. Center Section: The Core Ring (Enlarged) ─────────────────
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier
                .size(102.dp)
                .clickable { onBackPressed() }
        ) {
            Canvas(modifier = Modifier.matchParentSize()) {
                val strokeWidth = 6.dp.toPx()
                drawArc(
                    color = Color.White.copy(alpha = 0.1f),
                    startAngle = 135f,
                    sweepAngle = 270f,
                    useCenter = false,
                    style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                )
                val progress = (lastEfficiency / 100f).coerceIn(0.01f, 1f)
                drawArc(
                    brush = Brush.sweepGradient(
                        0.35f to ratingColor.copy(alpha = 0.4f),
                        0.75f to ratingColor
                    ),
                    startAngle = 135f,
                    sweepAngle = 270f * progress,
                    useCenter = false,
                    style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                )
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = String.format("%.0f", lastSpeed),
                    color = Color.White,
                    fontSize = 38.sp,
                    fontWeight = FontWeight.Black
                )
                Text(
                    text = lastRating.uppercase(),
                    color = ratingColor,
                    fontSize = 9.sp,
                    fontWeight = FontWeight.ExtraBold
                )
                Text(
                    text = "#$shotCount",
                    color = Color.White.copy(alpha = 0.5f),
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        // ── 3. Side Quadrants: React & Efficiency ──────────────────────
        // Left: REACT (Time to Impact)
        Box(modifier = Modifier.align(Alignment.CenterStart).padding(start = 6.dp)) {
            MiniStat("REACT", "${lastImpactTimeMs}ms", iceBlue)
        }
        // Right: EFF (Efficiency)
        Box(modifier = Modifier.align(Alignment.CenterEnd).padding(end = 6.dp)) {
            MiniStat("EFF", "${String.format("%.0f", lastEfficiency)}%", neonGreen)
        }

        // ── 4. Lower Quadrants: Wrist & Finish (Shifted up slightly for bottom arc) ──
        Row(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 54.dp)
                .fillMaxWidth(0.9f),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            MiniStat("WRIST", "${String.format("%.0f", lastWristRollDeg)}°", iceBlue)
            MiniStat("FINISH", "${String.format("%.0f", lastFollowThroughAngle)}°", iceBlue)
        }

        // ── 5. Footer: Session Aggregates (SYNC button removed, stats enlarged) ──
        Column(
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Row(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(navySurface.copy(alpha = 0.6f))
                    .padding(horizontal = 12.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("AVG: ${String.format("%.0f", avgSpeed)}", color = iceBlue, fontSize = 10.sp, fontWeight = FontWeight.Black)
                Text("MAX: ${String.format("%.0f", maxSpeed)}", color = neonGreen, fontSize = 10.sp, fontWeight = FontWeight.Black)
            }
        }
    }
}

// Small 3-line stat: label / value
@Composable
fun MiniStat(label: String, value: String, color: Color) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(Color(0xFF001B3D))
            .padding(horizontal = 6.dp, vertical = 3.dp)
    ) {
        Text(
            text = label,
            color = color.copy(alpha = 0.6f),
            fontSize = 7.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.2.sp
        )
        Text(
            text = value,
            color = Color.White,
            fontSize = 11.sp,
            fontWeight = FontWeight.Black
        )
    }
}

@Composable
fun SummaryStat(label: String, value: String, color: Color) {
    val iceBlue = Color(0xFFBCD2FE)
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = iceBlue.copy(alpha = 0.5f), fontSize = 8.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 14.sp, fontWeight = FontWeight.Black)
    }
}

@Composable
fun StatPill(label: String, count: Int, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = color, fontSize = 9.sp, fontWeight = FontWeight.Black)
        Text("$count", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}
