package com.mrpeel.cricketbattingtracker.ui.insights

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.mrpeel.cricketbattingtracker.coaching.EarconAudioPlayer
import com.mrpeel.cricketbattingtracker.coaching.FailureFamily
import com.mrpeel.cricketbattingtracker.coaching.LiveShotFault

/**
 * In-Ear Biomechanical Coaching Playbook & Acoustic Guide.
 * Displays the 4 failure families, 10 technical failure modes, earcon synthesis specs,
 * intuitive acoustic design rationales, and motor learning corrective fixes.
 */
@Composable
fun BiomechanicalCoachingPlaybookCard(
    modifier: Modifier = Modifier
) {
    var expandedFamily by remember { mutableStateOf<FailureFamily?>(FailureFamily.FAMILY_A_UPWARD_LOOP) }
    var showTimelineGuide by remember { mutableStateOf(false) }

    // Lazy instantiated earcon audio player for in-app preview
    val earconPlayer = remember { EarconAudioPlayer(isEnabled = true) }
    DisposableEffect(Unit) {
        onDispose { earconPlayer.release() }
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Color(0xFF58FF63).copy(alpha = 0.25f))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        "🎧 IN-EAR COACHING PLAYBOOK",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary,
                        letterSpacing = 1.2.sp
                    )
                    Text(
                        "ACOUSTIC EARCONS & BIOMECHANICAL CUES",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }
            }

            Text(
                "Real-time failure diagnoses, acoustic earcon designs, and 2-syllable motor cues for instant net correction.",
                fontSize = 11.sp,
                color = Color.LightGray,
                lineHeight = 15.sp
            )

            // Timeline & Stage Modes Toggle Button
            Surface(
                onClick = { showTimelineGuide = !showTimelineGuide },
                shape = RoundedCornerShape(10.dp),
                color = Color.White.copy(alpha = 0.05f),
                border = BorderStroke(1.dp, Color.White.copy(alpha = 0.1f)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        if (showTimelineGuide) "⏱️ HIDE AUDIO TIMELINE & STAGES" else "⏱️ VIEW AUDIO TIMELINE & 3 STAGES",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.secondary
                    )
                    Text(if (showTimelineGuide) "▲" else "▼", fontSize = 10.sp, color = Color.Gray)
                }
            }

            AnimatedVisibility(
                visible = showTimelineGuide,
                enter = expandVertically() + fadeIn(),
                exit = shrinkVertically() + fadeOut()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color(0xFF001226))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        "POST-IMPACT AUDIO TIMELINE",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        "• T + 0 to 300 ms: Silence (lets you hear the physical crack of the ball)\n" +
                        "• T + 300 to 520 ms: Acoustic Earcon plays (~200 ms)\n" +
                        "• T + 550 to 1050 ms: 2-syllable TTS cue (1.25x) or Bat Speed plays\n" +
                        "• T + 1100 ms onwards: Mic channel completely open for voice narration",
                        fontSize = 10.sp,
                        color = Color.White,
                        lineHeight = 16.sp
                    )

                    HorizontalDivider(color = Color.White.copy(alpha = 0.08f))

                    Text(
                        "THREE-STAGE COACHING SYSTEM",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.secondary
                    )
                    Text(
                        "1. Stage 1 (Calibration): Earcon + Voice Cue (builds mental link)\n" +
                        "2. Stage 2 (Flow State): Earcon Only on faults (0.2s duration); Chime + Speed on good shots\n" +
                        "3. Stage 3 (Silent Diagnostic): Only plays if you repeat the same fault twice in a row",
                        fontSize = 10.sp,
                        color = Color.LightGray,
                        lineHeight = 16.sp
                    )
                }
            }

            // Failure Families Accordion
            FailureFamily.values().forEach { family ->
                val isExpanded = expandedFamily == family
                val faultsInFamily = LiveShotFault.values().filter { it.family == family }

                Surface(
                    shape = RoundedCornerShape(14.dp),
                    color = if (isExpanded) Color.White.copy(alpha = 0.04f) else Color.White.copy(alpha = 0.02f),
                    border = BorderStroke(
                        1.dp,
                        if (isExpanded) MaterialTheme.colorScheme.primary.copy(alpha = 0.4f) else Color.White.copy(alpha = 0.06f)
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.fillMaxWidth().padding(12.dp)) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    expandedFamily = if (isExpanded) null else family
                                },
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    family.title,
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                                Text(
                                    family.acousticTheme,
                                    fontSize = 10.sp,
                                    color = MaterialTheme.colorScheme.secondary
                                )
                            }
                            Text(
                                if (isExpanded) "▲" else "▼",
                                fontSize = 11.sp,
                                color = Color.Gray,
                                modifier = Modifier.padding(start = 8.dp)
                            )
                        }

                        AnimatedVisibility(
                            visible = isExpanded,
                            enter = expandVertically() + fadeIn(),
                            exit = shrinkVertically() + fadeOut()
                        ) {
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 12.dp),
                                verticalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                faultsInFamily.forEach { fault ->
                                    FaultDetailItem(fault = fault, onPreviewEarcon = { earconPlayer.play(fault) })
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FaultDetailItem(
    fault: LiveShotFault,
    onPreviewEarcon: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(Color(0xFF00162B))
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    fault.shotName,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Text(
                    fault.failureDescription,
                    fontSize = 10.sp,
                    color = Color.Gray
                )
            }

            // Cue badge + Preview Earcon button
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    onClick = onPreviewEarcon,
                    shape = RoundedCornerShape(6.dp),
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f),
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.5f))
                ) {
                    Text(
                        "🔊 TEST",
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 4.dp)
                    )
                }

                Spacer(modifier = Modifier.width(6.dp))

                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = Color(0xFF58FF63),
                    modifier = Modifier.padding(start = 2.dp)
                ) {
                    Text(
                        "\"${fault.cue}\"",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFF000C1B),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }
        }

        HorizontalDivider(color = Color.White.copy(alpha = 0.05f))

        Text(
            text = "🎵 Acoustic Synth: ${fault.acousticDesign}",
            fontSize = 9.5.sp,
            color = MaterialTheme.colorScheme.secondary,
            lineHeight = 13.sp
        )

        Text(
            text = "🧠 Brain Intuition: ${fault.acousticIntuition}",
            fontSize = 9.5.sp,
            color = Color.LightGray,
            lineHeight = 13.sp
        )

        Surface(
            shape = RoundedCornerShape(8.dp),
            color = Color.White.copy(alpha = 0.04f),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.08f)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(8.dp),
                verticalArrangement = Arrangement.spacedBy(3.dp)
            ) {
                Text(
                    text = "🛠️ COACHING NOTE & BIOMECHANICAL FIX",
                    fontSize = 9.sp,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.primary,
                    letterSpacing = 0.8.sp
                )
                Text(
                    text = fault.biomechanicalFix,
                    fontSize = 10.sp,
                    color = Color.White,
                    lineHeight = 14.5.sp
                )
            }
        }
    }
}
