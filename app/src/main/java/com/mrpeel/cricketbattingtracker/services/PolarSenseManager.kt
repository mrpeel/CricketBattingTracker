package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.polar.sdk.api.PolarBleApi
import com.polar.sdk.api.PolarBleApiCallback
import com.polar.sdk.api.PolarBleApiDefaultImpl
import com.polar.sdk.api.model.PolarDeviceInfo
import com.polar.sdk.api.model.PolarAccelerometerData
import com.polar.sdk.api.model.PolarGyroData
import com.polar.sdk.api.model.PolarSensorSetting
import io.reactivex.rxjava3.disposables.Disposable
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import java.util.UUID
import kotlin.math.sqrt

/** DataStore for persisting paired Polar device ID. */
private val Context.polarDataStore: DataStore<Preferences> by preferencesDataStore(name = "polar_prefs")
private val POLAR_DEVICE_ID_KEY = stringPreferencesKey("polar_device_id")

/** Connection state of the Polar Sense. */
enum class PolarConnectionState {
    DISCONNECTED,
    SCANNING,
    CONNECTING,
    CONNECTED,
    STREAMING
}

/** Info about a discovered Polar device during scanning. */
data class DiscoveredPolarDevice(
    val deviceId: String,
    val name: String,
    val rssi: Int
)

/**
 * Singleton manager for the Polar Verity Sense (bottom hand sensor).
 * Handles scanning, pairing, connection, SDK Mode, ACC/GYRO streaming,
 * and continuous tap sequence detection for watch alignment.
 */
object PolarSenseManager {
    private const val TAG = "PolarSenseManager"

    private var api: PolarBleApi? = null
    private var accDisposable: Disposable? = null
    private var gyroDisposable: Disposable? = null
    private var scanDisposable: Disposable? = null
    private var sdkModeEnabled = false

    // --- State flows ---
    private val _connectionState = MutableStateFlow(PolarConnectionState.DISCONNECTED)
    val connectionState: StateFlow<PolarConnectionState> = _connectionState.asStateFlow()

    private val _discoveredDevices = MutableStateFlow<List<DiscoveredPolarDevice>>(emptyList())
    val discoveredDevices: StateFlow<List<DiscoveredPolarDevice>> = _discoveredDevices.asStateFlow()

    private val _pairedDeviceId = MutableStateFlow<String?>(null)
    val pairedDeviceId: StateFlow<String?> = _pairedDeviceId.asStateFlow()

    private val _sampleCount = MutableStateFlow(0L)
    val sampleCount: StateFlow<Long> = _sampleCount.asStateFlow()

    // --- Tap sequence detection ---
    private data class TapEvent(val phoneTimestampMs: Long, val magnitude: Float)
    private val tapBuffer = mutableListOf<TapEvent>()
    private val _detectedTapSequences = MutableStateFlow<List<List<Long>>>(emptyList()) // each: list of 5 phone-clock timestamps
    val detectedTapSequences: StateFlow<List<List<Long>>> = _detectedTapSequences.asStateFlow()
    private var lastTapDetectionMs = 0L

    private const val TAP_THRESHOLD_MG = 2500f  // milliG threshold for peaks
    private const val TAP_BUFFER_THRESHOLD_MG = 1750f  // lower threshold for buffer context
    private const val TAP_MIN_GAP_MS = 200L
    private const val TAP_MAX_GAP_MS = 1500L
    private const val TAP_SEQUENCE_MAX_DURATION_MS = 5000L
    private const val TAP_SEQUENCE_COOLDOWN_MS = 10000L

    // Callback for CSV writing — set by PolarSenseService
    var onAccSample: ((phoneMs: Long, sensorNs: Long, xMg: Int, yMg: Int, zMg: Int) -> Unit)? = null
    var onGyroSample: ((phoneMs: Long, sensorNs: Long, xDps: Float, yDps: Float, zDps: Float) -> Unit)? = null

