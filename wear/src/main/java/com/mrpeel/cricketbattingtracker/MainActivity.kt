package com.mrpeel.cricketbattingtracker

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.wear.compose.navigation.SwipeDismissableNavHost
import androidx.wear.compose.navigation.composable
import androidx.wear.compose.navigation.rememberSwipeDismissableNavController
import com.mrpeel.cricketbattingtracker.services.SessionManager
import com.mrpeel.cricketbattingtracker.services.TrackerService
import com.mrpeel.cricketbattingtracker.ui.screens.SessionSummaryScreen
import com.mrpeel.cricketbattingtracker.ui.screens.StartSessionScreen
import com.mrpeel.cricketbattingtracker.ui.screens.SessionActionsScreen
import com.mrpeel.cricketbattingtracker.ui.screens.DiscardConfirmationScreen
import com.mrpeel.cricketbattingtracker.ui.theme.PavilionTheme
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import android.content.pm.PackageManager
import android.Manifest

class MainActivity : ComponentActivity() {

    private val requestBackgroundPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            android.widget.Toast.makeText(this, "Background sensor access is recommended for tracking when screen is off.", android.widget.Toast.LENGTH_LONG).show()
        }
    }

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val bodySensorsGranted = permissions[Manifest.permission.BODY_SENSORS] ?: false
        val activityRecGranted = permissions[Manifest.permission.ACTIVITY_RECOGNITION] ?: false
        val postNotificationsGranted = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            permissions[Manifest.permission.POST_NOTIFICATIONS] ?: false
        } else {
            true
        }
        
        if (!bodySensorsGranted || !activityRecGranted || !postNotificationsGranted) {
            android.widget.Toast.makeText(this, "Permissions are required for session tracking.", android.widget.Toast.LENGTH_LONG).show()
        } else {
            checkAndRequestBackgroundPermission()
        }
    }

    private fun checkAndRequestPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.BODY_SENSORS,
            Manifest.permission.ACTIVITY_RECOGNITION
        )
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        
        val needsRequest = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (needsRequest.isNotEmpty()) {
            requestPermissionLauncher.launch(needsRequest.toTypedArray())
        } else {
            checkAndRequestBackgroundPermission()
        }
    }

    private fun checkAndRequestBackgroundPermission() {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BODY_SENSORS_BACKGROUND) != PackageManager.PERMISSION_GRANTED) {
                requestBackgroundPermissionLauncher.launch(Manifest.permission.BODY_SENSORS_BACKGROUND)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        checkAndRequestPermissions()
        
        // Keep the screen on during the tracking session so we don't drop to ambient watch face
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            window.addFlags(
                android.view.WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                android.view.WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
            )
        }

        setContent {
            PavilionTheme {
                val navController = rememberSwipeDismissableNavController()
                
                // Collect states from SessionManager securely
                val isTracking = SessionManager.isTracking.collectAsState()
                val shotCount = SessionManager.shotCount.collectAsState()
                val avgSpeed = SessionManager.avgSpeed.collectAsState()
                val maxSpeed = SessionManager.maxSpeed.collectAsState()
                
                val excellentShots = SessionManager.excellentShots.collectAsState()
                val goodShots = SessionManager.goodShots.collectAsState()
                val poorShots = SessionManager.poorShots.collectAsState()
                val lastShotSpeed = SessionManager.lastShotSpeed.collectAsState()
                val lastShotRating = SessionManager.lastShotRating.collectAsState()
                val lastShotEfficiency = SessionManager.lastShotEfficiency.collectAsState()
                val lastShotType = SessionManager.lastShotType.collectAsState()
                val lastImpactTimeMs = SessionManager.lastImpactTimeMs.collectAsState()
                val lastFollowThroughAngle = SessionManager.lastFollowThroughAngle.collectAsState()
                val lastWristRollDeg = SessionManager.lastWristRollDeg.collectAsState()

                // Automatically navigate based on tracking state
                LaunchedEffect(isTracking.value) {
                    if (isTracking.value) {
                        if (navController.currentDestination?.route == "start") {
                            navController.navigate("summary") {
                                popUpTo("start") { inclusive = true }
                            }
                        }
                    } else {
                        val currentRoute = navController.currentDestination?.route
                        if (currentRoute == "summary" || currentRoute == "actions" || currentRoute == "confirm_discard") {
                            navController.navigate("start") {
                                popUpTo("start") { inclusive = true }
                            }
                        }
                    }
                }

                SwipeDismissableNavHost(
                    navController = navController,
                    startDestination = "start"
                ) {
                    composable("start") {
                        StartSessionScreen(
                            onStartClick = { isDebug ->
                                startTrackerService(isDebug)
                                navController.navigate("summary")
                            }
                        )
                    }
                    
                    composable("summary") {
                        SessionSummaryScreen(
                            avgSpeed = avgSpeed.value,
                            maxSpeed = maxSpeed.value,
                            shotCount = shotCount.value,
                            excellent = excellentShots.value,
                            good = goodShots.value,
                            poor = poorShots.value,
                            lastSpeed = lastShotSpeed.value,
                            lastRating = lastShotRating.value,
                            lastEfficiency = lastShotEfficiency.value,
                            lastType = lastShotType.value,
                            lastImpactTimeMs = lastImpactTimeMs.value,
                            lastFollowThroughAngle = lastFollowThroughAngle.value,
                            lastWristRollDeg = lastWristRollDeg.value,
                            onBackPressed = {
                                navController.navigate("actions")
                            }
                        )
                    }

                    composable("actions") {
                        SessionActionsScreen(
                            onSyncClick = {
                                stopTrackerService()
                                SessionManager.resetSession()
                                navController.navigate("start") {
                                    popUpTo("start") { inclusive = true }
                                }
                            },
                            onDiscardClick = {
                                navController.navigate("confirm_discard")
                            }
                        )
                    }

                    composable("confirm_discard") {
                        DiscardConfirmationScreen(
                            onYesClick = {
                                stopTrackerServiceWithoutSync()
                                SessionManager.resetSession()
                                navController.navigate("start") {
                                    popUpTo("start") { inclusive = true }
                                }
                            },
                            onNoClick = {
                                navController.navigate("summary") {
                                    popUpTo("summary") { inclusive = true }
                                }
                            }
                        )
                    }
                }
            }
        }
    }

    private fun startTrackerService(enableRawLogging: Boolean) {
        val intent = Intent(this, TrackerService::class.java)
        intent.putExtra("ENABLE_RAW_LOGGING", enableRawLogging)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopTrackerService() {
        val intent = Intent(this, TrackerService::class.java)
        intent.action = "STOP_TRACKING"
        startService(intent)
    }

    private fun stopTrackerServiceWithoutSync() {
        val intent = Intent(this, TrackerService::class.java)
        intent.action = "DISCARD_TRACKING"
        startService(intent)
    }
}
