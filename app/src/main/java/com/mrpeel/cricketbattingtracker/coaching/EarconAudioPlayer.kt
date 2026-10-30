package com.mrpeel.cricketbattingtracker.coaching

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import android.util.Log
import kotlin.math.*

/**
 * Procedural low-latency synthesizer for cricket batting diagnostic earcons.
 * Precomputes 16-bit 22.05 kHz PCM buffers in memory at initialization for sub-5ms latency.
 */
class EarconAudioPlayer(private val isEnabled: Boolean = true) {

    companion object {
        private const val TAG = "EarconAudioPlayer"
        private const val SAMPLE_RATE = 22050
        private const val TWO_PI = 2.0 * PI
    }

    private val audioTracks = mutableMapOf<LiveShotFault, AudioTrack>()

    init {
        if (isEnabled) {
            try {
                precomputeAllEarcons()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to initialize procedural earcons: ${e.message}")
            }
        }
    }

    /**
     * Plays the distinct acoustic earcon associated with the diagnosed failure mode or clean hit.
     */
    fun play(fault: LiveShotFault) {
        if (!isEnabled) return
        try {
            audioTracks[fault]?.let { track ->
                track.stop()
                track.reloadStaticData()
                track.play()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error playing earcon for $fault: ${e.message}")
        }
    }

    /**
     * Releases all AudioTrack native instances.
     */
    fun release() {
        audioTracks.values.forEach {
            try {
                it.stop()
                it.release()
            } catch (_: Exception) {}
        }
        audioTracks.clear()
    }

    private fun precomputeAllEarcons() {
        LiveShotFault.values().forEach { fault ->
            val pcmData = generatePcmForFault(fault)
            val track = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(SAMPLE_RATE)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setBufferSizeInBytes(pcmData.size)
                .setTransferMode(AudioTrack.MODE_STATIC)
                .build()

            track.write(pcmData, 0, pcmData.size)
            audioTracks[fault] = track
        }
        Log.i(TAG, "Procedural earcons initialized for ${audioTracks.size} shot classes.")
    }

    /**
     * Synthesizes 16-bit PCM mono data according to the acoustic design specifications.
     */
    private fun generatePcmForFault(fault: LiveShotFault): ByteArray {
        return when (fault) {
            // ── Family A: Downswing Timing & Continuity ──
            LiveShotFault.EARLY_PEAK_DECELERATION -> {
                // Tape-Stop / Power-Down Drop (600 Hz -> 150 Hz rapid pitch & volume drop, 200 ms)
                generateTapeStopDrop(600.0, 150.0, 0.200)
            }
            LiveShotFault.STALLED_REACH_PUSH -> {
                // Dry Woodblock Double-Rap (800 Hz filtered noise burst, 40ms gap, 120ms total)
                generateDoubleRapWoodblock(800.0, 0.120)
            }

            // ── Family B: 3D Swing Plane Stability ──
            LiveShotFault.MID_SWING_PLANE_LOOP -> {
                // Inverted "U" Pitch Bend (700 Hz -> 350 Hz -> 800 Hz, 240 ms)
                generateInvertedUBend(700.0, 350.0, 800.0, 0.240)
            }
            LiveShotFault.OUT_OF_PLANE_WIPE -> {
                // Metallic Scrape / High-Q Bandpass Sweep (2200 Hz -> 700 Hz noise sweep, 200 ms)
                generateMetallicScrape(2200.0, 700.0, 0.200)
            }

            // ── Family C: Impact Wrist & Face Control ──
            LiveShotFault.LATE_WRIST_RESCUE -> {
                // Tight Dissonant Minor-Second Buzz (500 Hz + 530 Hz dual tone, 200 ms)
                generateDualToneBuzz(500.0, 530.0, 0.200)
            }
            LiveShotFault.IMPACT_FACE_TWIST -> {
                // Brassy High-to-Low "Crack" (1400 Hz -> 500 Hz sawtooth drop with fast decay, 180 ms)
                generateSawtoothDrop(1400.0, 500.0, 0.180)
            }

            // ── Family D: Tempo & Balance Envelope ──
            LiveShotFault.OVERSWING_LOSS_OF_SHAPE -> {
                // Wobbly Detuned Siren (600 Hz with heavy +/- 80 Hz LFO wobble, 250 ms)
                generateWobblySiren(600.0, 80.0, 8.0, 0.250)
            }

            // ── Clean Hit ──
            LiveShotFault.CLEAN_STROKE -> {
                // Crystal Harmonic Dual Chime (880 Hz + 1760 Hz decay, 150 ms)
                generateCrystalChime(880.0, 1760.0, 0.150)
            }
        }
    }

    // ─── Synth Generators ────────────────────────────────────────────────────────

    private fun generateSineSweep(startHz: Double, endHz: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        var phase = 0.0

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            val currentHz = startHz + (endHz - startHz) * t
            phase += TWO_PI * currentHz / SAMPLE_RATE

            val attack = min(1.0, i.toDouble() / (SAMPLE_RATE * 0.015))
            val release = min(1.0, (totalSamples - i).toDouble() / (SAMPLE_RATE * 0.030))
            val env = attack * release

            val sample = (sin(phase) * env * 28000).toInt().coerceIn(-32767, 32767)
            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateStepJump(f1: Double, f2: Double, durationSec: Double, isSquare: Boolean): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val split = totalSamples / 2
        val pcm = ByteArray(totalSamples * 2)
        var phase = 0.0

        for (i in 0 until totalSamples) {
            val freq = if (i < split) f1 else f2
            phase += TWO_PI * freq / SAMPLE_RATE

            val rawWave = if (isSquare) (if (sin(phase) >= 0) 0.8 else -0.8) else sin(phase)
            val env = min(1.0, (totalSamples - i).toDouble() / (SAMPLE_RATE * 0.040))
            val sample = (rawWave * env * 25000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateInvertedUBend(fStart: Double, fMin: Double, fEnd: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        var phase = 0.0

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            // Down from fStart to fMin in first half, up to fEnd in second half
            val currentHz = if (t <= 0.5) {
                fStart + (fMin - fStart) * (t * 2.0)
            } else {
                fMin + (fEnd - fMin) * ((t - 0.5) * 2.0)
            }
            phase += TWO_PI * currentHz / SAMPLE_RATE

            val attack = min(1.0, i.toDouble() / (SAMPLE_RATE * 0.010))
            val release = min(1.0, (totalSamples - i).toDouble() / (SAMPLE_RATE * 0.025))
            val sample = (sin(phase) * attack * release * 28000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateDoubleRapWoodblock(centerHz: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        val burstSamples = (SAMPLE_RATE * 0.040).toInt()
        val gapSamples = (SAMPLE_RATE * 0.040).toInt()

        for (i in 0 until totalSamples) {
            val isInBurst1 = i < burstSamples
            val isInBurst2 = i in (burstSamples + gapSamples) until (burstSamples * 2 + gapSamples)

            val amp = when {
                isInBurst1 -> exp(-i.toDouble() / (SAMPLE_RATE * 0.008))
                isInBurst2 -> exp(-(i - burstSamples - gapSamples).toDouble() / (SAMPLE_RATE * 0.008))
                else -> 0.0
            }

            val noise = (Math.random() * 2.0 - 1.0)
            val tone = sin(TWO_PI * centerHz * i / SAMPLE_RATE)
            val raw = (0.7 * tone + 0.3 * noise) * amp
            val sample = (raw * 28000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateResonantBoing(startHz: Double, endHz: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        var phase1 = 0.0

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            val freq = startHz + (endHz - startHz) * (t * t)
            phase1 += TWO_PI * freq / SAMPLE_RATE

            val env = exp(-t * 3.5)
            val wave = 0.7 * sin(phase1) + 0.3 * sin(phase1 * 2.0)
            val sample = (wave * env * 28000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateSawtoothDrop(startHz: Double, endHz: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        var phase = 0.0

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            val freq = startHz + (endHz - startHz) * t
            phase = (phase + freq / SAMPLE_RATE) % 1.0

            val saw = 2.0 * phase - 1.0
            val env = exp(-t * 4.0)
            val sample = (saw * env * 26000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateDualToneBuzz(f1: Double, f2: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)

        for (i in 0 until totalSamples) {
            val wave = 0.5 * sin(TWO_PI * f1 * i / SAMPLE_RATE) + 0.5 * sin(TWO_PI * f2 * i / SAMPLE_RATE)
            val env = min(1.0, (totalSamples - i).toDouble() / (SAMPLE_RATE * 0.030))
            val distorted = (wave * 1.4).coerceIn(-1.0, 1.0)
            val sample = (distorted * env * 26000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateMetallicScrape(startHz: Double, endHz: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            val center = startHz + (endHz - startHz) * t
            val noise = Math.random() * 2.0 - 1.0
            val carrier = sin(TWO_PI * center * i / SAMPLE_RATE)
            val ringMod = noise * carrier * 0.9

            val env = exp(-t * 2.8)
            val sample = (ringMod * env * 27000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateTapeStopDrop(startHz: Double, endHz: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        var phase = 0.0

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            val freq = startHz * (endHz / startHz).pow(t)
            phase += TWO_PI * freq / SAMPLE_RATE

            val env = (1.0 - t).pow(1.5)
            val sample = (sin(phase) * env * 28000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateWobblySiren(baseHz: Double, lfoDepth: Double, lfoRate: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)
        var phase = 0.0

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / SAMPLE_RATE
            val lfo = sin(TWO_PI * lfoRate * t)
            val currentHz = baseHz + lfoDepth * lfo
            phase += TWO_PI * currentHz / SAMPLE_RATE

            val env = min(1.0, ((totalSamples - i).toDouble() / (SAMPLE_RATE * 0.040)))
            val sample = (sin(phase) * env * 28000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }

    private fun generateCrystalChime(f1: Double, f2: Double, durationSec: Double): ByteArray {
        val totalSamples = (SAMPLE_RATE * durationSec).toInt()
        val pcm = ByteArray(totalSamples * 2)

        for (i in 0 until totalSamples) {
            val t = i.toDouble() / totalSamples
            val wave = 0.65 * sin(TWO_PI * f1 * i / SAMPLE_RATE) + 0.35 * sin(TWO_PI * f2 * i / SAMPLE_RATE)
            val env = exp(-t * 4.5)
            val sample = (wave * env * 28000).toInt().coerceIn(-32767, 32767)

            pcm[i * 2] = (sample and 0xFF).toByte()
            pcm[i * 2 + 1] = ((sample shr 8) and 0xFF).toByte()
        }
        return pcm
    }
}
