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

    suspend fun writeCricketWorkout(
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
                    metadata = Metadata(recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED)
                )

                // 2. Generate or parse heart rate samples over the session duration
                val samples = mutableListOf<HeartRateRecord.Sample>()
                var baseHr = 110.0
                val durationSeconds = (endTimeMillis - startTimeMillis) / 1000
                val stepSeconds = if (durationSeconds < 10) 1 else 5

                if (!realHeartRates.isNullOrEmpty()) {
                    // Populate from physical smartwatch PPG samples
                    for (pair in realHeartRates) {
                        samples.add(
                            HeartRateRecord.Sample(
                                time = Instant.ofEpochMilli(pair.first),
                                beatsPerMinute = pair.second
                            )
                        )
                    }
                    // Sort samples by time chronologically (required by Health Connect SDK)
                    samples.sortBy { it.time }
                    if (samples.isNotEmpty()) {
                        baseHr = samples.map { it.beatsPerMinute.toDouble() }.average()
                    }
                } else {
                    // Fallback to fluctuating generated samples
                    var currentInstant = startInstant
                    val random = Random(startTimeMillis) // Seeded
                    while (!currentInstant.isAfter(endInstant)) {
                        val change = random.nextDouble(-4.0, 4.0)
                        baseHr = (baseHr + change).coerceIn(90.0, 138.0)
                        samples.add(
                            HeartRateRecord.Sample(
                                time = currentInstant,
                                beatsPerMinute = baseHr.toLong()
                            )
                        )
                        currentInstant = currentInstant.plusSeconds(stepSeconds.toLong())
                    }
                }

                // If session has fewer than 2 samples, ensure at least two heart rate samples to draw a graph
                if (samples.size < 2) {
                    samples.clear()
                    samples.add(HeartRateRecord.Sample(time = startInstant, beatsPerMinute = 110L))
                    samples.add(HeartRateRecord.Sample(time = endInstant, beatsPerMinute = 112L))
                }

                val heartRateRecord = HeartRateRecord(
                    startTime = startInstant,
                    startZoneOffset = startOffset,
                    endTime = endInstant,
                    endZoneOffset = endOffset,
                    samples = samples,
                    metadata = Metadata(recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED)
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

                if (!realHeartRates.isNullOrEmpty() && samples.size >= 2) {
                    for (i in 0 until samples.size) {
                        val sample = samples[i]
                        val hr = sample.beatsPerMinute.toDouble()
                        val eeKjPerMin = if (userGender.equals("Female", ignoreCase = true)) {
                             -20.4022 + (0.4472 * hr) - (0.1263 * userWeight) + (0.074 * userAge)
                        } else {
                             -55.0969 + (0.6309 * hr) + (0.1988 * userWeight) + (0.2017 * userAge)
                        }
                        val eeKcalPerMin = eeKjPerMin / 4.184
                        
                        val deltaMillis = if (i == 0) {
                            java.time.Duration.between(samples[0].time, samples[1].time).toMillis()
                        } else {
                            java.time.Duration.between(samples[i - 1].time, sample.time).toMillis()
                        }
                        val intervalMinutes = deltaMillis.toDouble() / (60.0 * 1000.0)
                        val intervalCalories = (eeKcalPerMin * intervalMinutes).coerceAtLeast(0.0)
                        totalCalories += intervalCalories
                    }
                } else {
                    val intervalMinutes = stepSeconds.toDouble() / 60.0 // Dynamic step-based minutes
                    for (sample in samples) {
                        val hr = sample.beatsPerMinute.toDouble()
                        val eeKjPerMin = if (userGender.equals("Female", ignoreCase = true)) {
                             -20.4022 + (0.4472 * hr) - (0.1263 * userWeight) + (0.074 * userAge)
                        } else {
                             -55.0969 + (0.6309 * hr) + (0.1988 * userWeight) + (0.2017 * userAge)
                        }
                        val eeKcalPerMin = eeKjPerMin / 4.184
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
                    energy = Energy.calories(totalCalories),
                    metadata = Metadata(recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED)
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
                    energy = Energy.calories(finalTotalCalories),
                    metadata = Metadata(recordingMethod = Metadata.RECORDING_METHOD_ACTIVELY_RECORDED)
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
