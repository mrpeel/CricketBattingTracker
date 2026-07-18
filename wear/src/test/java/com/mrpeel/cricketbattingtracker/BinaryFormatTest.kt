package com.mrpeel.cricketbattingtracker

import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sqrt

class BinaryFormatTest {

    @get:Rule
    val tempFolder = TemporaryFolder()

    @Test
    fun testStandardIMUBinaryWriteAndRead() {
        val file = tempFolder.newFile("WatchAccelerometer.bin")
        val timestamp = 1718392182000L
        val elapsed = 1.234f
        val x = 9.81f
        val y = -0.15f
        val z = 1.56f

        // Write
        FileOutputStream(file).use { out ->
            val buf = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN)
            buf.putLong(timestamp)
            buf.putFloat(elapsed)
            buf.putFloat(x)
            buf.putFloat(y)
            buf.putFloat(z)
            out.write(buf.array())
        }

        // Read and Assert
        assertTrue(file.exists())
        assertEquals(24L, file.length())

        val bytes = file.readBytes()
        val readBuf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(timestamp, readBuf.long)
        assertEquals(elapsed, readBuf.float, 1e-6f)
        assertEquals(x, readBuf.float, 1e-6f)
        assertEquals(y, readBuf.float, 1e-6f)
        assertEquals(z, readBuf.float, 1e-6f)
    }

    @Test
    fun testOrientationBinaryWriteAndRead() {
        val file = tempFolder.newFile("WatchGameOrientation.bin")
        val timestamp = 1718392183000L
        val elapsed = 2.345f
        val qx = 0.707f
        val qy = 0.0f
        val qz = 0.0f
        val qw = 0.707f

        // Write
        FileOutputStream(file).use { out ->
            val buf = ByteBuffer.allocate(28).order(ByteOrder.LITTLE_ENDIAN)
            buf.putLong(timestamp)
            buf.putFloat(elapsed)
            buf.putFloat(qx)
            buf.putFloat(qy)
            buf.putFloat(qz)
            buf.putFloat(qw)
            out.write(buf.array())
        }

        // Read and Assert
        assertTrue(file.exists())
        assertEquals(28L, file.length())

        val bytes = file.readBytes()
        val readBuf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(timestamp, readBuf.long)
        assertEquals(elapsed, readBuf.float, 1e-6f)
        assertEquals(qx, readBuf.float, 1e-6f)
        assertEquals(qy, readBuf.float, 1e-6f)
        assertEquals(qz, readBuf.float, 1e-6f)
        assertEquals(qw, readBuf.float, 1e-6f)
    }

    @Test
    fun testStepsBinaryWriteAndRead() {
        val file = tempFolder.newFile("WatchSteps.bin")
        val timestamp = 1718392184000L
        val elapsed = 3.456f

        // Write
        FileOutputStream(file).use { out ->
            val buf = ByteBuffer.allocate(12).order(ByteOrder.LITTLE_ENDIAN)
            buf.putLong(timestamp)
            buf.putFloat(elapsed)
            out.write(buf.array())
        }

        // Read and Assert
        assertTrue(file.exists())
        assertEquals(12L, file.length())

        val bytes = file.readBytes()
        val readBuf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(timestamp, readBuf.long)
        assertEquals(elapsed, readBuf.float, 1e-6f)
    }

    @Test
    fun testTruncatedFileHandling() {
        val file = tempFolder.newFile("WatchAccelerometerTruncated.bin")
        
        // Write 1.5 samples (36 bytes, which is 24 + 12 bytes)
        FileOutputStream(file).use { out ->
            val buf = ByteBuffer.allocate(36).order(ByteOrder.LITTLE_ENDIAN)
            // First complete sample (24 bytes)
            buf.putLong(1000L)
            buf.putFloat(0.1f)
            buf.putFloat(1.0f)
            buf.putFloat(2.0f)
            buf.putFloat(3.0f)
            // Truncated sample (12 bytes)
            buf.putLong(2000L)
            buf.putFloat(0.2f)
            out.write(buf.array())
        }

        // Parse using ByteBuffer loop matching PhoneSwingDetector
        val list = mutableListOf<Triple<Long, Double, FloatArray>>()
        val bytes = file.readBytes()
        val buffer = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        while (buffer.remaining() >= 24) {
            val t = buffer.long
            val sec = buffer.float.toDouble()
            val x = buffer.float
            val y = buffer.float
            val z = buffer.float
            list.add(Triple(t, sec, floatArrayOf(x, y, z)))
        }

        // Assert only 1 complete sample parsed, and it did not crash on remaining 12 bytes
        assertEquals(1, list.size)
        assertEquals(1000L, list[0].first)
        assertEquals(12, buffer.remaining()) // Remaining is 12 bytes which is less than 24, loop exited cleanly
    }

    @Test
    fun testNaNAndInfinityFloats() {
        val file = tempFolder.newFile("WatchAccelerometerNaN.bin")
        FileOutputStream(file).use { out ->
            val buf = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN)
            buf.putLong(100L)
            buf.putFloat(Float.NaN)
            buf.putFloat(Float.POSITIVE_INFINITY)
            buf.putFloat(Float.NEGATIVE_INFINITY)
            buf.putFloat(0.0f)
            out.write(buf.array())
        }

        val bytes = file.readBytes()
        val readBuf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        readBuf.long
        assertTrue(readBuf.float.isNaN())
        assertEquals(Float.POSITIVE_INFINITY, readBuf.float)
        assertEquals(Float.NEGATIVE_INFINITY, readBuf.float)
        assertEquals(0.0f, readBuf.float, 1e-6f)
    }
}
