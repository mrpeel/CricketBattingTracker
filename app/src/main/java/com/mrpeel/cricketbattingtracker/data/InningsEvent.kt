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
    val impactForce: Float? = null,
    val distanceRun: Float? = null
)

@Dao
interface InningsEventDao {
    @Query("SELECT * FROM innings_events WHERE inningsId = :inningsId ORDER BY timestamp ASC")
    fun getTimelineForInnings(inningsId: Long): Flow<List<InningsEvent>>

    @Insert
    suspend fun insertEvent(event: InningsEvent)
    
    @Query("SELECT MAX(inningsId) FROM innings_events")
    suspend fun getLatestInningsId(): Long?
}
