package com.mrpeel.cricketbattingtracker.services

import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

class PhoneSwingDetectorAdversarialTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    @Test
    fun testBinaryDecodingTruncatedFiles() {
        val testDir = tempFolder.newFolder("truncated_test")

        // 1. Zero-byte file
        val emptyFile = File(testDir, "empty.bin").apply { writeBytes(ByteArray(0)) }
        val emptyRes = PhoneSwingDetector.parseWatchIMUBin(emptyFile)
        assertTrue("Zero-byte file must return empty list", emptyRes.isEmpty())

        // 2. 5-byte file (less than long timestamp)
        val shortFile5 = File(testDir, "short5.bin").apply { writeBytes(ByteArray(5)) }
        val shortRes5 = PhoneSwingDetector.parseWatchIMUBin(shortFile5)
        assertTrue("5-byte file must return empty list", shortRes5.isEmpty())

        // 3. 23-byte file (1 byte short of 24-byte WatchIMU record)
        val shortFile23 = File(testDir, "short23.bin").apply { writeBytes(ByteArray(23)) }
        val shortRes23 = PhoneSwingDetector.parseWatchIMUBin(shortFile23)
        assertTrue("23-byte file must return empty list without crashing", shortRes23.isEmpty())
    }

    @Test
    fun testBinaryDecodingValidRecordPlusTrailingGarbage() {
        val testDir = tempFolder.newFolder("trailing_test")
        val file = File(testDir, "partial.bin")

        // 24-byte valid record + 13 bytes of trailing truncated record = 37 bytes
        val buffer = ByteBuffer.allocate(37).order(ByteOrder.LITTLE_ENDIAN)
        buffer.putLong(1000000000L) // timeNanos
        buffer.putFloat(1.0f)       // sec
        buffer.putFloat(0.5f)       // x
        buffer.putFloat(-9.81f)     // y
        buffer.putFloat(0.2f)       // z
        buffer.put(ByteArray(13) { 0xFF.toByte() }) // trailing garbage

        file.writeBytes(buffer.array())

        val res = PhoneSwingDetector.parseWatchIMUBin(file)
        assertEquals("Must parse exactly 1 complete record and ignore trailing bytes", 1, res.size)
        assertEquals(1000000000L, res[0].timeNanos)
        assertEquals(0.5f, res[0].x, 1e-4f)
        assertEquals(-9.81f, res[0].y, 1e-4f)
        assertEquals(0.2f, res[0].z, 1e-4f)
    }

    @Test
    fun testWatchRotBinaryDecodingTruncatedFiles() {
        val testDir = tempFolder.newFolder("rot_truncated")
        // WatchRot record is 28 bytes (timeNanos: Long + sec: Float + qx: Float + qy: Float + qz: Float + qw: Float)
        // 27 bytes is truncated
        val file = File(testDir, "rot_short.bin").apply { writeBytes(ByteArray(27)) }
        val res = PhoneSwingDetector.parseWatchRotBin(file)
        assertTrue("27-byte rot file must return empty list without throwing", res.isEmpty())
    }

    @Test
    fun testPolarBinaryDecodingTruncatedFiles() {
        val testDir = tempFolder.newFolder("polar_truncated")
        // Polar record is 28 bytes (phoneMs: Long + sensorNs: Long + x: Float + y: Float + z: Float)
        val file = File(testDir, "PolarAccelerometer.bin").apply { writeBytes(ByteArray(15)) }
        val res = PhoneSwingDetector.parsePolarCsv(file, isGyro = false)
        assertTrue("Truncated polar binary must return empty list without throwing", res.isEmpty())
    }

    @Test
    fun testZeroAllocationBinarySearchEmptyLists() {
        // Must return 0 without throwing ArrayIndexOutOfBoundsException or IndexOutOfBoundsException
        assertEquals(0, PhoneSwingDetector.findPolarStart(emptyList(), 1000L))
        assertEquals(0, PhoneSwingDetector.findWatchIMUStart(emptyList(), 1000L))
        assertEquals(0, PhoneSwingDetector.findWatchRotStart(emptyList(), 1000L))
    }

    @Test
    fun testZeroAllocationBinarySearchBoundaryConditions() {
        val samples = listOf(
            PhoneSwingDetector.WatchIMUSample(timeNanos = 100L, elapsedSecs = 0.1, x = 0f, y = 0f, z = 0f, mag = 0f),
            PhoneSwingDetector.WatchIMUSample(timeNanos = 200L, elapsedSecs = 0.2, x = 0f, y = 0f, z = 0f, mag = 0f),
            PhoneSwingDetector.WatchIMUSample(timeNanos = 300L, elapsedSecs = 0.3, x = 0f, y = 0f, z = 0f, mag = 0f)
        )

        // 1. Target before first sample -> index 0
        assertEquals(0, PhoneSwingDetector.findWatchIMUStart(samples, 50L))
        // 2. Target exactly on first sample -> index 0
        assertEquals(0, PhoneSwingDetector.findWatchIMUStart(samples, 100L))
        // 3. Target between samples -> next index
        assertEquals(1, PhoneSwingDetector.findWatchIMUStart(samples, 150L))
        // 4. Target exactly on last sample -> index 2
        assertEquals(2, PhoneSwingDetector.findWatchIMUStart(samples, 300L))
        // 5. Target after last sample -> size (3)
        assertEquals(3, PhoneSwingDetector.findWatchIMUStart(samples, 350L))
    }

    @Test
    fun testTimeAlignmentExtremeDriftInversion() {
        // Polar_phoneMs = watch_wallMs * (1 + driftRate) + offsetMs
        val alignment = PhoneSwingDetector.TimeAlignment(
            offsetMs = 45000.0, // 45 second offset
            driftRate = 0.0005  // 500 ppm drift
        )

        val watchMs = 1720000000000L
        val polarMs = alignment.watchToPolarMs(watchMs)
        val reconstructedWatchMs = alignment.polarToWatchMs(polarMs)

        // Inversion must reconstruct the original watch wall timestamp within 1ms
        assertEquals(watchMs.toDouble(), reconstructedWatchMs.toDouble(), 1.0)
    }
}
