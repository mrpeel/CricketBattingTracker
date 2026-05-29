package com.mrpeel.cricketbattingtracker.services

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.widget.Toast
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class AudioRecordService : Service() {

    private var mediaRecorder: MediaRecorder? = null
    private var recordingFile: File? = null

    // Scope backed by Main dispatcher so suspend funs can use withTimeout etc. on the main thread.
    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var timerJob: Job? = null
    private var amplitudeJob: Job? = null

    // Tracks whether we successfully routed to a Bluetooth device so we can pin the recorder.
    private var resolvedBluetoothDevice: AudioDeviceInfo? = null

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "AudioRecordService Created")
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        Log.d(TAG, "onStartCommand action: $action")

        when (action) {
            ACTION_START -> {
                // Launch on Main so coroutine suspension (BT wait) works cleanly.
                serviceScope.launch { startRecordingFlow() }
            }
            ACTION_STOP -> {
                stopRecordingFlow(isDiscard = false)
            }
            ACTION_DISCARD -> {
                stopRecordingFlow(isDiscard = true)
            }
        }

        return START_NOT_STICKY
    }

    // ─── Start flow ───────────────────────────────────────────────────────────

    private suspend fun startRecordingFlow() {
        if (AudioRecordManager.isRecording.value) return

        try {
            val ts = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val dir = getExternalFilesDir(null)
            if (dir != null && !dir.exists()) {
                dir.mkdirs()
            }

            val file = File(dir, "narration_$ts.m4a")
            recordingFile = file
            AudioRecordManager.activeRecordingFile = file

            // ── Step 1: Request Bluetooth routing and wait for the channel to open ──
            val btDevice = enableBluetoothRoutingAndWait()
            resolvedBluetoothDevice = btDevice

            // ── Step 2: Set up the recorder, pinning it to the resolved BT device if present ──
            setupMediaRecorder(file, btDevice)
            mediaRecorder?.start()

            AudioRecordManager.updateRecordingState(true)
            AudioRecordManager.updateElapsedSeconds(0L)

            startForegroundNotification()
            startTimer()
            startAmplitudeListener()

            val deviceDesc = btDevice?.productName ?: "built-in microphone"
            Log.d(TAG, "MediaRecorder started on [$deviceDesc]. Output: ${file.absolutePath}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start recording", e)
            withContext(Dispatchers.Main) {
                Toast.makeText(this@AudioRecordService, "Failed to start audio recording: ${e.message}", Toast.LENGTH_SHORT).show()
            }
            cleanup()
            stopSelf()
        }
    }

    // ─── Bluetooth routing ────────────────────────────────────────────────────

    /**
     * Requests Bluetooth SCO / BLE audio routing and waits (up to [BT_CONNECT_TIMEOUT_MS] ms)
     * for the route to become active.
     *
     * @return The [AudioDeviceInfo] of the connected Bluetooth input device, or `null` if no
     *         Bluetooth headset was found or the connection timed out (caller should fall back to
     *         the default built-in microphone).
     */
    private suspend fun enableBluetoothRoutingAndWait(): AudioDeviceInfo? {
        val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager

        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                // ── Modern path: setCommunicationDevice + OnCommunicationDeviceChangedListener ──
                enableBluetoothRoutingApi31(audioManager)
            } else {
                // ── Legacy path: startBluetoothSco + SCO_AUDIO_STATE_UPDATED broadcast ──
                enableBluetoothRoutingLegacy(audioManager)
                null  // Legacy path doesn't return a device handle we can pin.
            }
        } catch (e: SecurityException) {
            // BLUETOOTH_CONNECT permission denied on API 31+ — fall back gracefully.
            Log.w(TAG, "BLUETOOTH_CONNECT permission denied; using built-in mic. ${e.message}")
            null
        } catch (e: Exception) {
            Log.e(TAG, "Failed to enable Bluetooth audio routing; using built-in mic.", e)
            null
        }
    }

    /** Modern Bluetooth routing (API 31+). Returns the routed [AudioDeviceInfo] or null. */
    @androidx.annotation.RequiresApi(Build.VERSION_CODES.S)
    private suspend fun enableBluetoothRoutingApi31(audioManager: AudioManager): AudioDeviceInfo? {
        // Check BLUETOOTH_CONNECT runtime permission before touching the Bluetooth API.
        if (checkSelfPermission(android.Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            Log.w(TAG, "BLUETOOTH_CONNECT not granted; using built-in mic.")
            return null
        }

        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION

        val bluetoothDevice = audioManager.availableCommunicationDevices.firstOrNull {
            it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
            it.type == AudioDeviceInfo.TYPE_BLE_HEADSET ||
            it.type == AudioDeviceInfo.TYPE_BLE_SPEAKER
        }

        if (bluetoothDevice == null) {
            Log.d(TAG, "No Bluetooth communication device found; using built-in mic.")
            return null
        }

        Log.d(TAG, "Found BT device: ${bluetoothDevice.productName} (type=${bluetoothDevice.type}). Requesting route…")

        val requested = audioManager.setCommunicationDevice(bluetoothDevice)
        if (!requested) {
            Log.w(TAG, "setCommunicationDevice returned false for ${bluetoothDevice.productName}; using built-in mic.")
            return null
        }

        // Wait for the routing to be confirmed asynchronously.
        val confirmed = withTimeoutOrNull(BT_CONNECT_TIMEOUT_MS) {
            suspendCancellableCoroutine<Boolean> { cont ->
                val listener = AudioManager.OnCommunicationDeviceChangedListener { device ->
                    if (device?.id == bluetoothDevice.id) {
                        Log.d(TAG, "BT route confirmed: ${device.productName}")
                        if (cont.isActive) cont.resumeWith(Result.success(true))
                    }
                }
                audioManager.addOnCommunicationDeviceChangedListener(mainExecutor, listener)
                cont.invokeOnCancellation {
                    audioManager.removeOnCommunicationDeviceChangedListener(listener)
                }
            }
        } ?: false

        return if (confirmed) {
            Log.d(TAG, "Bluetooth routing active: ${bluetoothDevice.productName}")
            bluetoothDevice
        } else {
            Log.w(TAG, "BT route confirmation timed out after ${BT_CONNECT_TIMEOUT_MS}ms; using built-in mic.")
            // The route was requested but not confirmed — clear it so we don't record silence.
            audioManager.clearCommunicationDevice()
            null
        }
    }

    /**
     * Legacy Bluetooth routing (API < 31): starts the SCO channel and waits up to
     * [BT_CONNECT_TIMEOUT_MS] for `SCO_AUDIO_STATE_CONNECTED`.
     */
    @Suppress("DEPRECATION")
    private suspend fun enableBluetoothRoutingLegacy(audioManager: AudioManager) {
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        audioManager.startBluetoothSco()
        audioManager.isBluetoothScoOn = true
        Log.d(TAG, "Legacy startBluetoothSco called; waiting for SCO_AUDIO_STATE_CONNECTED…")

        withTimeoutOrNull(BT_CONNECT_TIMEOUT_MS) {
            suspendCancellableCoroutine<Unit> { cont ->
                val receiver = object : BroadcastReceiver() {
                    override fun onReceive(context: Context, intent: Intent) {
                        val state = intent.getIntExtra(
                            AudioManager.EXTRA_SCO_AUDIO_STATE,
                            AudioManager.SCO_AUDIO_STATE_ERROR
                        )
                        if (state == AudioManager.SCO_AUDIO_STATE_CONNECTED) {
                            Log.d(TAG, "Legacy SCO connected.")
                            if (cont.isActive) cont.resumeWith(Result.success(Unit))
                        } else if (state == AudioManager.SCO_AUDIO_STATE_DISCONNECTED) {
                            Log.w(TAG, "Legacy SCO disconnected unexpectedly.")
                            if (cont.isActive) cont.cancel()
                        }
                    }
                }
                registerReceiver(receiver, IntentFilter(AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED))
                cont.invokeOnCancellation { unregisterReceiver(receiver) }
            }
        } ?: Log.w(TAG, "Legacy SCO connection timed out after ${BT_CONNECT_TIMEOUT_MS}ms; proceeding anyway.")
    }

    // ─── MediaRecorder setup ──────────────────────────────────────────────────

    /**
     * Creates and prepares the [MediaRecorder]. If [preferredDevice] is non-null and the API
     * supports it, the recorder is pinned to that device via [MediaRecorder.setPreferredDevice].
     */
    private fun setupMediaRecorder(file: File, preferredDevice: AudioDeviceInfo? = null) {
        val recorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(applicationContext)
        } else {
            @Suppress("DEPRECATION")
            MediaRecorder()
        }

        recorder.apply {
            setAudioSource(MediaRecorder.AudioSource.VOICE_COMMUNICATION)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioSamplingRate(44100)
            setAudioEncodingBitRate(128000)
            setOutputFile(file.absolutePath)

            // Pin the recorder to the resolved Bluetooth device so the OS doesn't silently
            // fall back to the built-in mic after we've set a communication route.
            if (preferredDevice != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                @Suppress("DEPRECATION")
                setPreferredDevice(preferredDevice)
                Log.d(TAG, "MediaRecorder pinned to: ${preferredDevice.productName}")
            }

            prepare()
        }

        mediaRecorder = recorder
    }

    // ─── Stop / cleanup ───────────────────────────────────────────────────────

    private fun stopRecordingFlow(isDiscard: Boolean) {
        try {
            mediaRecorder?.stop()
            Log.d(TAG, "MediaRecorder stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping MediaRecorder", e)
        } finally {
            mediaRecorder?.release()
            mediaRecorder = null
        }

        if (isDiscard) {
            recordingFile?.let { file ->
                if (file.exists()) {
                    file.delete()
                    Log.d(TAG, "Recording file discarded/deleted: ${file.name}")
                }
            }
        } else {
            recordingFile?.let { file ->
                Log.d(TAG, "Recording saved successfully: ${file.name} (size: ${file.length()} bytes)")
            }
        }

        cleanup()
        AudioRecordManager.refreshRecordings(applicationContext)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    private fun disableBluetoothRouting() {
        val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                audioManager.clearCommunicationDevice()
            } else {
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = false
                @Suppress("DEPRECATION")
                audioManager.stopBluetoothSco()
            }
            audioManager.mode = AudioManager.MODE_NORMAL
            Log.d(TAG, "Bluetooth routing cleared, mode set back to NORMAL")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to disable Bluetooth audio routing", e)
        }
    }

    private fun cleanup() {
        timerJob?.cancel()
        amplitudeJob?.cancel()
        serviceScope.cancel()
        resolvedBluetoothDevice = null
        disableBluetoothRouting()
        AudioRecordManager.updateRecordingState(false)
        AudioRecordManager.activeRecordingFile = null
    }

    // ─── Timer & amplitude ────────────────────────────────────────────────────

    private fun startTimer() {
        timerJob?.cancel()
        val startTime = System.currentTimeMillis()
        timerJob = serviceScope.launch(Dispatchers.Default) {
            while (isActive) {
                val elapsed = (System.currentTimeMillis() - startTime) / 1000
                AudioRecordManager.updateElapsedSeconds(elapsed)
                delay(1000)
            }
        }
    }

    private fun startAmplitudeListener() {
        amplitudeJob?.cancel()
        amplitudeJob = serviceScope.launch(Dispatchers.Default) {
            while (isActive) {
                try {
                    val amp = mediaRecorder?.maxAmplitude ?: 0
                    // Scale 0-32767 range to 0.0-1.0f
                    val normalized = (amp.toFloat() / 32767f).coerceIn(0f, 1f)
                    AudioRecordManager.updateAmplitude(normalized)
                } catch (e: Exception) {
                    // Ignore transient exceptions if recorder is stopped/released
                }
                delay(100)
            }
        }
    }

    // ─── Notification ─────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Audio Narration Recording",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Active session audio narration notification"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun startForegroundNotification() {
        val notificationIntent = Intent(this, com.mrpeel.cricketbattingtracker.MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            notificationIntent,
            PendingIntent.FLAG_IMMUTABLE
        )

        val deviceLabel = resolvedBluetoothDevice?.productName?.let { " via $it" } ?: ""
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Cricket Session Active")
            .setContentText("Recording audio narration$deviceLabel & tracking swings…")
            .setSmallIcon(android.R.drawable.presence_video_online)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "AudioRecordService Destroyed")
        cleanup()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        const val TAG = "AudioRecordService"
        const val CHANNEL_ID = "AUDIO_RECORDING_CHANNEL"
        const val NOTIFICATION_ID = 101

        const val ACTION_START = "com.mrpeel.cricketbattingtracker.action.START_RECORDING"
        const val ACTION_STOP = "com.mrpeel.cricketbattingtracker.action.STOP_RECORDING"
        const val ACTION_DISCARD = "com.mrpeel.cricketbattingtracker.action.DISCARD_RECORDING"

        /** Maximum time (ms) to wait for a Bluetooth SCO/LE audio route to become active. */
        private const val BT_CONNECT_TIMEOUT_MS = 1500L
    }
}
