package com.mrpeel.cricketbattingtracker

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.MaterialTheme
import com.mrpeel.cricketbattingtracker.services.TrackerService

class MainActivity : ComponentActivity() {

    private var isTracking by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        setContent {
            MaterialTheme {
                Column(
                    modifier = Modifier.fillMaxSize(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(text = "Cricket Tracker")
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    Button(onClick = { toggleTracking() }) {
                        Text(text = if (isTracking) "Stop Innings" else "Start Innings")
                    }
                }
            }
        }
    }

    private fun toggleTracking() {
        isTracking = !isTracking
        if (isTracking) {
            val intent = Intent(this, TrackerService::class.java)
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
        } else {
            val intent = Intent(this, TrackerService::class.java)
            intent.action = "STOP_TRACKING"
            startService(intent)
        }
    }
}
