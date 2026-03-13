package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import androidx.health.services.client.HealthServices
import androidx.health.services.client.ExerciseClient
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.ExerciseConfig
import androidx.health.services.client.data.ExerciseType
import androidx.health.services.client.data.ExerciseUpdateCallback
import androidx.health.services.client.data.ExerciseUpdate
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.ExerciseLapSummary
import com.google.common.util.concurrent.FutureCallback
import com.google.common.util.concurrent.Futures
import java.util.concurrent.Executors

class HealthServicesManager(private val context: Context) {
    private val TAG = "HealthServicesManager"
    private val healthClient = HealthServices.getClient(context)
    private val exerciseClient: ExerciseClient = healthClient.exerciseClient

    private val executor = Executors.newSingleThreadExecutor()

    private val dataTypes = setOf(
        DataType.HEART_RATE_BPM,
        DataType.DISTANCE_TOTAL,
        DataType.CALORIES_TOTAL
    )

    private val exerciseUpdateCallback = object : ExerciseUpdateCallback {
        override fun onExerciseUpdateReceived(update: ExerciseUpdate) {
            val metrics = update.latestMetrics
            val distance = metrics.getData(DataType.DISTANCE_TOTAL)?.lastOrNull()?.value
            val calories = metrics.getData(DataType.CALORIES_TOTAL)?.lastOrNull()?.value
            
            Log.d(TAG, "Health Update: Dist=\$distance, Cal=\$calories")
            // Here we can cache this value and push it to timeline
        }

        override fun onLapSummaryReceived(lapSummary: ExerciseLapSummary) {}
        override fun onRegistered() {
            Log.d(TAG, "ExerciseClient Registered")
        }
        override fun onRegistrationFailed(throwable: Throwable) {
            Log.e(TAG, "ExerciseClient Registration Failed", throwable)
        }
        override fun onAvailabilityChanged(dataType: DataType, availability: Availability) {}
    }

    fun startTracking() {
        val config = ExerciseConfig(
            exerciseType = ExerciseType.CRICKET, // The closest standard identifier for Samsung Health integration
            dataTypes = dataTypes,
            isAutoPauseAndResumeEnabled = false,
            isGpsEnabled = true
        )

        exerciseClient.setUpdateCallback(exerciseUpdateCallback)
        
        Futures.addCallback(
            exerciseClient.startExerciseAsync(config),
            object : FutureCallback<Void?> {
                override fun onSuccess(result: Void?) {
                    Log.d(TAG, "Exercise started successfully")
                }
                override fun onFailure(t: Throwable) {
                    Log.e(TAG, "Failed to start exercise", t)
                }
            },
            executor
        )
    }

    fun stopTracking() {
        Futures.addCallback(
            exerciseClient.endExerciseAsync(),
            object : FutureCallback<Void?> {
                override fun onSuccess(result: Void?) {
                    Log.d(TAG, "Exercise ended successfully")
                }
                override fun onFailure(t: Throwable) {
                    Log.e(TAG, "Failed to end exercise", t)
                }
            },
            executor
        )
    }
}
