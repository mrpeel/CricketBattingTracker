package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import androidx.health.services.client.ExerciseUpdateCallback
import androidx.health.services.client.HealthServices
import androidx.health.services.client.data.ExerciseConfig
import androidx.health.services.client.data.ExerciseType
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.ExerciseUpdate
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.ExerciseLapSummary
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.concurrent.Executors

class HealthServicesManager(private val context: Context) {
    private val TAG = "HealthServicesManager"
    private val healthClient = HealthServices.getClient(context)
    private val exerciseClient = healthClient.exerciseClient
    private val executor = Executors.newSingleThreadExecutor()

    var onHeartRateUpdate: ((Int) -> Unit)? = null

    private val callback = object : ExerciseUpdateCallback {
        override fun onExerciseUpdateReceived(update: ExerciseUpdate) {
            val hrData = update.latestMetrics.getData(DataType.HEART_RATE_BPM)
            if (!hrData.isNullOrEmpty()) {
                val latestBpm = hrData.last().value.toInt()
                Log.d(TAG, "Real HR captured from PPG sensor: $latestBpm BPM")
                onHeartRateUpdate?.invoke(latestBpm)
            }
        }

        override fun onAvailabilityChanged(dataType: DataType<*, *>, availability: Availability) {
            Log.d(TAG, "Sensor availability changed: ${dataType.name} -> $availability")
        }

        override fun onLapSummaryReceived(lapSummary: ExerciseLapSummary) {}

        override fun onRegistered() {}

        override fun onRegistrationFailed(throwable: Throwable) {}
    }

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

                // Register listener before starting exercise to avoid missing initial frames
                // Signature is: setUpdateCallback(executor: Executor, callback: ExerciseUpdateCallback)
                exerciseClient.setUpdateCallback(executor, callback)

                val config = ExerciseConfig.builder(type)
                    .setDataTypes(setOf(DataType.HEART_RATE_BPM, DataType.CALORIES_TOTAL))
                    .build()
                
                exerciseClient.startExerciseAsync(config)
                Log.d(TAG, "Samsung Health Exercise tracking Started: $type")
            } catch (e: Exception) {
                Log.e(TAG, "Health tracking initialization failed: ${e.message}")
            }
        }
    }

    fun stopTracking() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                exerciseClient.endExerciseAsync()
                exerciseClient.clearUpdateCallbackAsync(callback)
                Log.d(TAG, "Samsung Health Exercise Tracking Ended & Synchronized.")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to end health session: ${e.message}")
            }
        }
    }
}
