package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.content.Intent
import android.util.Log
import com.google.android.gms.tasks.Tasks
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File
import android.widget.Toast

object AudioRecordManager {
    private const val TAG = "AudioRecordManager"

    private val _isRecording = MutableStateFlow(false)
    val isRecording: StateFlow<Boolean> = _isRecording.asStateFlow()

    private val _elapsedSeconds = MutableStateFlow(0L)
    val elapsedSeconds: StateFlow<Long> = _elapsedSeconds.asStateFlow()

    private val _maxAmplitude = MutableStateFlow(0f)
    val maxAmplitude: StateFlow<Float> = _maxAmplitude.asStateFlow()

    private val _recordingsList = MutableStateFlow<List<File>>(emptyList())
    val recordingsList: StateFlow<List<File>> = _recordingsList.asStateFlow()

    var activeRecordingFile: File? = null

    fun updateRecordingState(recording: Boolean) {
        _isRecording.value = recording
        if (!recording) {
            _maxAmplitude.value = 0f
        }
    }

    fun updateElapsedSeconds(seconds: Long) {
        _elapsedSeconds.value = seconds
    }

    fun updateAmplitude(amplitude: Float) {
        _maxAmplitude.value = amplitude
    }

    fun startRecording(context: Context, recordAudio: Boolean) {
        if (_isRecording.value) return

        if (recordAudio) {
            val intent = Intent(context, AudioRecordService::class.java).apply {
                action = AudioRecordService.ACTION_START
            }
            try {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start recording service: ${e.message}", e)
            }
        } else {
            // No audio recording, just mark active tracking session
            updateRecordingState(true)
        }
        sendMessageToWatch(context, "/start_tracking")
    }

    fun stopRecording(context: Context) {
        val intent = Intent(context, AudioRecordService::class.java).apply {
            action = AudioRecordService.ACTION_STOP
        }
        context.startService(intent)
        updateRecordingState(false) // Safe fallback if service wasn't running
        sendMessageToWatch(context, "/stop_tracking")
    }

    fun discardRecording(context: Context) {
        val intent = Intent(context, AudioRecordService::class.java).apply {
            action = AudioRecordService.ACTION_DISCARD
        }
        context.startService(intent)
        updateRecordingState(false) // Safe fallback if service wasn't running
        sendMessageToWatch(context, "/stop_tracking")
    }

    fun refreshRecordings(context: Context) {
        try {
            val dir = context.getExternalFilesDir(null)
            if (dir != null && dir.exists()) {
                val files = dir.listFiles { file ->
                    file.isFile && file.name.startsWith("narration_") && file.name.endsWith(".m4a")
                }
                _recordingsList.value = files?.sortedByDescending { it.lastModified() } ?: emptyList()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to refresh recordings list: ${e.message}", e)
        }
    }

    fun deleteRecording(file: File, context: Context) {
        try {
            if (file.exists()) {
                file.delete()
                Log.d(TAG, "Deleted recording: ${file.name}")
            }
            refreshRecordings(context)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to delete recording: ${e.message}", e)
        }
    }

    private fun sendMessageToWatch(context: Context, path: String) {
        Thread {
            try {
                val nodeClient = Wearable.getNodeClient(context)
                val nodes = Tasks.await(nodeClient.connectedNodes)
                val messageClient = Wearable.getMessageClient(context)
                
                if (nodes.isEmpty()) {
                    Log.w(TAG, "No connected watch nodes found to send $path")
                }

                for (node in nodes) {
                    Tasks.await(messageClient.sendMessage(node.id, path, null))
                    Log.d(TAG, "Sent message to watch node ${node.displayName} ($path)")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to send message to watch: ${e.message}", e)
            }
        }.start()
    }
}

object AudioPlayManager {
    private var mediaPlayer: android.media.MediaPlayer? = null
    private val _playingFile = MutableStateFlow<File?>(null)
    val playingFile: StateFlow<File?> = _playingFile.asStateFlow()

    fun playFile(context: Context, file: File) {
        stopPlaying()
        try {
            val mp = android.media.MediaPlayer().apply {
                setDataSource(file.absolutePath)
                prepare()
                start()
                setOnCompletionListener {
                    stopPlaying()
                }
            }
            mediaPlayer = mp
            _playingFile.value = file
            Log.d("AudioPlayManager", "Started playback: ${file.name}")
        } catch (e: Exception) {
            Log.e("AudioPlayManager", "Failed to play audio: ${e.message}", e)
            Toast.makeText(context, "Playback failed: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    fun stopPlaying() {
        try {
            mediaPlayer?.stop()
            mediaPlayer?.release()
            Log.d("AudioPlayManager", "Stopped playback")
        } catch (e: Exception) {
            // ignore
        } finally {
            mediaPlayer = null
            _playingFile.value = null
        }
    }
}
