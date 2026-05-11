package com.mrpeel.cricketbattingtracker.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Sync
import androidx.compose.runtime.Composable
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
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn

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
    onSyncClick: () -> Unit
) {
    val misses = shotCount - (excellent + good + poor)
    
    // Brand Colors
    val neonGreen = Color(0xFF58FF63)
    val iceBlue = Color(0xFFBCD2FE)
    val navyDark = Color(0xFF000C1B)
    val navySurface = Color(0xFF001B3D)

    // Map Rating to Color
    val ratingColor = when (lastRating) {
        "Excellent" -> neonGreen
        "Good" -> Color(0xFF2196F3)
        "Poor" -> Color(0xFFFF5252)
        else -> iceBlue
    }

    // ---- PAGE 1: Last shot glanceable view ----
    // Layout is a single Box that fills the circle.
    // Designed to show everything without scrolling.
    ScalingLazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(navyDark),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(3.dp),
        contentPadding = PaddingValues(
            // Inset top/bottom enough to keep content in the circular safe area
            top = 20.dp,
            bottom = 20.dp,
            start = 8.dp,
            end = 8.dp
        )
    ) {

        // ── Row 1: Shot type badge ─────────────────────────────────────
        item {
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(10.dp))
                    .background(ratingColor.copy(alpha = 0.18f))
                    .padding(horizontal = 10.dp, vertical = 2.dp)
            ) {
                Text(
                    text = lastType.uppercase(),
                    color = ratingColor,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = 0.8.sp
                )
            }
        }

        // ── Row 2: Speed ring with rating label inside ─────────────────
        item {
            Box(contentAlignment = Alignment.Center, modifier = Modifier.size(84.dp)) {
                Canvas(modifier = Modifier.matchParentSize()) {
                    val strokeWidth = 7.dp.toPx()

                    // Track background
                    drawArc(
                        color = Color.White.copy(alpha = 0.06f),
                        startAngle = 130f,
                        sweepAngle = 280f,
                        useCenter = false,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                    // Efficiency progress arc colored by rating
                    val progress = (lastEfficiency / 100f).coerceIn(0.01f, 1f)
                    drawArc(
                        brush = Brush.sweepGradient(
                            0f to ratingColor.copy(alpha = 0.3f),
                            progress to ratingColor
                        ),
                        startAngle = 130f,
                        sweepAngle = 280f * progress,
                        useCenter = false,
                        style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
                    )
                }

                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = String.format("%.0f", lastSpeed),
                        color = Color.White,
                        fontSize = 30.sp,
                        fontWeight = FontWeight.Black,
                        lineHeight = 30.sp
                    )
                    Text(
                        text = "KM/H",
                        color = ratingColor,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 1.sp
                    )
                }
            }
        }

        // ── Row 3: Rating + Efficiency inline ──────────────────────────
        item {
            Row(
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(0.9f)
            ) {
                Text(
                    text = lastRating.uppercase(),
                    color = ratingColor,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = 0.5.sp
                )
                Text(
                    text = "  ·  ${String.format("%.0f", lastEfficiency)}% EFF",
                    color = iceBlue.copy(alpha = 0.7f),
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        // ── Row 4: 4 metrics in a single horizontal row ────────────────
        item {
            Row(
                modifier = Modifier.fillMaxWidth(0.92f),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                MiniStat("REACT", "${lastImpactTimeMs}ms", iceBlue)
                MiniStat("WRIST", "${String.format("%.0f", lastWristRollDeg)}°", iceBlue)
                MiniStat("FINISH", "${String.format("%.0f", lastFollowThroughAngle)}°", iceBlue)
            }
        }

        // ── Row 5: Session summary ──────────────────────────────────────
        item {
            Row(
                modifier = Modifier
                    .fillMaxWidth(0.88f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(navySurface.copy(alpha = 0.7f))
                    .padding(vertical = 5.dp, horizontal = 4.dp),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                SummaryStat("AVG", "${String.format("%.0f", avgSpeed)}", iceBlue)
                SummaryStat("MAX", "${String.format("%.0f", maxSpeed)}", neonGreen)
                SummaryStat("SHOTS", "$shotCount", Color.White)
                SummaryStat("⭐", "$excellent", neonGreen)
            }
        }

        // ── Row 6: End session button ───────────────────────────────────
        item {
            Button(
                onClick = onSyncClick,
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = neonGreen,
                    contentColor = navyDark
                ),
                modifier = Modifier
                    .fillMaxWidth(0.75f)
                    .height(34.dp),
                shape = RoundedCornerShape(17.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(imageVector = Icons.Default.Sync, contentDescription = null, modifier = Modifier.size(13.dp))
                    Spacer(modifier = Modifier.width(5.dp))
                    Text("SYNC", fontSize = 11.sp, fontWeight = FontWeight.Black)
                }
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
            .clip(RoundedCornerShape(8.dp))
            .background(Color(0xFF001B3D))
            .padding(horizontal = 5.dp, vertical = 4.dp)
    ) {
        Text(
            text = label,
            color = color.copy(alpha = 0.6f),
            fontSize = 7.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.3.sp,
            textAlign = TextAlign.Center
        )
        Text(
            text = value,
            color = Color.White,
            fontSize = 11.sp,
            fontWeight = FontWeight.Black,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
fun SummaryStat(label: String, value: String, color: Color) {
    val iceBlue = Color(0xFFBCD2FE)
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = iceBlue.copy(alpha = 0.5f), fontSize = 7.sp, fontWeight = FontWeight.Bold)
        Text(value, color = color, fontSize = 13.sp, fontWeight = FontWeight.Black)
    }
}

@Composable
fun StatPill(label: String, count: Int, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = color, fontSize = 9.sp, fontWeight = FontWeight.Black)
        Text("$count", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}
