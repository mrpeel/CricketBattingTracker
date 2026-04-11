package com.mrpeel.cricketbattingtracker.ui.theme

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.wear.compose.material.Colors
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Typography
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.sp

// Design System Tokens
val TrueBlack = Color(0xFF000000)
val NeonGreen = Color(0xFF58FF63)
val LightBlueSecondary = Color(0xFFBCD2FE)
val NavyAccent = Color(0xFF001B3D)
val DarkGray = Color(0xFF222222)

val SpaceGrotesk = FontFamily.SansSerif

val PavilionTypography = Typography(
    title1 = androidx.compose.ui.text.TextStyle(
        fontFamily = SpaceGrotesk,
        fontWeight = FontWeight.Bold,
        fontSize = 24.sp
    ),
    title2 = androidx.compose.ui.text.TextStyle(
        fontFamily = SpaceGrotesk,
        fontWeight = FontWeight.Bold,
        fontSize = 20.sp
    ),
    body1 = androidx.compose.ui.text.TextStyle(
        fontFamily = SpaceGrotesk,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp
    ),
    body2 = androidx.compose.ui.text.TextStyle(
        fontFamily = SpaceGrotesk,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp
    ),
    button = androidx.compose.ui.text.TextStyle(
        fontFamily = SpaceGrotesk,
        fontWeight = FontWeight.Bold,
        fontSize = 15.sp,
        letterSpacing = 1.sp
    )
)

private val PavilionColorPalette = Colors(
    primary = NeonGreen,
    primaryVariant = NeonGreen,
    secondary = LightBlueSecondary,
    secondaryVariant = LightBlueSecondary,
    background = TrueBlack,
    surface = DarkGray,
    error = Color.Red,
    onPrimary = TrueBlack,
    onSecondary = TrueBlack,
    onBackground = Color.White,
    onSurface = Color.White,
    onError = Color.Black
)

@Composable
fun PavilionTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colors = PavilionColorPalette,
        typography = PavilionTypography,
        content = content
    )
}
