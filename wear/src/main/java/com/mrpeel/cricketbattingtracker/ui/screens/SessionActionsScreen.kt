package com.mrpeel.cricketbattingtracker.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.material.*

@Composable
fun SessionActionsScreen(
    onSyncClick: () -> Unit,
    onDiscardClick: () -> Unit
) {
    // Cohesive Theme Colors
    val neonGreen = Color(0xFF58FF63)
    val iceBlue = Color(0xFFBCD2FE)
    val navySurface = Color(0xFF001B3D)
    val crimsonRed = Color(0xFFFF5252)

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .padding(16.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                text = "SESSION ACTIONS",
                color = iceBlue.copy(alpha = 0.7f),
                fontSize = 11.sp,
                fontWeight = FontWeight.ExtraBold,
                letterSpacing = 1.sp
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Main Large SYNC Button
            Button(
                onClick = onSyncClick,
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = neonGreen,
                    contentColor = Color.Black
                ),
                modifier = Modifier
                    .fillMaxWidth(0.9f)
                    .height(44.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text(
                    text = "SYNC & SAVE",
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Black
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Smaller DISCARD Button
            Button(
                onClick = onDiscardClick,
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = navySurface,
                    contentColor = crimsonRed
                ),
                modifier = Modifier
                    .fillMaxWidth(0.7f)
                    .height(36.dp),
                shape = RoundedCornerShape(10.dp)
            ) {
                Text(
                    text = "DISCARD",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}
