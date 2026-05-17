package com.mrpeel.cricketbattingtracker

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.data.HeartRateEvent
import com.mrpeel.cricketbattingtracker.services.HealthConnectManager
import java.text.SimpleDateFormat
import java.util.*
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.HealthConnectClient
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.window.Dialog
import android.content.Context

class MainActivity : ComponentActivity() {

    private val viewModel: InningsViewModel by viewModels()

    // Location permissions request launcher
    private val requestLocationPermissionLauncher = registerForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val fineGranted = permissions[android.Manifest.permission.ACCESS_FINE_LOCATION] ?: false
        val coarseGranted = permissions[android.Manifest.permission.ACCESS_COARSE_LOCATION] ?: false
        if (fineGranted || coarseGranted) {
            android.util.Log.d("MainActivity", "Location permissions granted successfully!")
        } else {
            android.util.Log.w("MainActivity", "Location permissions were denied.")
        }
    }

    // Register Health Connect permissions activity launcher contract
    private val requestPermissionActivityContract = PermissionController.createRequestPermissionResultContract()
    private val requestPermissions = registerForActivityResult(requestPermissionActivityContract) { granted ->
        if (granted.containsAll(setOf(
                HealthPermission.getWritePermission(ExerciseSessionRecord::class),
                HealthPermission.getWritePermission(HeartRateRecord::class),
                HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class),
                HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class)
            ))) {
            android.util.Log.d("MainActivity", "Health Connect permissions granted successfully!")
            syncSessionToHealthConnect(null)
        } else {
            android.util.Log.w("MainActivity", "Health Connect permissions were not fully granted.")
        }
    }

    override fun onResume() {
        super.onResume()
        checkHealthConnectPermissions()
    }

    private fun checkHealthConnectPermissions() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            try {
                if (HealthConnectClient.getSdkStatus(this) == HealthConnectClient.SDK_AVAILABLE) {
                    val healthConnectClient = HealthConnectClient.getOrCreate(this)
                    lifecycleScope.launch {
                        val permissions = setOf(
                            HealthPermission.getWritePermission(ExerciseSessionRecord::class),
                            HealthPermission.getWritePermission(HeartRateRecord::class),
                            HealthPermission.getWritePermission(TotalCaloriesBurnedRecord::class),
                            HealthPermission.getWritePermission(ActiveCaloriesBurnedRecord::class)
                        )
                        val granted = healthConnectClient.permissionController.getGrantedPermissions()
                        if (!granted.containsAll(permissions)) {
                            requestPermissions.launch(permissions)
                        } else {
                            android.util.Log.d("MainActivity", "Health Connect permissions already granted.")
                            syncSessionToHealthConnect(null)
                        }
                    }
                } else {
                    android.util.Log.i("MainActivity", "Health Connect is not available on this device.")
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Failed to check Health Connect permissions: ${e.message}")
            }
        }
    }

    fun syncSessionToHealthConnect(inningsId: Long? = null) {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val database = AppDatabase.getDatabase(applicationContext)
                val dao = database.inningsEventDao()
                val hcManager = HealthConnectManager(applicationContext)
                
                // Get list of already synced sessions from SharedPreferences
                val prefs = getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                val syncedIds = prefs.getStringSet("synced_innings_ids", emptySet())?.toMutableSet() ?: mutableSetOf()

                val targetIds = if (inningsId != null) {
                    listOf(inningsId)
                } else {
                    dao.getAllUniqueInningsIds()
                }

                var newlySyncedCount = 0
                for (id in targetIds) {
                    if (inningsId == null && syncedIds.contains(id.toString())) {
                        continue // Skip already synced sessions when doing automatic full sync
                    }

                    val events = dao.getTimelineForInningsListSync(id)
                    if (events.isEmpty()) continue
                    
                    val shotEvents = events.filter { it.batSpeed != null }
                    val maxSpeed = shotEvents.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
                    val minTime = events.minOfOrNull { it.timestamp } ?: 0L
                    val maxTime = events.maxOfOrNull { it.timestamp } ?: 0L
                    val duration = if (maxTime > minTime) maxTime - minTime else (events.size * 5000L)
                    val endTime = if (maxTime > minTime) maxTime else (minTime + duration)
                    
                    val dbHeartRates = dao.getHeartRatesForInningsSync(id)
                    val realHeartRates = dbHeartRates.map { Pair(it.timestamp, it.beatsPerMinute) }

                    val success = hcManager.writeCricketWorkout(
                        startTimeMillis = minTime,
                        endTimeMillis = endTime,
                        shotCount = shotEvents.size,
                        maxSpeed = maxSpeed,
                        realHeartRates = realHeartRates
                    )

                    if (success) {
                        syncedIds.add(id.toString())
                        newlySyncedCount++
                    }
                }

                if (newlySyncedCount > 0) {
                    prefs.edit().putStringSet("synced_innings_ids", syncedIds).apply()
                    android.util.Log.d("MainActivity", "Successfully synced $newlySyncedCount new sessions to Health Connect!")
                    withContext(Dispatchers.Main) {
                        Toast.makeText(this@MainActivity, "Synced $newlySyncedCount new session(s) to Health Connect!", Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("MainActivity", "Failed syncing sessions to Health Connect: ${e.message}")
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        requestLocationPermissionLauncher.launch(
            arrayOf(
                android.Manifest.permission.ACCESS_FINE_LOCATION,
                android.Manifest.permission.ACCESS_COARSE_LOCATION
            )
        )
        
        checkHealthConnectPermissions()

        setContent {
            val timeline by viewModel.currentTimeline.collectAsState()
            val allSessions by viewModel.allSessions.collectAsState()
            val selectedSessionId by viewModel.selectedInningsId.collectAsState()
            
            // Athlete Profile preference state management
            var showProfileDialog by remember { mutableStateOf(false) }
            val prefs = remember { getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE) }
            var userName by remember { mutableStateOf(prefs.getString("user_name", "Neil Kloot") ?: "Neil Kloot") }
            var userWeight by remember { mutableStateOf(prefs.getFloat("user_weight", 80.0f)) }
            var userAge by remember { mutableStateOf(prefs.getInt("user_age", 35)) }
            var userGender by remember { mutableStateOf(prefs.getString("user_gender", "Male") ?: "Male") }

            // Compute dynamic uppercase initials from name
            val initials = remember(userName) {
                userName.split(" ")
                    .filter { it.isNotEmpty() }
                    .take(2)
                    .map { it.first().uppercaseChar() }
                    .joinToString("")
                    .let { if (it.isEmpty()) "PA" else it }
            }

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
                        if (selectedSessionId == null) {
                            // HOME SCREEN
                            TopBar(
                                title = "PITCH ANALYTIX", 
                                subtitle = "SESSIONS HISTORY", 
                                showBack = false, 
                                onBack = {},
                                initials = initials,
                                onProfileClick = { showProfileDialog = true }
                            )
                            
                            // Cumulative Career Statistics
                            val careerMaxSpeed = allSessions.map { it.maxSpeed }.maxOrNull() ?: 0f
                            val totalShots = allSessions.sumOf { it.totalShots }
                            
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(16.dp),
                                horizontalArrangement = Arrangement.spacedBy(12.dp)
                            ) {
                                SummaryCard("CAREER MAX", "${careerMaxSpeed.toInt()}", "KM/H", Modifier.weight(1f))
                                SummaryCard("SHOTS", "$totalShots", "COUNT", Modifier.weight(1f))
                                SummaryCard("SESSIONS", "${allSessions.size}", "COUNT", Modifier.weight(1f))
                            }
                            
                            Text(
                                "HISTORY LIST",
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Black,
                                color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.6f),
                                letterSpacing = 2.sp
                            )
                            
                            if (allSessions.isEmpty()) {
                                Card(
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.4f)),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(16.dp),
                                    shape = RoundedCornerShape(24.dp),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
                                ) {
                                    Column(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(24.dp),
                                        horizontalAlignment = Alignment.CenterHorizontally,
                                        verticalArrangement = Arrangement.spacedBy(12.dp)
                                    ) {
                                        Text(
                                            "🏏",
                                            fontSize = 48.sp,
                                            modifier = Modifier.padding(bottom = 8.dp)
                                        )
                                        Text(
                                            "NO SESSIONS SYNCED YET",
                                            fontSize = 14.sp,
                                            fontWeight = FontWeight.Black,
                                            color = Color.White,
                                            letterSpacing = 1.sp
                                        )
                                        Text(
                                            "Ready to track your innings? Open Pitch Analytix Pro on your Wear OS watch and start batting! Your shots, heart rate telemetry, and workout calories will automatically sync here.",
                                            fontSize = 12.sp,
                                            color = Color.Gray,
                                            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                                            lineHeight = 18.sp
                                        )
                                    }
                                }
                            } else {
                                LazyColumn(
                                    modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                                    contentPadding = PaddingValues(bottom = 24.dp),
                                    verticalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    items(allSessions) { session ->
                                        SessionHistoryCard(session) {
                                            viewModel.selectInnings(session.inningsId)
                                        }
                                    }
                                }
                            }
                        } else {
                            // DETAIL SCREEN
                            val selectedSession = allSessions.find { it.inningsId == selectedSessionId }
                            val startFormatted = selectedSession?.let {
                                SimpleDateFormat("d MMM HH:mm", Locale.getDefault()).format(Date(it.startTimeMillis))
                            } ?: ""
                            val rawLocation = selectedSession?.locationText ?: ""
                            val suburb = if (rawLocation.contains(",")) {
                                rawLocation.substringAfter(",").trim()
                            } else {
                                rawLocation.trim()
                            }
                            val subtitleText = if (startFormatted.isNotEmpty()) {
                                "$startFormatted • $suburb"
                            } else {
                                "INNINGS #${selectedSessionId}"
                            }

                            TopBar(
                                title = "SESSION DETAILS",
                                subtitle = subtitleText,
                                showBack = true,
                                onBack = { viewModel.selectInnings(null) },
                                initials = initials,
                                onProfileClick = { showProfileDialog = true }
                            )
                            
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
                    
                    if (showProfileDialog) {
                        ProfileDialog(
                            currentName = userName,
                            currentWeight = userWeight,
                            currentAge = userAge,
                            currentGender = userGender,
                            onDismiss = { showProfileDialog = false },
                            onSave = { name, weight, age, gender ->
                                userName = name
                                userWeight = weight
                                userAge = age
                                userGender = gender
                                prefs.edit().apply {
                                    putString("user_name", name)
                                    putFloat("user_weight", weight)
                                    putInt("user_age", age)
                                    putString("user_gender", gender)
                                    apply()
                                }
                                showProfileDialog = false
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun TopBar(title: String, subtitle: String, showBack: Boolean, onBack: () -> Unit, initials: String, onProfileClick: () -> Unit) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier
            .fillMaxWidth()
            .height(72.dp)
            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
    ) {
        Row(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (showBack) {
                    Box(
                        modifier = Modifier
                            .padding(end = 12.dp)
                            .size(36.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f))
                            .clickable { onBack() },
                        contentAlignment = Alignment.Center
                    ) {
                        Text("←", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Black, fontSize = 18.sp)
                    }
                }
                Column {
                    Text(
                        title,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.sp
                    )
                    Text(
                        subtitle,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.secondary.copy(alpha = 0.7f)
                    )
                }
            }
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f))
                    .clickable { onProfileClick() },
                contentAlignment = Alignment.Center
            ) {
                Text(initials, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun DashboardSummary(events: List<InningsEvent>) {
    val maxBatSpeed = events.mapNotNull { it.batSpeed }.maxOrNull() ?: 0f
    val avgEfficiency = events.mapNotNull { it.efficiency }.average().let { if (it.isNaN()) 0.0 else it }
    val shotCount = events.count { it.description.contains("Shot") || it.shotType != null }

    val minTime = events.minOfOrNull { it.timestamp } ?: 0L
    val maxTime = events.maxOfOrNull { it.timestamp } ?: 0L
    val durationMs = if (maxTime > minTime) maxTime - minTime else 0L
    val totalSecs = durationMs / 1000
    val mins = totalSecs / 60
    val secs = totalSecs % 60
    
    val durationVal = if (mins > 0) "$mins" else "$secs"
    val durationUnit = if (mins > 0) "MIN" else "SEC"

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            SummaryCard("MAX SPEED", "${maxBatSpeed.toInt()}", "KM/H", Modifier.weight(1f))
            SummaryCard("AVG EFF", "${avgEfficiency.toInt()}", "%", Modifier.weight(1f))
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            SummaryCard("SHOTS", "$shotCount", "COUNT", Modifier.weight(1f))
            SummaryCard("DURATION", durationVal, durationUnit, Modifier.weight(1f))
        }
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
fun SessionHistoryCard(session: SessionHistoryItem, onClick: () -> Unit) {
    val durationMs = session.endTimeMillis - session.startTimeMillis
    val totalSecs = durationMs / 1000
    val mins = totalSecs / 60
    val secs = totalSecs % 60
    val durationText = if (mins > 0) "${mins}m ${secs}s" else "${secs}s"
    val startFormatted = SimpleDateFormat("d MMM HH:mm", Locale.getDefault()).format(Date(session.startTimeMillis))

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.6f)),
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        shape = RoundedCornerShape(16.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.05f))
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    startFormatted,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Black,
                    color = Color.White
                )
                Text(
                    session.locationText,
                    fontSize = 11.sp,
                    color = Color.Gray
                )
                Spacer(modifier = Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column {
                        Text("SHOTS", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text("${session.totalShots}", fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                    Column {
                        Text("MAX SPEED", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text("${session.maxSpeed.toInt()} km/h", fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                    Column {
                        Text("AVG EFF", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text("${session.avgEfficiency.toInt()}%", fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                    Column {
                        Text("DURATION", fontSize = 8.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Text(durationText, fontSize = 12.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
            Text("→", fontSize = 18.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
fun HealthSyncBar(onSync: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF001F4D)),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f))
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)),
                    contentAlignment = Alignment.Center
                ) {
                    Text("❤️", fontSize = 14.sp)
                }
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text("Samsung Health Sync", fontSize = 12.sp, fontWeight = FontWeight.Black, color = Color.White)
                    Text("Keep workout and vitals linked", fontSize = 10.sp, color = Color.Gray)
                }
            }
            Button(
                onClick = { onSync() },
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.height(28.dp)
            ) {
                Text("Sync Now", fontSize = 10.sp, fontWeight = FontWeight.Black, color = Color(0xFF000C1B))
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
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        MetricSmall("SPEED", "${event.batSpeed.toInt()} km/h")
                        if (event.efficiency != null) {
                            MetricSmall("EFF", "${event.efficiency.toInt()}%")
                        }
                        if (event.impactTimeMs != null) {
                            MetricSmall("REACT", "${event.impactTimeMs} ms")
                        }
                    }
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileDialog(
    currentName: String,
    currentWeight: Float,
    currentAge: Int,
    currentGender: String,
    onDismiss: () -> Unit,
    onSave: (name: String, weight: Float, age: Int, gender: String) -> Unit
) {
    var name by remember { mutableStateOf(currentName) }
    var weightText by remember { mutableStateOf(currentWeight.toString()) }
    var ageText by remember { mutableStateOf(currentAge.toString()) }
    var gender by remember { mutableStateOf(currentGender) }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Color.White.copy(alpha = 0.1f))
        ) {
            Column(
                modifier = Modifier
                    .padding(24.dp)
                    .fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "ATHLETE BIO & PROFILE",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.primary,
                    letterSpacing = 1.sp
                )
                
                Text(
                    text = "Used for physiologically accurate dynamic Keytel energy expenditure tracking in Samsung Health.",
                    fontSize = 11.sp,
                    color = Color.Gray,
                    lineHeight = 16.sp
                )

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Name") },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        focusedLabelColor = MaterialTheme.colorScheme.primary
                    ),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedTextField(
                        value = ageText,
                        onValueChange = { ageText = it },
                        label = { Text("Age (yrs)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            focusedLabelColor = MaterialTheme.colorScheme.primary
                        ),
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )

                    OutlinedTextField(
                        value = weightText,
                        onValueChange = { weightText = it },
                        label = { Text("Weight (kg)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            focusedLabelColor = MaterialTheme.colorScheme.primary
                        ),
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )
                }

                Column(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "GENDER",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Gray,
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        listOf("Male", "Female").forEach { option ->
                            val isSelected = gender.equals(option, ignoreCase = true)
                            Button(
                                onClick = { gender = option },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (isSelected) MaterialTheme.colorScheme.primary else Color.White.copy(alpha = 0.05f),
                                    contentColor = if (isSelected) MaterialTheme.colorScheme.onPrimary else Color.White
                                ),
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text(option, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
                    ) {
                        Text("CANCEL")
                    }

                    Button(
                        onClick = {
                            val parsedWeight = weightText.toFloatOrNull() ?: currentWeight
                            val parsedAge = ageText.toIntOrNull() ?: currentAge
                            if (name.isNotBlank()) {
                                onSave(name, parsedWeight, parsedAge, gender)
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text("SAVE", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
