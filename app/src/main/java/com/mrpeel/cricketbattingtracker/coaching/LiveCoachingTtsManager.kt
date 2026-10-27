package com.mrpeel.cricketbattingtracker.coaching

import android.content.Context
import android.media.AudioAttributes
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.util.Log
import java.util.Locale

/**
 * Three-Stage In-Ear Coaching Modes.
 */
enum class CoachingMode(val displayName: String, val shortDescription: String) {
    STAGE_1_CALIBRATION(
        "Stage 1: Calibration",
        "Earcon + 2-syllable voice cue (builds Pavlovian link)"
    ),
    STAGE_2_FLOW_STATE(
        "Stage 2: Flow State",
        "Earcon only on faults (0.2s); Chime + Speed on good shots"
    ),
    STAGE_3_SILENT_DIAGNOSTIC(
        "Stage 3: Silent Diagnostic",
        "Silent unless you repeat the same fault twice in a row"
    );

    companion object {
        fun fromPreference(value: String?): CoachingMode {
            return when (value) {
                STAGE_1_CALIBRATION.name -> STAGE_1_CALIBRATION
                STAGE_2_FLOW_STATE.name -> STAGE_2_FLOW_STATE
                STAGE_3_SILENT_DIAGNOSTIC.name -> STAGE_3_SILENT_DIAGNOSTIC
                "FAULTS_ONLY" -> STAGE_2_FLOW_STATE
                "ALL_DELIVERIES" -> STAGE_1_CALIBRATION
                "SPEED_CALLOUT" -> STAGE_1_CALIBRATION
                else -> STAGE_1_CALIBRATION
            }
        }
    }
}

/**
 * Interface defining audio feedback delivery, allowing headless unit testing without Android TTS engine.
 */
interface LiveCoachingAudioFeedback {
    var coachingMode: CoachingMode
    var isEnabled: Boolean
    fun speak(cue: String)
    fun playEarcon(fault: LiveShotFault)
}

/**
 * Manages on-device low-latency Text-to-Speech coaching cues through Bluetooth earphones.
 */
class LiveCoachingTtsManager(
    private val context: Context,
    private val earconPlayer: EarconAudioPlayer? = null
) : LiveCoachingAudioFeedback, TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "LiveCoachingTtsManager"
        private const val UTTERANCE_ID = "live_batting_cue"
    }

    private var tts: TextToSpeech? = null
    private var isInitialized = false
    private var pendingCue: String? = null

    override var coachingMode: CoachingMode = CoachingMode.STAGE_1_CALIBRATION
    override var isEnabled: Boolean = true

    init {
        try {
            tts = TextToSpeech(context.applicationContext, this)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to instantiate TextToSpeech: ${e.message}")
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.let { engine ->
                val result = engine.setLanguage(Locale.US)
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    engine.language = Locale.getDefault()
                }
                // Crisp 1.25x tempo so 2-syllable cues finish in < 500ms
                engine.setSpeechRate(1.25f)
                engine.setPitch(1.0f)

                val audioAttributes = AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
                engine.setAudioAttributes(audioAttributes)

                isInitialized = true
                Log.i(TAG, "Live coaching TTS initialized successfully at 1.25x speed.")

                pendingCue?.let { cue ->
                    speak(cue)
                    pendingCue = null
                }
            }
        } else {
            Log.e(TAG, "TextToSpeech init failed with status: $status")
        }
    }

    /**
     * Plays the procedural acoustic earcon for the fault.
     */
    override fun playEarcon(fault: LiveShotFault) {
        if (!isEnabled) return
        earconPlayer?.play(fault)
    }

    /**
     * Speaks a concise coaching cue. Uses QUEUE_FLUSH to guarantee zero audio lag.
     */
    override fun speak(cue: String) {
        if (!isEnabled || cue.isBlank()) return

        if (!isInitialized) {
            pendingCue = cue
            return
        }

        try {
            val params = Bundle().apply {
                putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f)
            }
            tts?.speak(cue, TextToSpeech.QUEUE_FLUSH, params, UTTERANCE_ID)
            Log.d(TAG, "Voiced live coaching cue: \"$cue\"")
        } catch (e: Exception) {
            Log.e(TAG, "Error voicing coaching cue: ${e.message}")
        }
    }

    /**
     * Shuts down the TTS engine and procedural earcon player.
     */
    fun shutdown() {
        try {
            tts?.stop()
            tts?.shutdown()
            tts = null
            isInitialized = false
            earconPlayer?.release()
            Log.i(TAG, "Live coaching TTS and earcon player shut down.")
        } catch (e: Exception) {
            Log.e(TAG, "Error shutting down TTS: ${e.message}")
        }
    }
}