    /** Initialize the Polar BLE API. Call once from Application or Service context. */
    fun initialize(context: Context) {
        if (api != null) return

        api = PolarBleApiDefaultImpl.defaultImplementation(
            context.applicationContext,
            setOf(
                PolarBleApi.PolarBleSdkFeature.FEATURE_POLAR_ONLINE_STREAMING,
                PolarBleApi.PolarBleSdkFeature.FEATURE_POLAR_SDK_MODE,
                PolarBleApi.PolarBleSdkFeature.FEATURE_DEVICE_INFO
            )
        )

        api?.setApiCallback(object : PolarBleApiCallback() {
            override fun deviceConnecting(polarDeviceInfo: PolarDeviceInfo) {
                Log.d(TAG, "Connecting to ${polarDeviceInfo.deviceId}")
                _connectionState.value = PolarConnectionState.CONNECTING
            }

            override fun deviceConnected(polarDeviceInfo: PolarDeviceInfo) {
                Log.d(TAG, "Connected to ${polarDeviceInfo.deviceId}")
                _connectionState.value = PolarConnectionState.CONNECTED
            }

            override fun deviceDisconnected(polarDeviceInfo: PolarDeviceInfo) {
                Log.d(TAG, "Disconnected from ${polarDeviceInfo.deviceId}")
                sdkModeEnabled = false
                _connectionState.value = PolarConnectionState.DISCONNECTED
            }

            override fun bleSdkFeatureReady(identifier: String, feature: PolarBleApi.PolarBleSdkFeature) {
                Log.d(TAG, "Feature ready: $feature for $identifier")
            }

            override fun disInformationReceived(identifier: String, uuid: UUID, value: String) {
                Log.d(TAG, "DIS info: $uuid = $value")
            }

            override fun batteryLevelReceived(identifier: String, level: Int) {
                Log.d(TAG, "Battery: $level%")
            }
        })

        // Load persisted device ID
        CoroutineScope(Dispatchers.IO).launch {
            val savedId = context.polarDataStore.data
                .map { it[POLAR_DEVICE_ID_KEY] }
                .first()
            _pairedDeviceId.value = savedId
            Log.d(TAG, "Loaded paired device ID: $savedId")
        }
    }

    /** Save a device ID as the paired Polar Sense. */
    fun pairDevice(context: Context, deviceId: String) {
        _pairedDeviceId.value = deviceId
        CoroutineScope(Dispatchers.IO).launch {
            context.polarDataStore.edit { prefs ->
                prefs[POLAR_DEVICE_ID_KEY] = deviceId
            }
        }
        Log.d(TAG, "Paired device: $deviceId")
    }

    /** Forget the currently paired device. */
    fun forgetDevice(context: Context) {
        disconnect()
        _pairedDeviceId.value = null
        CoroutineScope(Dispatchers.IO).launch {
            context.polarDataStore.edit { prefs ->
                prefs.remove(POLAR_DEVICE_ID_KEY)
            }
        }
        Log.d(TAG, "Forgot paired device")
    }

    /** Start scanning for nearby Polar Sense devices. */
    fun startScan() {
        val polarApi = api ?: return
        stopScan()
        _discoveredDevices.value = emptyList()
        _connectionState.value = PolarConnectionState.SCANNING

        scanDisposable = polarApi.searchForDevice()
            .subscribe(
                { deviceInfo ->
                    val device = DiscoveredPolarDevice(
                        deviceId = deviceInfo.deviceId,
                        name = deviceInfo.name,
                        rssi = deviceInfo.rssi
                    )
                    val current = _discoveredDevices.value.toMutableList()
                    // Update existing or add new
                    val existingIndex = current.indexOfFirst { it.deviceId == device.deviceId }
                    if (existingIndex >= 0) {
                        current[existingIndex] = device
                    } else {
                        current.add(device)
                    }
                    _discoveredDevices.value = current
                    Log.d(TAG, "Found device: ${device.name} (${device.deviceId}), RSSI: ${device.rssi}")
                },
                { error ->
                    Log.e(TAG, "Scan error: ${error.message}", error)
                    _connectionState.value = PolarConnectionState.DISCONNECTED
                },
                {
                    Log.d(TAG, "Scan complete")
                    if (_connectionState.value == PolarConnectionState.SCANNING) {
                        _connectionState.value = PolarConnectionState.DISCONNECTED
                    }
                }
            )
    }

