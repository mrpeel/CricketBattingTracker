package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import android.util.Log
import com.mrpeel.cricketbattingtracker.data.AppDatabase
import com.mrpeel.cricketbattingtracker.data.InningsEvent
import java.io.File
import java.nio.ByteBuffer

/**
 * Clips recorded session videos into short individual clips centered around shot impacts.
 */
object VideoClippingEngine {
    private const val TAG = "VideoClippingEngine"

    /**
     * Clips video files for all shots recorded in the current session.
     */
    suspend fun clipSessionShots(inningsId: Long, context: Context) {
        val prefs = context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
        val videoPath = prefs.getString("video_session_file_path", null)
        val startEpoch = prefs.getLong("video_session_start_epoch", 0L)

        if (videoPath == null || startEpoch == 0L) {
            Log.d(TAG, "No video recorded for session $inningsId. Skipping clipping.")
            return
        }

        val videoFile = File(videoPath)
        if (!videoFile.exists()) {
            Log.w(TAG, "Video file not found at: $videoPath")
            return
        }

        Log.d(TAG, "Starting video clipping for innings $inningsId. Video: $videoPath, Start: $startEpoch")

        val database = AppDatabase.getDatabase(context)
        val dao = database.inningsEventDao()
        val events = dao.getTimelineForInningsListSync(inningsId)

        val shots = events.filter { it.shotType != null && it.shotType != "Session Started" && it.shotType != "Session Ended" }
        if (shots.isEmpty()) {
            Log.d(TAG, "No shots found to clip.")
            return
        }

        // Output directory for shot clips
        val clipsDir = File(context.getExternalFilesDir("shot_clips"), "innings_$inningsId")
        clipsDir.mkdirs()

        for ((index, shot) in shots.withIndex()) {
            // Calculate starting time of shot relative to video start
            // Shot timestamp is wall-clock time of impact.
            val impactTimeRelMs = shot.timestamp - startEpoch
            if (impactTimeRelMs < 0) {
                Log.w(TAG, "Shot #${index + 1} timestamp is before video start. Skipping.")
                continue
            }

            // Clip ±2 seconds around impact
            val startMs = Math.max(0L, impactTimeRelMs - 2000L)
            val durationMs = 4000L

            val outClipFile = File(clipsDir, "shot_${shot.id}_${index + 1}.mp4")

            Log.d(TAG, "Clipping shot #${index + 1} (ID: ${shot.id}) at ${startMs}ms for ${durationMs}ms...")
            val success = try {
                trimVideo(videoFile, outClipFile, startMs, startMs + durationMs)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to clip shot #${shot.id}: ${e.message}", e)
                false
            }

            if (success && outClipFile.exists()) {
                Log.d(TAG, "Shot clip saved successfully: ${outClipFile.absolutePath}")
                dao.updateVideoFilePath(shot.id, outClipFile.absolutePath)
            }
        }

        // Clean up preference cache after processing
        prefs.edit()
            .remove("video_session_file_path")
            .remove("video_session_start_epoch")
            .apply()
    }

    /**
     * Extracts and muxes a portion of an MP4 file using Android's MediaExtractor and MediaMuxer.
     * This is fast (no re-encoding) but depends on keyframe boundaries.
     */
    private fun trimVideo(src: File, dst: File, startMs: Long, endMs: Long): Boolean {
        val extractor = MediaExtractor()
        var muxer: MediaMuxer? = null
        try {
            extractor.setDataSource(src.absolutePath)
            val trackCount = extractor.trackCount
            muxer = MediaMuxer(dst.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)

            // Track index mapping
            val trackIndexMap = HashMap<Int, Int>()
            var maxBufferSize = 0

            for (i in 0 until trackCount) {
                val format = extractor.getTrackFormat(i)
                val mime = format.getString(MediaFormat.KEY_MIME) ?: continue
                if (mime.startsWith("video/") || mime.startsWith("audio/")) {
                    extractor.selectTrack(i)
                    val newIndex = muxer.addTrack(format)
                    trackIndexMap[i] = newIndex

                    if (format.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) {
                        val inputSize = format.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE)
                        if (inputSize > maxBufferSize) {
                            maxBufferSize = inputSize
                        }
                    }
                }
            }

            if (maxBufferSize == 0) {
                maxBufferSize = 1024 * 1024 // Fallback 1MB buffer
            }

            muxer.start()

            // Seek to start position (convert to microseconds)
            val startUs = startMs * 1000
            val endUs = endMs * 1000
            extractor.seekTo(startUs, MediaExtractor.SEEK_TO_PREVIOUS_SYNC)

            val buffer = ByteBuffer.allocate(maxBufferSize)
            val bufferInfo = MediaCodec.BufferInfo()

            while (true) {
                val trackIndex = extractor.sampleTrackIndex
                if (trackIndex < 0) break

                val sampleTimeUs = extractor.sampleTime
                if (sampleTimeUs > endUs) break

                buffer.clear()
                val sampleSize = extractor.readSampleData(buffer, 0)
                if (sampleSize < 0) break

                bufferInfo.offset = 0
                bufferInfo.size = sampleSize
                bufferInfo.presentationTimeUs = sampleTimeUs - startUs
                bufferInfo.flags = extractor.sampleFlags

                val newTrackIndex = trackIndexMap[trackIndex]
                if (newTrackIndex != null) {
                    muxer.writeSampleData(newTrackIndex, buffer, bufferInfo)
                }

                extractor.advance()
            }

            return true
        } finally {
            try {
                extractor.release()
            } catch (e: Exception) {}
            try {
                muxer?.stop()
                muxer?.release()
            } catch (e: Exception) {}
        }
    }
}
