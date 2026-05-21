package com.mrpeel.cricketbattingtracker.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.material.*

@Composable
fun DiscardConfirmationScreen(
    onYesClick: () -> Unit,
    onNoClick: () -> Unit
) {
    val crimsonRed = Color(0xFFFF5252)
    val iceBlue = Color(0xFFBCD2FE)
    val navySurface = Color(0xFF001B3D)

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
                text = "Discard this\nsession?",
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Black,
                textAlign = TextAlign.Center,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(18.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterHorizontally)
            ) {
                // NO Button (Keep session, go back to main screen)
                Button(
                    onClick = onNoClick,
                    colors = ButtonDefaults.buttonColors(
                        backgroundColor = navySurface,
                        contentColor = iceBlue
                    ),
                    modifier = Modifier
                        .width(60.dp)
                        .height(36.dp),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text(
                        text = "NO",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                // YES Button (Discard session, wipe data)
                Button(
                    onClick = onYesClick,
                    colors = ButtonDefaults.buttonColors(
                        backgroundColor = crimsonRed,
                        contentColor = Color.Black
                    ),
                    modifier = Modifier
                        .width(60.dp)
                        .height(36.dp),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text(
                        text = "YES",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Black
                    )
                }
            }
        }
    }
}