    /** Stop scanning. */
    fun stopScan() {
        scanDisposable?.dispose()
        scanDisposable = null
        if (_connectionState.value == PolarConnectionState.SCANNING) {
            _connectionState.value = PolarConnectionState.DISCONNECTED
        }
    }

    /** Connect to the paired device. */
    fun connect() {
        val deviceId = _pairedDeviceId.value ?: run {
            Log.w(TAG, "No paired device ID")
            return
        }
        val polarApi = api ?: return

        try {
            polarApi.connectToDevice(deviceId)
            _connectionState.value = PolarConnectionState.CONNECTING
        } catch (e: Exception) {
            Log.e(TAG, "Connect failed: ${e.message}", e)
        }
    }

    /** Disconnect from the paired device. */
    fun disconnect() {
        stopStreaming()
        val deviceId = _pairedDeviceId.value ?: return
        try {
            api?.disconnectFromDevice(deviceId)
        } catch (e: Exception) {
            Log.e(TAG, "Disconnect error: ${e.message}", e)
        }
        _connectionState.value = PolarConnectionState.DISCONNECTED
    }

    /** Enable SDK Mode, then start ACC + GYRO streaming at 52Hz. */
    fun startStreaming() {
        val deviceId = _pairedDeviceId.value ?: return
        val polarApi = api ?: return

        // Reset state
        _sampleCount.value = 0
        tapBuffer.clear()
        _detectedTapSequences.value = emptyList()
        lastTapDetectionMs = 0L

        // Enable SDK Mode first (gives us exclusive sensor control)
        polarApi.enableSDKMode(deviceId)
            .subscribe(
                {
                    sdkModeEnabled = true
                    Log.d(TAG, "SDK Mode enabled — starting streams")
                    startAccStream(deviceId, polarApi)
                    startGyroStream(deviceId, polarApi)
                    _connectionState.value = PolarConnectionState.STREAMING
                },
                { error ->
                    Log.e(TAG, "Failed to enable SDK Mode: ${error.message}", error)
                    // Fall back to default streaming without SDK Mode
                    startAccStream(deviceId, polarApi)
                    startGyroStream(deviceId, polarApi)
                    _connectionState.value = PolarConnectionState.STREAMING
                }
            )
    }

    private fun startAccStream(deviceId: String, polarApi: PolarBleApi) {
        val settings = PolarSensorSetting(
            mapOf(
                PolarSensorSetting.SettingType.SAMPLE_RATE to 52,
                PolarSensorSetting.SettingType.RANGE to 8,
                PolarSensorSetting.SettingType.RESOLUTION to 16
            )
        )

        accDisposable = polarApi.startAccStreaming(deviceId, settings)
            .subscribe(
                { data: PolarAccelerometerData ->
                    val phoneMs = System.currentTimeMillis()
                    for (sample in data.samples) {
                        _sampleCount.value++
                        onAccSample?.invoke(phoneMs, sample.timeStamp, sample.x, sample.y, sample.z)
                        processTapCandidate(phoneMs, sample.x, sample.y, sample.z)
                    }
                },
                { error ->
                    Log.e(TAG, "ACC stream error: ${error.message}", error)
                }
            )
        Log.d(TAG, "ACC stream started at 52Hz")
    }

    private fun startGyroStream(deviceId: String, polarApi: PolarBleApi) {
        val settings = PolarSensorSetting(
            mapOf(
                PolarSensorSetting.SettingType.SAMPLE_RATE to 52,
                PolarSensorSetting.SettingType.RANGE to 2000,
                PolarSensorSetting.SettingType.RESOLUTION to 16
            )
        )

        gyroDisposable = polarApi.startGyroStreaming(deviceId, settings)
            .subscribe(
                { data: PolarGyroData ->
                    val phoneMs = System.currentTimeMillis()
                    for (sample in data.samples) {
                        onGyroSample?.invoke(phoneMs, sample.timeStamp, sample.x, sample.y, sample.z)
                    }
                },
                { error ->
                    Log.e(TAG, "GYRO stream error: ${error.message}", error)
                }
            )
        Log.d(TAG, "GYRO stream started at 52Hz")
    }

