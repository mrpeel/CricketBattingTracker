package com.mrpeel.cricketbattingtracker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Mock data for preview until sync is verified
        val mockTimeline = listOf(
            InningsEvent(1, 1, System.currentTimeMillis() - 600000, "Innings Started"),
            InningsEvent(2, 1, System.currentTimeMillis() - 500000, "Shot detected (Drive)", 65.4f, 20.1f),
            InningsEvent(3, 1, System.currentTimeMillis() - 400000, "Running between wickets", distanceRun = 18.0f),
            InningsEvent(4, 1, System.currentTimeMillis() - 300000, "Shot detected (Pull)", 72.1f, 35.0f),
            InningsEvent(5, 1, System.currentTimeMillis() - 200000, "Running between wickets", distanceRun = 36.0f),
            InningsEvent(6, 1, System.currentTimeMillis() - 100000, "Innings Ended")
        )

        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = Color(0xFF4CAF50),
                    background = Color(0xFF1E1E1E),
                    surface = Color(0xFF2C2C2C)
                )
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    Column(modifier = Modifier.fillMaxSize()) {
                        TopBar()
                        DashboardSummary(mockTimeline)
                        Spacer(modifier = Modifier.height(16.dp))
                        TimelineList(mockTimeline)
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
        modifier = Modifier.fillMaxWidth().height(64.dp)
    ) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.CenterStart) {
            Text(
                "Innings Review", 
                fontSize = 20.sp, 
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(start = 16.dp),
                color = Color.White
            )
        }
    }
}

@Composable
fun DashboardSummary(events: List<InningsEvent>) {
    val totalDistance = events.mapNotNull { it.distanceRun }.sum()
    val maxBatSpeed = events.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        horizontalArrangement = Arrangement.SpaceEvenly
    ) {
        SummaryCard("Distance", "\${totalDistance.toInt()}m")
        SummaryCard("Max Speed", "\${maxBatSpeed.toInt()} km/h")
        SummaryCard("Actions", "\${events.size}")
    }
}

@Composable
fun SummaryCard(title: String, value: String) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.size(100.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize().padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text(title, fontSize = 12.sp, color = Color.Gray)
            Spacer(modifier = Modifier.height(8.dp))
            Text(value, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
fun TimelineList(events: List<InningsEvent>) {
    val formatter = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        contentPadding = PaddingValues(bottom = 16.dp)
    ) {
        items(events) { event ->
            Row(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                // Timeline line & dot
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(modifier = Modifier.size(12.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primary))
                    Box(modifier = Modifier.width(2.dp).height(80.dp).background(Color.Gray.copy(alpha=0.3f)))
                }
                Spacer(modifier = Modifier.width(16.dp))
                // Card Content
                Card(
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(event.description, fontWeight = FontWeight.Bold, color = Color.White)
                            Text(formatter.format(Date(event.timestamp)), fontSize = 12.sp, color = Color.Gray)
                        }
                        
                        if (event.batSpeed != null) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("Speed: \${event.batSpeed} | Impact: \${event.impactForce}", fontSize = 12.sp, color = MaterialTheme.colorScheme.primary)
                        }
                        if (event.distanceRun != null) {
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("Distance tracked: \${event.distanceRun}m", fontSize = 12.sp, color = Color(0xFF2196F3))
                        }
                    }
                }
            }
        }
    }
}
