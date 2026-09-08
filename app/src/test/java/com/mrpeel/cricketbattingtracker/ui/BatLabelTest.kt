package com.mrpeel.cricketbattingtracker.ui

import com.mrpeel.cricketbattingtracker.data.InningsEvent
import com.mrpeel.cricketbattingtracker.formatBatLabel
import com.mrpeel.cricketbattingtracker.getBatLabel
import com.mrpeel.cricketbattingtracker.services.BatProfile
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BatLabelTest {

    private val testProfiles = listOf(
        BatProfile(1, "Game bat", 1425.0f),
        BatProfile(2, "Gray Nicholls Giant", 1625.0f),
        BatProfile(3, "Eye in bat", 1200.0f)
    )

    @Test
    fun testExplicitNameAndWeight() {
        val label = formatBatLabel(
            batName = "Gray Nicholls Giant",
            batWeightGrams = 1625.0f,
            batId = 2,
            fallbackProfiles = testProfiles
        )
        assertEquals("Gray Nicholls Giant (1625g)", label)
    }

    @Test
    fun testEyeInBatExplicit() {
        val label = formatBatLabel(
            batName = "Eye in bat",
            batWeightGrams = 1200.0f,
            batId = 3,
            fallbackProfiles = testProfiles
        )
        assertEquals("Eye in bat (1200g)", label)
    }

    @Test
    fun testGameBatExplicit() {
        val label = formatBatLabel(
            batName = "Game bat",
            batWeightGrams = 1425.0f,
            batId = 1,
            fallbackProfiles = testProfiles
        )
        assertEquals("Game bat (1425g)", label)
    }

    @Test
    fun testHistoricalRecordWithNullNameAndWeightResolvesProfile() {
        val label = formatBatLabel(
            batName = null,
            batWeightGrams = null,
            batId = 2,
            fallbackProfiles = testProfiles
        )
        assertEquals("Gray Nicholls Giant (1625g)", label)
    }

    @Test
    fun testBlankNameResolvesFallbackProfile() {
        val label = formatBatLabel(
            batName = "   ",
            batWeightGrams = null,
            batId = 1,
            fallbackProfiles = testProfiles
        )
        assertEquals("Game bat (1425g)", label)
    }

    @Test
    fun testNameOnlyWithoutWeight() {
        val label = formatBatLabel(
            batName = "Custom Willow",
            batWeightGrams = null,
            batId = null,
            fallbackProfiles = testProfiles
        )
        assertEquals("Custom Willow", label)
    }

    @Test
    fun testNameWithZeroWeightOmitsWeight() {
        val label = formatBatLabel(
            batName = "Kookaburra Ghost",
            batWeightGrams = 0f,
            batId = null,
            fallbackProfiles = testProfiles
        )
        assertEquals("Kookaburra Ghost", label)
    }

    @Test
    fun testUnknownBatIdWithoutNameFallsBackToBatId() {
        val label = formatBatLabel(
            batName = null,
            batWeightGrams = null,
            batId = 99,
            fallbackProfiles = testProfiles
        )
        assertEquals("Bat 99", label)
    }

    @Test
    fun testAllNullReturnsNullNoBadge() {
        val label = formatBatLabel(
            batName = null,
            batWeightGrams = null,
            batId = null,
            fallbackProfiles = testProfiles
        )
        assertNull(label)
    }

    @Test
    fun testInningsEventExtensionFunction() {
        val event = InningsEvent(
            id = 1,
            inningsId = 100L,
            timestamp = 1000L,
            description = "Shot: Pull",
            bat_name = "Gray Nicholls Giant",
            bat_weight_grams = 1625.0f,
            bat_id = 2
        )
        assertEquals("Gray Nicholls Giant (1625g)", event.getBatLabel(testProfiles))
    }

    @Test
    fun testHistoricalInningsEventExtensionFunction() {
        val event = InningsEvent(
            id = 2,
            inningsId = 100L,
            timestamp = 2000L,
            description = "Shot: Slog",
            bat_name = null,
            bat_weight_grams = null,
            bat_id = 3
        )
        assertEquals("Eye in bat (1200g)", event.getBatLabel(testProfiles))
    }
}