    /** Stop all streams and exit SDK Mode. */
    fun stopStreaming() {
        accDisposable?.dispose()
        accDisposable = null
        gyroDisposable?.dispose()
        gyroDisposable = null

        if (sdkModeEnabled) {
            val deviceId = _pairedDeviceId.value
            if (deviceId != null) {
                api?.disableSDKMode(deviceId)?.subscribe(
                    { Log.d(TAG, "SDK Mode disabled") },
                    { Log.e(TAG, "Failed to disable SDK Mode: ${it.message}") }
                )
            }
            sdkModeEnabled = false
        }

        if (_connectionState.value == PolarConnectionState.STREAMING) {
            _connectionState.value = PolarConnectionState.CONNECTED
        }
    }

    /** Shut down the Polar API entirely. */
    fun shutdown() {
        disconnect()
        api?.shutDown()
        api = null
    }

    // --- Tap sequence detection ---

    private fun processTapCandidate(phoneMs: Long, xMg: Int, yMg: Int, zMg: Int) {
        val magnitude = sqrt((xMg.toLong() * xMg + yMg.toLong() * yMg + zMg.toLong() * zMg).toFloat())

        // Buffer events above a lower threshold for context
        if (magnitude >= TAP_BUFFER_THRESHOLD_MG) {
            tapBuffer.add(TapEvent(phoneMs, magnitude))
        }

        // Prune old entries (>10 seconds)
        val cutoff = phoneMs - 10_000L
        tapBuffer.removeAll { it.phoneTimestampMs < cutoff }

        // Only check for sequences if this sample is a strong tap candidate
        if (magnitude >= TAP_THRESHOLD_MG) {
            checkForTapSequence(phoneMs)
        }
    }

    private fun checkForTapSequence(nowMs: Long) {
        // Cooldown check
        if (nowMs - lastTapDetectionMs < TAP_SEQUENCE_COOLDOWN_MS) return

        // Find peaks in the tap buffer (local maxima within ±150ms, above threshold)
        val peaks = mutableListOf<TapEvent>()
        for (i in tapBuffer.indices) {
            val event = tapBuffer[i]
            if (event.magnitude < TAP_THRESHOLD_MG) continue

            // Check if local maximum within ±150ms window
            var isLocalMax = true
            for (j in tapBuffer.indices) {
                if (i == j) continue
                val other = tapBuffer[j]
                if (kotlin.math.abs(event.phoneTimestampMs - other.phoneTimestampMs) <= 150L &&
                    other.magnitude > event.magnitude) {
                    isLocalMax = false
                    break
                }
            }
            if (isLocalMax) peaks.add(event)
        }

        // Deduplicate peaks within TAP_MIN_GAP_MS
        val dedupedPeaks = mutableListOf<TapEvent>()
        for (peak in peaks.sortedBy { it.phoneTimestampMs }) {
            if (dedupedPeaks.isEmpty() ||
                peak.phoneTimestampMs - dedupedPeaks.last().phoneTimestampMs >= TAP_MIN_GAP_MS) {
                dedupedPeaks.add(peak)
            }
        }

        // Check for 5 consecutive peaks forming a valid sequence
        if (dedupedPeaks.size < 5) return

        for (startIdx in 0..(dedupedPeaks.size - 5)) {
            val sequence = dedupedPeaks.subList(startIdx, startIdx + 5)
            val totalDuration = sequence.last().phoneTimestampMs - sequence.first().phoneTimestampMs

            if (totalDuration > TAP_SEQUENCE_MAX_DURATION_MS) continue

            // Validate inter-tap gaps
            var validGaps = true
            for (k in 0 until 4) {
                val gap = sequence[k + 1].phoneTimestampMs - sequence[k].phoneTimestampMs
                if (gap < TAP_MIN_GAP_MS || gap > TAP_MAX_GAP_MS) {
                    validGaps = false
                    break
                }
            }

            if (validGaps) {
                val timestamps = sequence.map { it.phoneTimestampMs }
                val currentList = _detectedTapSequences.value.toMutableList()
                currentList.add(timestamps)
                _detectedTapSequences.value = currentList
                lastTapDetectionMs = nowMs
                Log.d(TAG, "🔔 Tap sequence #${currentList.size} detected at ${timestamps.first()}")
                return
            }
        }
    }
}
