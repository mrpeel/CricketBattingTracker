package com.mrpeel.cricketbattingtracker.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import com.mrpeel.cricketbattingtracker.ui.theme.*

@Composable
fun StartSessionScreen(
    onStartClick: (Boolean) -> Unit
) {
    var isDebugChecked by remember { mutableStateOf(false) }
    ScalingLazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF000C1B)), // Deep navy from brand
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        item {
            // Header: Battery & Status
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center,
                modifier = Modifier.padding(top = 20.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.BatteryFull,
                    contentDescription = "Battery",
                    tint = Color(0xFFBCD2FE),
                    modifier = Modifier.size(14.dp)
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
        }
            
        item { Spacer(modifier = Modifier.height(8.dp)) }
        
        item {
            Text(
                text = "PITCH ANALYTIX",
                color = Color.White,
                style = MaterialTheme.typography.title2,
                fontSize = 16.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = 2.sp
            )
        }
            
        item { Spacer(modifier = Modifier.height(16.dp)) }
        
        item {
            Chip(
                onClick = { isDebugChecked = !isDebugChecked },
                label = { Text("DIAGNOSTICS", color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.Bold) },
                icon = {
                    Icon(
                        imageVector = ToggleChipDefaults.switchIcon(checked = isDebugChecked),
                        contentDescription = null,
                        tint = if (isDebugChecked) Color(0xFF58FF63) else Color.Gray,
                        modifier = Modifier.size(16.dp)
                    )
                },
                colors = ChipDefaults.chipColors(
                    backgroundColor = Color.White.copy(alpha = 0.05f)
                ),
                modifier = Modifier.fillMaxWidth(0.85f).height(42.dp)
            )
        }
            
        item { Spacer(modifier = Modifier.height(12.dp)) }
        
        item {
            // Primary Action
            Button(
                onClick = { onStartClick(isDebugChecked) },
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = Color(0xFF58FF63),
                    contentColor = Color(0xFF000C1B)
                ),
                modifier = Modifier
                    .fillMaxWidth(0.9f)
                    .height(64.dp),
                shape = RoundedCornerShape(32.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.SportsCricket,
                        contentDescription = "Start",
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "GO PRO",
                        style = MaterialTheme.typography.button,
                        fontWeight = FontWeight.Black,
                        fontSize = 18.sp
                    )
                }
            }
        }
            
        item { Spacer(modifier = Modifier.height(20.dp)) }
    }
}
