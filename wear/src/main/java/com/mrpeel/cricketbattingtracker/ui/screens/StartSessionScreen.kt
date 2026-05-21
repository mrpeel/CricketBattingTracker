package com.mrpeel.cricketbattingtracker.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SportsCricket
import androidx.compose.material.icons.filled.BatteryFull
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.material.*
import com.mrpeel.cricketbattingtracker.ui.theme.*

@Composable
fun StartSessionScreen(
    onStartClick: (Boolean) -> Unit
) {
    var isDebugChecked by remember { mutableStateOf(false) }
    
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF000C1B)), // Deep navy from brand
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .fillMaxHeight()
                .padding(horizontal = 8.dp)
        ) {
            // Header: Battery & Status
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Icon(
                    imageVector = Icons.Default.BatteryFull,
                    contentDescription = "Battery",
                    tint = Color(0xFFBCD2FE),
                    modifier = Modifier.size(12.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "READY",
                    color = Color(0xFF58FF63),
                    style = MaterialTheme.typography.body2,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Black
                )
            }
                
            Spacer(modifier = Modifier.height(4.dp))
            
            Text(
                text = "PITCH ANALYTIX",
                color = Color.White,
                style = MaterialTheme.typography.title2,
                fontSize = 15.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = 1.5.sp
            )
                
            Spacer(modifier = Modifier.height(10.dp))
            
            Chip(
                onClick = { isDebugChecked = !isDebugChecked },
                label = { Text("DIAGNOSTICS", color = Color.White, fontSize = 8.sp, fontWeight = FontWeight.Bold) },
                icon = {
                    Icon(
                        imageVector = ToggleChipDefaults.switchIcon(checked = isDebugChecked),
                        contentDescription = null,
                        tint = if (isDebugChecked) Color(0xFF58FF63) else Color.Gray,
                        modifier = Modifier.size(14.dp)
                    )
                },
                colors = ChipDefaults.chipColors(
                    backgroundColor = Color.White.copy(alpha = 0.05f)
                ),
                modifier = Modifier.fillMaxWidth(0.85f).height(38.dp)
            )
                
            Spacer(modifier = Modifier.height(8.dp))
            
            // Primary Action
            Button(
                onClick = { onStartClick(isDebugChecked) },
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = Color(0xFF58FF63),
                    contentColor = Color(0xFF000C1B)
                ),
                modifier = Modifier
                    .fillMaxWidth(0.9f)
                    .height(48.dp),
                shape = RoundedCornerShape(24.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.SportsCricket,
                        contentDescription = "Start",
                        modifier = Modifier.size(20.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "START SESSION",
                        style = MaterialTheme.typography.button,
                        fontWeight = FontWeight.Black,
                        fontSize = 12.sp
                    )
                }
            }
        }
    }
}
