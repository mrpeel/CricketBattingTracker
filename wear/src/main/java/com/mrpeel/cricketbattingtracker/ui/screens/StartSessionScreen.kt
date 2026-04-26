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
            .background(TrueBlack),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        item {
            // Header: Battery & Status
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center
            ) {
                Icon(
                    imageVector = Icons.Default.BatteryFull,
                    contentDescription = "Battery",
                    tint = LightBlueSecondary,
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "84%",
                    color = LightBlueSecondary,
                    style = MaterialTheme.typography.body2,
                    fontSize = 12.sp
                )
                Spacer(modifier = Modifier.width(12.dp))
                // Mock GPS indicator
                Box(modifier = Modifier.size(6.dp).background(NeonGreen, RoundedCornerShape(3.dp)))
            }
        }
            
        item { Spacer(modifier = Modifier.height(12.dp)) }
        
        item {
            Text(
                text = "THE PAVILION",
                color = Color.White,
                style = MaterialTheme.typography.title2,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 2.sp
            )
        }
            
        item { Spacer(modifier = Modifier.height(16.dp)) }
        
        item {
            ToggleChip(
                checked = isDebugChecked,
                onCheckedChange = { isDebugChecked = it },
                label = { Text("Save Raw DBG Logs", color = Color.White, fontSize = 11.sp) },
                toggleControl = {
                    Icon(
                        imageVector = ToggleChipDefaults.switchIcon(checked = isDebugChecked),
                        contentDescription = if (isDebugChecked) "On" else "Off",
                        tint = NeonGreen
                    )
                },
                modifier = Modifier.fillMaxWidth(0.9f).height(40.dp)
            )
        }
            
        item { Spacer(modifier = Modifier.height(16.dp)) }
        
        item {
            // Primary Action
            Button(
                onClick = { onStartClick(isDebugChecked) },
                colors = ButtonDefaults.buttonColors(
                    backgroundColor = Color.Transparent,
                    contentColor = NeonGreen
                ),
                modifier = Modifier
                    .fillMaxWidth(0.9f)
                    .height(64.dp)
                    .border(2.dp, NeonGreen, RoundedCornerShape(24.dp)),
                shape = RoundedCornerShape(24.dp)
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
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "START SESSION",
                        style = MaterialTheme.typography.button,
                        fontWeight = FontWeight.ExtraBold
                    )
                }
            }
        }
            
        item { Spacer(modifier = Modifier.height(24.dp)) }
        
        item {
            // Footer
            Text(
                text = "PITCHANALYTIX PRO",
                color = LightBlueSecondary,
                style = MaterialTheme.typography.body2,
                fontSize = 10.sp,
                letterSpacing = 1.sp
            )
        }
    }
}
