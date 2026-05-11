package com.mrpeel.cricketbattingtracker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : ComponentActivity() {

    private val viewModel: InningsViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            val timeline by viewModel.currentTimeline.collectAsState()
            
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF58FF63),      // Neon green
                    secondary = Color(0xFFBCD2FE),   // Ice blue
                    background = Color(0xFF000C1B),  // Deep navy
                    surface = Color(0xFF001B3D),     // Navy surface
                    onBackground = Color.White,
                    onSurface = Color.White,
                    onPrimary = Color(0xFF000C1B)
                )
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    Column(modifier = Modifier.fillMaxSize()) {
                        TopBar()
                        if (timeline.isEmpty()) {
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                                    Spacer(modifier = Modifier.height(16.dp))
                                    Text("Waiting for Watch Sync...", color = Color.Gray, fontSize = 14.sp)
                                }
                            }
                        } else {
                            DashboardSummary(timeline)
                            Text(
                                "SESSION TIMELINE",
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Black,
                                color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.6f),
                                letterSpacing = 2.sp
                            )
                            TimelineList(timeline)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun TopBar() {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier
            .fillMaxWidth()
            .height(72.dp)
            .padding(bottom = 1.dp)
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
    ) {
        Row(
            modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(
                    "PITCH ANALYTIX",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.primary,
                    letterSpacing = 1.sp
                )
                Text(
                    "PRO PERFORMANCE TRACKER",
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.7f)
                )
            }
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center
            ) {
                Text("NK", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun DashboardSummary(events: List<InningsEvent>) {
    val maxBatSpeed = events.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
    val avgEfficiency = events.mapNotNull { it.efficiency }.average().let { if (it.isNaN()) 0.0 else it }
    val shotCount = events.count { it.description.contains("Shot") || it.shotType != null }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        SummaryCard("MAX SPEED", "${maxBatSpeed.toInt()}", "KM/H", Modifier.weight(1f))
        SummaryCard("AVG EFF", "${avgEfficiency.toInt()}", "%", Modifier.weight(1f))
        SummaryCard("SHOTS", "$shotCount", "COUNT", Modifier.weight(1f))
    }
}

@Composable
fun SummaryCard(title: String, value: String, unit: String, modifier: Modifier = Modifier) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = modifier.height(110.dp),
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(12.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Text(title, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color.Gray, letterSpacing = 1.sp)
            Row(verticalAlignment = Alignment.Bottom) {
                Text(value, fontSize = 32.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(4.dp))
                Text(unit, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.secondary, modifier = Modifier.padding(bottom = 6.dp))
            }
        }
    }
}

@Composable
fun TimelineList(events: List<InningsEvent>) {
    val formatter = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        items(events.reversed()) { event ->
            TimelineItem(event, formatter)
        }
    }
}

@Composable
fun TimelineItem(event: InningsEvent, formatter: SimpleDateFormat) {
    val isHit = !event.description.contains("Miss")
    val accentColor = if (isHit) MaterialTheme.colorScheme.primary else Color(0xFFFF5252)

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f)),
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, accentColor.copy(alpha = 0.2f))
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(40.dp)
                    .clip(CircleShape)
                    .background(accentColor)
            )
            
            Spacer(modifier = Modifier.width(16.dp))
            
            Column(modifier = Modifier.weight(1f)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(
                        event.shotType?.uppercase() ?: "ACTION",
                        fontWeight = FontWeight.Black,
                        fontSize = 14.sp,
                        color = Color.White,
                        letterSpacing = 0.5.sp
                    )
                    Text(
                        formatter.format(Date(event.timestamp)),
                        fontSize = 11.sp,
                        color = Color.Gray
                    )
                }
                
                Text(
                    event.description,
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.6f)
                )

                if (event.batSpeed != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    // First row: Speed, Efficiency, Impact Time
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        MetricSmall("SPEED", "${event.batSpeed.toInt()} km/h")
                        if (event.efficiency != null) {
                            MetricSmall("EFF", "${event.efficiency.toInt()}%")
                        }
                        if (event.impactTimeMs != null) {
                            MetricSmall("REACT", "${event.impactTimeMs} ms")
                        }
                    }
                    // Second row: Wrist Roll, Follow-Through Angle
                    if (event.wristRollDeg != null || event.followThroughAngle != null) {
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            if (event.wristRollDeg != null) {
                                MetricSmall("WRIST", "${String.format("%.0f", event.wristRollDeg)}°")
                            }
                            if (event.followThroughAngle != null) {
                                MetricSmall("FINISH", "${String.format("%.0f", event.followThroughAngle)}°")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MetricSmall(label: String, value: String) {
    Column {
        Text(label, fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
        Text(value, fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color(0xFFBCD2FE))
    }
}
