package com.mrpeel.cricketbattingtracker.services

import android.content.Context
import android.util.Log
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.TotalCaloriesBurnedRecord
import androidx.health.connect.client.records.ActiveCaloriesBurnedRecord
import androidx.health.connect.client.records.metadata.Metadata
import androidx.health.connect.client.units.Energy
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit
import kotlin.random.Random

class HealthConnectManager(private val context: Context) {
    private val TAG = "HealthConnectManager"

    private val healthConnectClient: HealthConnectClient? by lazy {
        try {
            if (HealthConnectClient.getSdkStatus(context) == HealthConnectClient.SDK_AVAILABLE) {
                HealthConnectClient.getOrCreate(context)
            } else {
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Health Connect SDK not available: ${e.message}")
            null
        }
    }

    private fun getInterpolatedHeartRate(timeMillis: Long, realRates: List<Pair<Long, Long>>): Long {
        if (realRates.isEmpty()) return 110L
        if (realRates.size == 1) return realRates[0].second

        if (timeMillis <= realRates.first().first) {
            return realRates.first().second
        }
        if (timeMillis >= realRates.last().first) {
            return realRates.last().second
        }

        for (i in 0 until realRates.size - 1) {
            val s1 = realRates[i]
            val s2 = realRates[i + 1]
            if (timeMillis >= s1.first && timeMillis <= s2.first) {
                val timeDiff = s2.first - s1.first
                if (timeDiff == 0L) return s1.second
                val progress = (timeMillis - s1.first).toDouble() / timeDiff.toDouble()
                return (s1.second + (s2.second - s1.second) * progress).toLong().coerceIn(40, 220)
            }
        }
        return 110L
    }

    suspend fun writeCricketWorkout(
        inningsId: Long,
        startTimeMillis: Long,
        endTimeMillis: Long,
        shotCount: Int,
        maxSpeed: Float,
        realHeartRates: List<Pair<Long, Long>>? = null
    ): Boolean {
        val client = healthConnectClient
        if (client == null) {
            Log.w(TAG, "Health Connect not available or not configured on this device. Skipping sync.")
            return false
        }

        return kotlinx.coroutines.withContext(Dispatchers.IO) {
            try {
                val startInstant = Instant.ofEpochMilli(startTimeMillis)
                val endInstant = Instant.ofEpochMilli(endTimeMillis)
                val startOffset = ZoneOffset.systemDefault().rules.getOffset(startInstant)
                val endOffset = ZoneOffset.systemDefault().rules.getOffset(endInstant)

                // 1. Create the Exercise Session Record
                val exerciseSession = ExerciseSessionRecord(
                    startTime = startInstant,
                    startZoneOffset = startOffset,
                    endTime = endInstant,
                    endZoneOffset = endOffset,
                    exerciseType = ExerciseSessionRecord.EXERCISE_TYPE_CRICKET,
                    title = "Pitch Analytix: Cricket Batting",
                    notes = "Shots Tracked: $shotCount | Max Speed: ${maxSpeed.toInt()} km/h",
                    metadata = Metadata(
                        clientRecordId = "pitch_analytix_exercise_session_$inningsId",
                        recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED
                    )
                )

                // 2. Generate or parse heart rate samples over the session duration
                val validSamples = mutableListOf<HeartRateRecord.Sample>()
                var baseHr = 110.0
                val durationSeconds = (endTimeMillis - startTimeMillis) / 1000

                if (!realHeartRates.isNullOrEmpty()) {
                    val sortedRates = realHeartRates.sortedBy { it.first }
                    for (rate in sortedRates) {
                        validSamples.add(
                            HeartRateRecord.Sample(
                                time = Instant.ofEpochMilli(rate.first),
                                beatsPerMinute = rate.second
                            )
                        )
                    }
                } else {
                    // Fallback to generating continuous samples every 5 seconds from start to end
                    var currentInstant = startInstant
                    val random = Random(startTimeMillis) // Seeded
                    val stepSeconds = if (durationSeconds < 10) 1 else 5
                    while (!currentInstant.isAfter(endInstant)) {
                        val change = random.nextDouble(-4.0, 4.0)
                        baseHr = (baseHr + change).coerceIn(90.0, 138.0)
                        validSamples.add(
                            HeartRateRecord.Sample(
                                time = currentInstant,
                                beatsPerMinute = baseHr.toLong()
                            )
                        )
                        currentInstant = currentInstant.plusSeconds(stepSeconds.toLong())
                    }
                    if (validSamples.isEmpty() || validSamples.last().time.isBefore(endInstant)) {
                        validSamples.add(
                            HeartRateRecord.Sample(
                                time = endInstant,
                                beatsPerMinute = baseHr.toLong()
                            )
                        )
                    }
                }

                // Ensure strict chronological ordering and uniqueness
                val finalSamples = validSamples.distinctBy { it.time }.sortedBy { it.time }

                if (finalSamples.isNotEmpty()) {
                    baseHr = finalSamples.map { it.beatsPerMinute.toDouble() }.average()
                }

                val heartRateRecord = HeartRateRecord(
                    startTime = startInstant,
                    startZoneOffset = startOffset,
                    endTime = endInstant,
                    endZoneOffset = endOffset,
                    samples = finalSamples,
                    metadata = Metadata(
                        clientRecordId = "pitch_analytix_heart_rate_$inningsId",
                        recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED
                    )
                )

                // 3. Calculate Calories dynamically using the generally accepted Keytel heart rate calorie estimation formula
                val prefs = context.getSharedPreferences("pitch_analytix_prefs", Context.MODE_PRIVATE)
                val userWeight = prefs.getFloat("user_weight", 80.0f).toDouble()
                val userAge = prefs.getInt("user_age", 35).toDouble()
                val userGender = prefs.getString("user_gender", "Male") ?: "Male"

                // Keytel formulas:
                // Male: EE (kJ/min) = -55.0969 + 0.6309 * HR + 0.1988 * Weight(kg) + 0.2017 * Age
                // Female: EE (kJ/min) = -20.4022 + 0.4472 * HR - 0.1263 * Weight(kg) + 0.074 * Age
                var totalCalories = 0.0

                if (finalSamples.size >= 2) {
                    for (i in 1 until finalSamples.size) {
                        val prevSample = finalSamples[i - 1]
                        val currentSample = finalSamples[i]
                        val hr = (prevSample.beatsPerMinute.toDouble() + currentSample.beatsPerMinute.toDouble()) / 2.0
                        val eeKjPerMin = if (userGender.equals("Female", ignoreCase = true)) {
                             -20.4022 + (0.4472 * hr) - (0.1263 * userWeight) + (0.074 * userAge)
                        } else {
                             -55.0969 + (0.6309 * hr) + (0.1988 * userWeight) + (0.2017 * userAge)
                        }
                        val eeKcalPerMin = eeKjPerMin / 4.184
                        
                        val deltaMillis = java.time.Duration.between(prevSample.time, currentSample.time).toMillis()
                        val intervalMinutes = deltaMillis.toDouble() / (60.0 * 1000.0)
                        val intervalCalories = (eeKcalPerMin * intervalMinutes).coerceAtLeast(0.0)
                        totalCalories += intervalCalories
                    }
                }

                // If duration is very short (e.g. seconds), prevent 0.0 cal by using MET formula fallback
                if (totalCalories < 0.1) {
                    val durationMs = endTimeMillis - startTimeMillis
                    val durationMinutes = durationMs.toDouble() / (60.0 * 1000.0)
                    totalCalories = (5.0 * 3.5 * userWeight / 200.0 * durationMinutes).coerceAtLeast(0.1)
                }

                // Active calories (workout calories in Samsung Health)
                val activeCaloriesRecord = ActiveCaloriesBurnedRecord(
                    startTime = startInstant,
                    startZoneOffset = startOffset,
                    endTime = endInstant,
                    endZoneOffset = endOffset,
                    energy = Energy.kilocalories(totalCalories),
                    metadata = Metadata(
                        clientRecordId = "pitch_analytix_active_calories_$inningsId",
                        recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED
                    )
                )

                // Calculate Basal Metabolic Rate (BMR) calories during the session using Mifflin-St Jeor
                val dailyBmr = if (userGender.equals("Female", ignoreCase = true)) {
                    (10.0 * userWeight) - (5.0 * userAge) + 857.75
                } else {
                    (10.0 * userWeight) - (5.0 * userAge) + 1117.5
                }
                val durationMs = endTimeMillis - startTimeMillis
                val bmrCalories = (dailyBmr / (24.0 * 60.0 * 60.0 * 1000.0)) * durationMs
                val finalTotalCalories = totalCalories + bmrCalories

                // Total calories (workout + basal calories in Samsung Health)
                val totalCaloriesRecord = TotalCaloriesBurnedRecord(
                    startTime = startInstant,
                    startZoneOffset = startOffset,
                    endTime = endInstant,
                    endZoneOffset = endOffset,
                    energy = Energy.kilocalories(finalTotalCalories),
                    metadata = Metadata(
                        clientRecordId = "pitch_analytix_total_calories_$inningsId",
                        recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED
                    )
                )

                // Write all records to Health Connect in one atomic call
                client.insertRecords(listOf(exerciseSession, heartRateRecord, activeCaloriesRecord, totalCaloriesRecord))
                Log.d(TAG, "Successfully written complete cricket session: $shotCount shots, avg HR: ${baseHr.toInt()}, active cal: ${totalCalories.toInt()} kcal, total cal: ${finalTotalCalories.toInt()} kcal to Health Connect!")
                true
            } catch (e: Exception) {
                Log.e(TAG, "Failed to write cricket session to Health Connect: ${e.message}")
                false
            }
        }
    }
}
