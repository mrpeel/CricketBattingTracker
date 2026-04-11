package com.mrpeel.cricketbattingtracker

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
        
        setContent {
            PavilionTheme {
                val navController = rememberSwipeDismissableNavController()
                
                // Collect states from SessionManager securely
                val isTracking = SessionManager.isTracking.collectAsState()
                val shotCount = SessionManager.shotCount.collectAsState()
                val avgSpeed = SessionManager.avgSpeed.collectAsState()
                val maxSpeed = SessionManager.maxSpeed.collectAsState()

                SwipeDismissableNavHost(
                    navController = navController,
                    startDestination = if (isTracking.value) "summary" else "start"
                ) {
                    composable("start") {
                        StartSessionScreen(
                            onStartClick = {
                                startTrackerService()
                                navController.navigate("summary")
                            }
                        )
                    }
                    
                    composable("summary") {
                        SessionSummaryScreen(
                            avgSpeed = avgSpeed.value,
                            maxSpeed = maxSpeed.value,
                            shotCount = shotCount.value,
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

    private fun startTrackerService() {
        val intent = Intent(this, TrackerService::class.java)
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
