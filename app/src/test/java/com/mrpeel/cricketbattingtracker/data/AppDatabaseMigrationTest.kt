package com.mrpeel.cricketbattingtracker.data

import androidx.sqlite.db.SupportSQLiteDatabase
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.lang.reflect.Proxy

class AppDatabaseMigrationTest {

    @Test
    fun testMigration11To12ExecutesAllSevenColumnAdditions() {
        val executedSql = mutableListOf<String>()
        val fakeDb = Proxy.newProxyInstance(
            SupportSQLiteDatabase::class.java.classLoader,
            arrayOf(SupportSQLiteDatabase::class.java)
        ) { _, method, args ->
            if (method.name == "execSQL" && args != null && args.isNotEmpty()) {
                executedSql.add(args[0] as String)
            }
            null
        } as SupportSQLiteDatabase

        AppDatabase.MIGRATION_11_12.migrate(fakeDb)

        assertEquals("Must execute exactly 7 ALTER TABLE commands", 7, executedSql.size)
        assertTrue(executedSql.any { it.contains("blade_pitch_deg REAL") })
        assertTrue(executedSql.any { it.contains("face_angle_deg REAL") })
        assertTrue(executedSql.any { it.contains("swing_yaw_deg REAL") })
        assertTrue(executedSql.any { it.contains("relative_wrist_angle_deg REAL") })
        assertTrue(executedSql.any { it.contains("azimuth_deviation_deg REAL") })
        assertTrue(executedSql.any { it.contains("polar_mount_type TEXT") })
        assertTrue(executedSql.any { it.contains("is_kinematically_valid INTEGER") })
    }

    @Test
    fun testEnsureSchemaIntegrityRepairsMissingV12Columns() {
        // Simulate a database with only 50 columns (missing the 7 v12 columns)
        val legacy50Columns = listOf(
            "id", "inningsId", "timestamp", "description", "batSpeed", "impactForce",
            "impactTimeMs", "distanceRun", "shotType", "efficiency", "backliftAngle",
            "followThroughAngle", "wristRollDeg", "location", "bladeAngle", "bladeClass",
            "launchAngle", "launchClass", "bottom_hand_gyro_peak", "bottom_hand_acc_peak",
            "bottom_hand_gyro_ratio", "bottom_hand_acc_ratio", "bottom_hand_time_lead_ms",
            "bottom_hand_sync_score", "bottom_hand_mag_peak", "bottom_hand_mag_delta",
            "bottom_hand_mag_x", "bottom_hand_mag_y", "bottom_hand_mag_z",
            "swing_feature_s1_gyro_y_std", "swing_feature_s1_gyro_z_std", "swing_feature_s1_delta_x",
            "swing_feature_s1_delta_z", "swing_feature_s2_gyro_mag", "swing_feature_s2_grav_y_mean",
            "swing_feature_s2_delta_x", "swing_feature_s2_delta_z", "swing_feature_s3_roll_deg",
            "swing_feature_s3_yaw_deg", "swing_feature_s3_delta_x", "swing_feature_s3_delta_z",
            "swing_feature_s3_plane_ratio", "swing_feature_s3_gyro_y_min", "videoFilePath",
            "polar_mount_mode", "bat_id", "bat_name", "bat_weight_grams",
            "bat_sensor_offset_knob_cm", "bat_sensor_offset_toe_cm"
        )

        var cursorRowIdx = -1
        val fakeCursor = Proxy.newProxyInstance(
            android.database.Cursor::class.java.classLoader,
            arrayOf(android.database.Cursor::class.java)
        ) { _, method, args ->
            when (method.name) {
                "getColumnIndex" -> if (args?.get(0) == "name") 0 else -1
                "moveToNext" -> {
                    cursorRowIdx++
                    cursorRowIdx < legacy50Columns.size
                }
                "getString" -> legacy50Columns[cursorRowIdx]
                "close" -> null
                else -> null
            }
        } as android.database.Cursor

        val executedSql = mutableListOf<String>()
        val fakeDb = Proxy.newProxyInstance(
            SupportSQLiteDatabase::class.java.classLoader,
            arrayOf(SupportSQLiteDatabase::class.java)
        ) { _, method, args ->
            when (method.name) {
                "query" -> fakeCursor
                "execSQL" -> {
                    if (args != null && args.isNotEmpty()) {
                        executedSql.add(args[0] as String)
                    }
                    null
                }
                else -> null
            }
        } as SupportSQLiteDatabase

        AppDatabase.ensureSchemaIntegrity(fakeDb)

        // All 7 missing v12 columns must have been repaired via ALTER TABLE
        assertEquals("Must execute exactly 7 repair ALTER TABLE statements", 7, executedSql.size)
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN blade_pitch_deg REAL") })
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN face_angle_deg REAL") })
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN swing_yaw_deg REAL") })
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN relative_wrist_angle_deg REAL") })
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN azimuth_deviation_deg REAL") })
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN polar_mount_type TEXT") })
        assertTrue(executedSql.any { it.contains("ALTER TABLE innings_events ADD COLUMN is_kinematically_valid INTEGER") })
    }

