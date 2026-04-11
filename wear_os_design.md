web application/stitch/projects/5364758526892918808/screens/b0decd98a8c748938d07dbe5c3fc7551
# Wear OS Design Specification: PitchAnalytix Pro

## 1. Visual Language & Foundation
**Creative North Star:** "The Digital Pavilion"
**Theme:** High-contrast, dark mode optimized for OLED efficiency and glanceability during high-intensity sports activity.

### Design System Tokens (PitchAnalytix Pro)
- **Background:** `#000000` (True Black for OLED) / `#001B3D` (Deep Navy accents)
- **Primary Color:** `#58FF63` (Neon Green - Action/Status)
- **Secondary Color:** `#BCD2FE` (Light Blue - Secondary Metrics)
- **Typography:** `Space Grotesk` (Modern, geometric, highly legible)
- **Roundness:** `Round Four` (Circular/Organic for watch face compatibility)

---

## 2. Screen Specifications

### A. Start Session Screen ({{DATA:SCREEN:SCREEN_2}})
**Goal:** Initiate tracking with minimal interaction.

*   **Layout:** Centered, circular-focused.
*   **Header:**
    *   Battery Icon + Percentage (Secondary Metrics color).
    *   GPS/Fixed Status Indicator.
    *   App Title: "THE PAVILION" (Uppercase, tracking-widest).
*   **Primary Action:**
    *   Large, rounded square button in the center.
    *   Color: Neon Green (`#58FF63`).
    *   Icon: Cricket Bat & Ball.
    *   Text: "START SESSION" (Bold, Uppercase).
*   **Footer:**
    *   Last Session Metric: e.g., "LAST: 142.5 SR".
    *   Brand Attribution: "PITCHANALYTIX PRO".

### B. Session Summary Screen ({{DATA:SCREEN:SCREEN_6}})
**Goal:** Provide immediate performance feedback post-activity.

*   **Layout:** Centered metrics with a primary action at the bottom.
*   **Header:**
    *   Status Text: "SESSION COMPLETE" (Subtle blue-gray).
*   **Metric Visualization:**
    *   Circular progress/indicator bar showing Avg Speed.
    *   Metric Label: "AVG SPEED" (Neon Green).
    *   Large Value: "84 MPH" (Space Grotesk, Bold).
*   **Secondary Metric Grid:**
    *   Horizontal split for "MAX SPEED" and "SHOTS" (not fully shown in screenshot but implied for the data model).
*   **Primary Action:**
    *   Button: "SYNC SESSION" (Neon Green).
    *   Icon: Sync/Refresh.
*   **Footer:**
    *   Small brand text: "THE PAVILION".

---

## 3. Interaction & Animation Logic
- **Haptics:** Short buzz on "Start", double buzz on successful "Sync".
- **Gestures:** Horizontal swipe to move between tracking views (Active vs. Heart Rate).
- **AOD (Always On Display):** Reduce brightness, remove background navy gradients, keep neon green metrics outlined or dimmed to 50% opacity.

## 4. Components Reference
- **TopAppBar (Wear):** Small, center-aligned, metadata focus.
- **ActionButton (Large):** High-contrast background, centered icon+label.
- **MetricRing:** Dynamic SVG/Canvas drawing based on session performance vs. personal averages.