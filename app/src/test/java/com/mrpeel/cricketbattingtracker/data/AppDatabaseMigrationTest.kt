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
    fun testRoomV12IdentityHashConsistency() {
        // Authoritative Room v12 expected identity hash from AppDatabase_Impl.java
        val expectedV12Hash = "36946e68af413e8cc2fca0555e69b534"

        // Verify pipelines/reprocess_sessions.py contains this exact hash
        val reprocessScript = File("../pipelines/reprocess_sessions.py").takeIf { it.exists() }
            ?: File("pipelines/reprocess_sessions.py")
        assertTrue("reprocess_sessions.py must exist", reprocessScript.exists())
        val scriptContent = reprocessScript.readText()
        assertTrue(
            "reprocess_sessions.py must insert the Room v12 hash to prevent crash on phone launch",
            scriptContent.contains("VALUES(42, '$expectedV12Hash')")
        )
        assertFalse(
            "reprocess_sessions.py must NOT contain the legacy v11 hash",
            scriptContent.contains("0663d4b5cc3a66d7b6e980a4f2ee357c")
        )
    }
}