    @Test
    fun testEnsureSchemaIntegrityNoOpWhenAllColumnsPresent() {
        val all57Columns = AppDatabase.REQUIRED_INNINGS_EVENT_COLUMNS.keys.toList()

        var cursorRowIdx = -1
        val fakeCursor = Proxy.newProxyInstance(
            android.database.Cursor::class.java.classLoader,
            arrayOf(android.database.Cursor::class.java)
        ) { _, method, args ->
            when (method.name) {
                "getColumnIndex" -> if (args?.get(0) == "name") 0 else -1
                "moveToNext" -> {
                    cursorRowIdx++
                    cursorRowIdx < all57Columns.size
                }
                "getString" -> all57Columns[cursorRowIdx]
                "close" -> null
                else -> null
            }
        } as android.database.Cursor

        val executedSql = mutableListOf<String>()
        val fakeDb = Proxy.newProxyInstance(
            SupportSQLiteDatabase::class.java.classLoader,
            arrayOf(SupportSQLiteDatabase::class.java)
        ) { _, method, args ->
            when (method.name) {
                "query" -> fakeCursor
                "execSQL" -> {
                    if (args != null && args.isNotEmpty()) {
                        executedSql.add(args[0] as String)
                    }
                    null
                }
                else -> null
            }
        } as SupportSQLiteDatabase

        AppDatabase.ensureSchemaIntegrity(fakeDb)

        assertEquals("No ALTER TABLE should be executed when all columns are present", 0, executedSql.size)
    }

    @Test
    fun testReprocessSessionsDDLMatchesRoomV12Entity() {
        val reprocessScript = File("../pipelines/reprocess_sessions.py").takeIf { it.exists() }
            ?: File("pipelines/reprocess_sessions.py")
        assertTrue("reprocess_sessions.py must exist", reprocessScript.exists())
        val scriptContent = reprocessScript.readText()

        // 1. Check Room v12 identity hash
        val expectedV12Hash = "36946e68af413e8cc2fca0555e69b534"
        assertTrue(
            "reprocess_sessions.py must insert the Room v12 hash",
            scriptContent.contains("VALUES(42, '$expectedV12Hash')")
        )

        // 2. Check all 7 v12 orientation and kinematic guard columns are in CREATE TABLE
        val v12Columns = listOf(
            "blade_pitch_deg REAL",
            "face_angle_deg REAL",
            "swing_yaw_deg REAL",
            "relative_wrist_angle_deg REAL",
            "azimuth_deviation_deg REAL",
            "polar_mount_type TEXT",
            "is_kinematically_valid INTEGER"
        )
        for (col in v12Columns) {
            assertTrue("reprocess_sessions.py CREATE TABLE must define '$col'", scriptContent.contains(col))
        }

        // 3. Check every required column from Room entity is defined in CREATE TABLE
        for (colName in AppDatabase.REQUIRED_INNINGS_EVENT_COLUMNS.keys) {
            assertTrue(
                "reprocess_sessions.py CREATE TABLE must define column '$colName'",
                scriptContent.contains(Regex("""\b$colName\b"""))
            )
        }

        // 4. Verify INSERT INTO statement includes all 7 columns and placeholders match
        val insertMatch = Regex("""INSERT INTO innings_events\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)""", RegexOption.DOT_MATCHES_ALL)
            .findAll(scriptContent)
            .firstOrNull { it.value.contains("blade_pitch_deg") }

        assertNotNull("reprocess_sessions.py must have an INSERT INTO innings_events containing blade_pitch_deg", insertMatch)
        val colsSection = insertMatch!!.groupValues[1]
        val valsSection = insertMatch.groupValues[2]

        val insertedCols = colsSection.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        val placeholders = valsSection.split(",").map { it.trim() }.filter { it.isNotEmpty() }

        assertEquals(
            "Inserted column count must match placeholder count in reprocess_sessions.py INSERT",
            insertedCols.size,
            placeholders.size
        )

        for (col in listOf("blade_pitch_deg", "face_angle_deg", "swing_yaw_deg", "relative_wrist_angle_deg", "azimuth_deviation_deg", "polar_mount_type", "is_kinematically_valid")) {
            assertTrue("INSERT INTO columns must include '$col'", insertedCols.contains(col))
        }
    }
}
