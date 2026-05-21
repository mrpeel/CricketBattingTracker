package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.util.concurrent.Executors

/**
 * Reads heart rate from the watch PPG sensor using MeasureClient.
 *
 * WHY MeasureClient, not ExerciseClient:
 *   ExerciseClient.startExerciseAsync() requires *exclusive* ownership of the exercise session.
 *   Samsung Health on the watch often owns its own background exercise session at all times.
 *   When that happens, our startExerciseAsync() fails silently — onExerciseUpdateReceived()
 *   never fires, and we collect zero HR samples.
 *
 *   MeasureClient is non-exclusive: it subscribes to the PPG sensor as a passive listener
 *   and delivers samples regardless of who owns the current exercise session. This means
 *   our app co-exists with Samsung Health instead of fighting it for sensor ownership.
 */
class HealthServicesManager(private val context: Context) {
    private val TAG = "HealthServicesManager"
    private val measureClient = HealthServices.getClient(context).measureClient
    private val executor = Executors.newSingleThreadExecutor()

    var onHeartRateUpdate: ((Int) -> Unit)? = null

    private val hrCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
            Log.d(TAG, "HR sensor availability: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            val hrSamples = data.getData(DataType.HEART_RATE_BPM)
            if (hrSamples.isNotEmpty()) {
                val bpm = hrSamples.last().value.toInt()
                Log.d(TAG, "Real HR captured from PPG sensor (MeasureClient): $bpm BPM")
                onHeartRateUpdate?.invoke(bpm)
            }
        }
    }

    fun startTracking() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Check device supports heart rate before registering
                val capabilities = measureClient.getCapabilitiesAsync().get()
                if (DataType.HEART_RATE_BPM !in capabilities.supportedDataTypesMeasure) {
                    Log.w(TAG, "Device does not support HEART_RATE_BPM via MeasureClient")
                    return@launch
                }

                measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, executor, hrCallback)
                Log.d(TAG, "MeasureClient HR callback registered — non-exclusive PPG sampling active")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to register MeasureClient HR callback: ${e.message}", e)
            }
        }
    }

    fun stopTracking() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                measureClient.unregisterMeasureCallbackAsync(DataType.HEART_RATE_BPM, hrCallback).get()
                Log.d(TAG, "MeasureClient HR callback unregistered")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to unregister MeasureClient HR callback: ${e.message}", e)
            }
        }
    }
}
