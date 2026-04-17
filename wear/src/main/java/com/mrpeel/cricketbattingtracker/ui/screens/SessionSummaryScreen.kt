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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.material.*
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import com.mrpeel.cricketbattingtracker.ui.theme.*

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
    onSyncClick: () -> Unit
) {
    val misses = shotCount - (excellent + good + poor)

    ScalingLazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(TrueBlack),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
        contentPadding = PaddingValues(top = 24.dp, bottom = 32.dp)
    ) {
        
        item {
            Text(
                text = "SESSION ACTIVE",
                color = LightBlueSecondary,
                style = MaterialTheme.typography.body2,
                fontSize = 11.sp,
                letterSpacing = 1.sp
            )
        }
        
        item {
            // Main Metric Ring
            Box(contentAlignment = Alignment.Center, modifier = Modifier.size(80.dp)) {
                Canvas(modifier = Modifier.matchParentSize()) {
                    // Background track
                    drawArc(
                        color = NavyAccent,
                        startAngle = 135f,
                        sweepAngle = 270f,
                        useCenter = false,
                        style = Stroke(width = 6.dp.toPx(), cap = StrokeCap.Round)
                    )
                    
                    // Foregound progress (Clamp at 160f impact for full circle visual)
                    val progress = (avgSpeed / 160f).coerceIn(0.01f, 1f)
                    drawArc(
                        color = NeonGreen,
                        startAngle = 135f,
                        sweepAngle = 270f * progress,
                        useCenter = false,
                        style = Stroke(width = 6.dp.toPx(), cap = StrokeCap.Round)
                    )
                }
                
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "AVG SPEED",
                        color = NeonGreen,
                        fontSize = 8.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = String.format("%.1f", avgSpeed),
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(0.9f),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("MAX SPEED", color = LightBlueSecondary, fontSize = 10.sp)
                    Text(String.format("%.1f", maxSpeed), color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text("TOTAL SHOTS", color = NeonGreen, fontSize = 10.sp)
                    Text("$shotCount", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        
        item {
            // Sweet Spot Box
            Column(
                modifier = Modifier
                    .fillMaxWidth(0.85f)
                    .background(Color(0xFF111111), RoundedCornerShape(12.dp))
                    .padding(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("QUALITY BREAKDOWN", color = LightBlueSecondary, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("E", color = NeonGreen, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text("$excellent", color = Color.White, fontSize = 12.sp)
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("G", color = Color(0xFFFFB300), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text("$good", color = Color.White, fontSize = 12.sp)
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("P", color = Color(0xFFE53935), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text("$poor", color = Color.White, fontSize = 12.sp)
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("M", color = Color.Gray, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text("$misses", color = Color.White, fontSize = 12.sp)
                    }
                }
            }
        }

        item {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("LAST SHOT", color = LightBlueSecondary, fontSize = 10.sp)
                Text("${String.format("%.1f", lastSpeed)} km/h • $lastRating", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
            }
        }

        item {
            // Sync Action
            Button(
                onClick = onSyncClick,
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = DarkGray,
                    contentColor = NeonGreen
                ),
                modifier = Modifier
                    .fillMaxWidth(0.85f)
                    .height(36.dp),
                shape = RoundedCornerShape(18.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(imageVector = Icons.Default.Sync, contentDescription = "Sync", modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("SYNC & END", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        
    }
}
