package com.mrpeel.cricketbattingtracker.services

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
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
    
    private val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var timerJob: Job? = null
    private var amplitudeJob: Job? = null

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
                startRecordingFlow()
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

    private fun startRecordingFlow() {
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

            enableBluetoothRouting()
            setupMediaRecorder(file)
            mediaRecorder?.start()
            
            AudioRecordManager.updateRecordingState(true)
            AudioRecordManager.updateElapsedSeconds(0L)
            
            startForegroundNotification()
            startTimer()
            startAmplitudeListener()
            
            Log.d(TAG, "MediaRecorder started. Output file: ${file.absolutePath}")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start recording", e)
            Toast.makeText(this, "Failed to start audio recording: ${e.message}", Toast.LENGTH_SHORT).show()
            cleanup()
            stopSelf()
        }
    }

    private fun setupMediaRecorder(file: File) {
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
            prepare()
        }
        
        mediaRecorder = recorder
    }

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

    private fun startTimer() {
        timerJob?.cancel()
        val startTime = System.currentTimeMillis()
        timerJob = serviceScope.launch {
            while (isActive) {
                val elapsed = (System.currentTimeMillis() - startTime) / 1000
                AudioRecordManager.updateElapsedSeconds(elapsed)
                delay(1000)
            }
        }
    }

    private fun startAmplitudeListener() {
        amplitudeJob?.cancel()
        amplitudeJob = serviceScope.launch {
            while (isActive) {
                try {
                    val amp = mediaRecorder?.maxAmplitude ?: 0
                    // Scale 0-32767 range down to 0.0-1.0f with simple logarithmic smoothing or linear
                    val normalized = (amp.toFloat() / 32767f).coerceIn(0f, 1f)
                    AudioRecordManager.updateAmplitude(normalized)
                } catch (e: Exception) {
                    // Ignore transient exceptions if recorder is stopped/released
                }
                delay(100)
            }
        }
    }

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

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Cricket Session Active")
            .setContentText("Recording audio narration & tracking swings...")
            .setSmallIcon(android.R.drawable.presence_video_online) // standard green indicator icon
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun enableBluetoothRouting() {
        val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        try {
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val devices = audioManager.availableCommunicationDevices
                val bluetoothDevice = devices.firstOrNull {
                    it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO || it.type == AudioDeviceInfo.TYPE_BLE_HEADSET
                }
                if (bluetoothDevice != null) {
                    val result = audioManager.setCommunicationDevice(bluetoothDevice)
                    Log.d(TAG, "setCommunicationDevice Bluetooth Sco/Ble result: $result, device: ${bluetoothDevice.productName}")
                } else {
                    Log.d(TAG, "No Bluetooth communication device available; using default built-in mic")
                }
            } else {
                @Suppress("DEPRECATION")
                audioManager.startBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = true
                Log.d(TAG, "Legacy startBluetoothSco called")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to enable Bluetooth audio routing", e)
        }
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
        disableBluetoothRouting()
        AudioRecordManager.updateRecordingState(false)
        AudioRecordManager.activeRecordingFile = null
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "AudioRecordService Destroyed")
        cleanup()
    }

    override fun onBind(intent: Intent?): IBinder? {
        return null
    }

    companion object {
        const val TAG = "AudioRecordService"
        const val CHANNEL_ID = "AUDIO_RECORDING_CHANNEL"
        const val NOTIFICATION_ID = 101

        const val ACTION_START = "com.mrpeel.cricketbattingtracker.action.START_RECORDING"
        const val ACTION_STOP = "com.mrpeel.cricketbattingtracker.action.STOP_RECORDING"
        const val ACTION_DISCARD = "com.mrpeel.cricketbattingtracker.action.DISCARD_RECORDING"
    }
}
