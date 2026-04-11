package com.mrpeel.cricketbattingtracker

import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class MainActivityTest {

    @get:Rule
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun app_launchesWithoutCrashing_andDisplaysStartButton() {
        // If the custom font fails to parse or the UI thread crashes, 
        // this test will immediately fail during initialization.
        
        // Assert that the UI successfully inflated and drew the "START SESSION" button to the screen.
        composeTestRule.onNodeWithText("START SESSION").assertExists()
    }
}
