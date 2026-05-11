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
import com.mrpeel.cricketbattingtracker.ui.theme.PavilionTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
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
                        navController.navigate("summary") {
                            popUpTo("start") { inclusive = true }
                        }
                    } else if (navController.currentDestination?.route == "summary") {
                        navController.navigate("start") {
                            popUpTo("summary") { inclusive = true }
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
                            onSyncClick = {
                                stopTrackerService()
                                SessionManager.resetSession()
                                navController.navigate("start") {
                                    popUpTo("start") { inclusive = true }
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
}
