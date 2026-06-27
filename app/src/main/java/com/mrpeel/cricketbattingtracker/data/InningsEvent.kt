package com.mrpeel.cricketbattingtracker.data

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "innings_events")
data class InningsEvent(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val inningsId: Long, // Grouping factor for a single match/innings
    val timestamp: Long,
    val description: String,
    val batSpeed: Float? = null,
    val impactForce: Float? = null,   // raw peak accel in g (not displayed directly)
    val impactTimeMs: Long? = null,    // reaction time: backlift→contact in ms
    val distanceRun: Float? = null,
    val shotType: String? = null,
    val efficiency: Float? = null,
    val backliftAngle: Float? = null,
    val followThroughAngle: Float? = null,
    val wristRollDeg: Float? = null,    // wrist rotation during follow-through
    val location: String? = null,       // reverse-geocoded street/suburb combo
    val bladeAngle: Float? = null,
    val bladeClass: String? = null,
    val launchAngle: Float? = null,
    val launchClass: String? = null
)

@Entity(tableName = "heart_rate_events")
data class HeartRateEvent(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val inningsId: Long,
    val timestamp: Long,
    val beatsPerMinute: Long
)

@Dao
interface InningsEventDao {
    @Query("SELECT * FROM innings_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    fun getTimelineForInnings(inningsId: Long): Flow<List<InningsEvent>>

    @Query("SELECT * FROM innings_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    suspend fun getTimelineForInningsListSync(inningsId: Long): List<InningsEvent>

    @Query("SELECT * FROM innings_events ORDER BY timestamp DESC")
    fun getAllEventsFlow(): Flow<List<InningsEvent>>

    @Insert
    suspend fun insertEvent(event: InningsEvent)

    @Insert
    suspend fun insertHeartRate(hrEvent: HeartRateEvent)

    @Query("SELECT * FROM heart_rate_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    suspend fun getHeartRatesForInningsSync(inningsId: Long): List<HeartRateEvent>
    
    @Query("SELECT MAX(inningsId) FROM innings_events")
    suspend fun getLatestInningsId(): Long?

    @Query("SELECT MAX(inningsId) FROM innings_events")
    fun getLatestInningsIdFlow(): Flow<Long?>

    @Query("SELECT DISTINCT inningsId FROM innings_events ORDER BY inningsId DESC")
    suspend fun getAllUniqueInningsIds(): List<Long>

    @Query("SELECT location FROM innings_events WHERE location IS NOT NULL AND location != 'Net Practice' AND location != '' ORDER BY timestamp DESC LIMIT 1")
    suspend fun getLastResolvedLocation(): String?
}
