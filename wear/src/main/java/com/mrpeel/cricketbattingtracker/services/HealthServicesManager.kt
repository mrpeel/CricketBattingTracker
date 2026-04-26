package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log

import androidx.health.services.client.HealthServices
import androidx.health.services.client.data.ExerciseConfig
import androidx.health.services.client.data.ExerciseType
import androidx.health.services.client.data.DataType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class HealthServicesManager(private val context: Context) {
    private val TAG = "HealthServicesManager"
    private val healthClient = HealthServices.getClient(context)
    private val exerciseClient = healthClient.exerciseClient

    fun startTracking() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Determine if Cricket is natively supported (fallback to Workout)
                val capabilities = exerciseClient.getCapabilitiesAsync().get()
                val type = if (capabilities.supportedExerciseTypes.contains(ExerciseType.CRICKET)) {
                    ExerciseType.CRICKET
                } else {
                    ExerciseType.WORKOUT
                }

                val config = ExerciseConfig.builder(type)
                    .setDataTypes(setOf(DataType.HEART_RATE_BPM, DataType.CALORIES_TOTAL))
                    .build()
                
                exerciseClient.startExerciseAsync(config)
                Log.d(TAG, "Samsung Health Exercise tracking Started: \$type")
            } catch (e: Exception) {
                Log.e(TAG, "Health tracking initialization failed: \${e.message}")
            }
        }
    }

    fun stopTracking() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                exerciseClient.endExerciseAsync()
                Log.d(TAG, "Samsung Health Exercise Tracking Ended & Synchronized.")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to end health session: \${e.message}")
            }
        }
    }
}
