# Cross-Device State-Gated AHRS Evaluation Report

**Generated**: 2026-09-10 14:49:28  
**Evaluated Sessions**: 5 bat-mount sessions  
**Total GT Physical Shots**: 185 shots  
**Authoritative Cohort Size**: 39 shots  
**Plausibility Pass Rate**: 84.6% (33/39)  

## 1. Evaluation Scorecard

| Shot ID | Ground Truth Class | Watch Yaw Seed (°) | Impact Bat Pitch (°) | Impact Face Roll (°) | Plausibility |
|---|---|---|---|---|---|
| `16-26-41_5` | **Cover drive** | `+6.9°` | `28.6°` | `+28.8°` | ✅ PASS |
| `16-26-41_11` | **Straight drive** | `+42.4°` | `49.7°` | `-12.8°` | ✅ PASS |
| `16-26-41_14` | **Cover drive** | `+7.5°` | `22.5°` | `-58.4°` | ❌ FAIL |
| `16-26-41_19` | **Cover drive** | `+24.7°` | `44.6°` | `+9.3°` | ✅ PASS |
| `16-26-41_20` | **Back foot defense** | `+15.4°` | `7.9°` | `-9.8°` | ❌ FAIL |
| `16-26-41_22` | **Cover drive** | `+14.3°` | `44.5°` | `+39.1°` | ✅ PASS |
| `16-26-41_26` | **Back foot punch** | `+8.7°` | `26.0°` | `+1.3°` | ✅ PASS |
| `16-26-41_31` | **On drive** | `+16.4°` | `34.7°` | `+85.1°` | ✅ PASS |
| `16-26-41_34` | **Cover drive** | `+17.6°` | `36.6°` | `+68.2°` | ✅ PASS |
| `16-26-41_38` | **Back foot punch** | `+22.7°` | `17.1°` | `+40.1°` | ❌ FAIL |
| `16-26-41_39` | **Back foot punch** | `+44.1°` | `37.2°` | `+22.0°` | ✅ PASS |
| `11-41-57_3` | **Forward defense** | `-24.3°` | `39.6°` | `-0.0°` | ✅ PASS |
| `11-41-57_4` | **Back foot defense** | `-33.2°` | `40.6°` | `-0.0°` | ✅ PASS |
| `11-41-57_6` | **Forward defense** | `-22.7°` | `46.1°` | `-0.0°` | ✅ PASS |
| `16-26-41_2` | **Pull shot** | `+12.9°` | `7.4°` | `+124.6°` | ✅ PASS |
| `16-26-41_3` | **Pull shot** | `+1.9°` | `26.0°` | `+141.8°` | ✅ PASS |
| `16-26-41_9` | **Pull shot** | `+8.3°` | `23.1°` | `+135.0°` | ✅ PASS |
| `16-26-41_21` | **Pull shot** | `+15.3°` | `32.0°` | `+132.3°` | ✅ PASS |
| `16-26-41_33` | **Pull shot** | `+14.1°` | `20.4°` | `+156.2°` | ✅ PASS |
| `16-26-41_37` | **Pull shot** | `+25.6°` | `27.5°` | `+128.0°` | ✅ PASS |
| `16-26-41_41` | **Pull shot** | `+47.3°` | `28.7°` | `+156.4°` | ✅ PASS |
| `11-41-57_10` | **Pull shot** | `-22.7°` | `48.4°` | `-2.0°` | ❌ FAIL |
| `12-14-46_22` | **Pull shot** | `-155.1°` | `9.1°` | `+1.6°` | ✅ PASS |
| `12-14-46_29` | **Pull shot** | `-147.5°` | `9.0°` | `-0.0°` | ✅ PASS |
| `12-14-46_31` | **Pull shot** | `-125.7°` | `8.6°` | `+11.6°` | ✅ PASS |
| `12-14-46_33` | **Pull shot** | `-141.1°` | `3.1°` | `-0.0°` | ✅ PASS |
| `12-14-46_40` | **Pull shot** | `-124.4°` | `10.3°` | `-7.8°` | ✅ PASS |
| `12-14-46_41` | **Pull shot** | `-88.1°` | `16.0°` | `+0.9°` | ✅ PASS |
| `16-26-41_8` | **Cut shot** | `+6.7°` | `33.5°` | `+20.1°` | ✅ PASS |
| `16-26-41_12` | **Cut shot** | `+3.3°` | `2.7°` | `-20.6°` | ❌ FAIL |
| `16-26-41_24` | **Cut shot** | `+13.9°` | `4.2°` | `-30.5°` | ❌ FAIL |
| `12-14-46_4` | **Cut shot** | `-173.9°` | `31.5°` | `-0.4°` | ✅ PASS |
| `12-14-46_8` | **Cut shot** | `-160.8°` | `30.5°` | `-0.0°` | ✅ PASS |
| `12-35-47_38` | **Cut shot** | `+178.3°` | `31.3°` | `-55.8°` | ✅ PASS |
| `12-35-47_44` | **Cut shot** | `-178.4°` | `34.7°` | `-74.0°` | ✅ PASS |
| `16-26-41_10` | **Guide** | `-124.0°` | `72.1°` | `+1.8°` | ✅ PASS |
| `16-26-41_15` | **Guide** | `+6.9°` | `20.6°` | `-28.7°` | ✅ PASS |
| `16-26-41_17` | **Flick shot** | `+10.7°` | `34.1°` | `+96.3°` | ✅ PASS |
| `16-26-41_18` | **Glance** | `+17.9°` | `53.2°` | `+105.2°` | ✅ PASS |

## 2. Drift & Failure Audit

| Shot ID | GT Class | Static Acc (m/s²) | Gravity Dev | Max Flip Jump | Stillness Status | Audit Verdict |
|---|---|---|---|---|---|---|
| `16-26-41_5` | Cover drive | `10.11` | `+0.30` (OK) | `2.8°` | OK | **PASS** |
| `16-26-41_11` | Straight drive | `9.81` | `+0.00` (OK) | `0.2°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_14` | Cover drive | `9.77` | `+0.04` (OK) | `2.6°` | OK | **PASS** |
| `16-26-41_19` | Cover drive | `9.75` | `+0.06` (OK) | `1.9°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_20` | Back foot defense | `9.82` | `+0.02` (OK) | `1.4°` | OK | **PASS** |
| `16-26-41_22` | Cover drive | `9.75` | `+0.06` (OK) | `2.8°` | OK | **PASS** |
| `16-26-41_26` | Back foot punch | `9.73` | `+0.07` (OK) | `2.7°` | OK | **PASS** |
| `16-26-41_31` | On drive | `9.74` | `+0.07` (OK) | `1.9°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_34` | Cover drive | `9.51` | `+0.30` (OK) | `2.3°` | OK | **PASS** |
| `16-26-41_38` | Back foot punch | `10.25` | `+0.44` (OK) | `2.9°` | OK | **PASS** |
| `16-26-41_39` | Back foot punch | `9.91` | `+0.11` (OK) | `3.1°` | OK | **PASS** |
| `11-41-57_3` | Forward defense | `9.90` | `+0.09` (OK) | `0.0°` | OK | **PASS** |
| `11-41-57_4` | Back foot defense | `10.18` | `+0.38` (OK) | `0.0°` | OK | **PASS** |
| `11-41-57_6` | Forward defense | `9.80` | `+0.01` (OK) | `0.0°` | OK | **PASS** |
| `16-26-41_2` | Pull shot | `10.08` | `+0.27` (OK) | `4.1°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_3` | Pull shot | `9.64` | `+0.16` (OK) | `4.1°` | OK | **PASS** |
| `16-26-41_9` | Pull shot | `9.77` | `+0.04` (OK) | `4.0°` | OK | **PASS** |
| `16-26-41_21` | Pull shot | `9.68` | `+0.13` (OK) | `3.7°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_33` | Pull shot | `9.79` | `+0.02` (OK) | `3.3°` | OK | **PASS** |
| `16-26-41_37` | Pull shot | `9.71` | `+0.10` (OK) | `3.8°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_41` | Pull shot | `9.82` | `+0.01` (OK) | `3.3°` | FLAG (>0.8 rad/s) | **PASS** |
| `11-41-57_10` | Pull shot | `9.81` | `+0.00` (OK) | `0.2°` | OK | **PASS** |
| `12-14-46_22` | Pull shot | `9.83` | `+0.02` (OK) | `0.4°` | OK | **PASS** |
| `12-14-46_29` | Pull shot | `9.85` | `+0.04` (OK) | `0.0°` | OK | **PASS** |
| `12-14-46_31` | Pull shot | `8.78` | `+1.03` (OK) | `0.1°` | FLAG (>0.8 rad/s) | **PASS** |
| `12-14-46_33` | Pull shot | `10.04` | `+0.24` (OK) | `0.0°` | OK | **PASS** |
| `12-14-46_40` | Pull shot | `9.95` | `+0.14` (OK) | `0.2°` | OK | **PASS** |
| `12-14-46_41` | Pull shot | `9.64` | `+0.17` (OK) | `0.3°` | OK | **PASS** |
| `16-26-41_8` | Cut shot | `9.94` | `+0.13` (OK) | `2.7°` | OK | **PASS** |
| `16-26-41_12` | Cut shot | `10.04` | `+0.24` (OK) | `3.1°` | OK | **PASS** |
| `16-26-41_24` | Cut shot | `9.63` | `+0.17` (OK) | `2.8°` | OK | **PASS** |
| `12-14-46_4` | Cut shot | `10.01` | `+0.20` (OK) | `0.2°` | OK | **PASS** |
| `12-14-46_8` | Cut shot | `9.98` | `+0.17` (OK) | `0.0°` | OK | **PASS** |
| `12-35-47_38` | Cut shot | `9.94` | `+0.13` (OK) | `1.8°` | OK | **PASS** |
| `12-35-47_44` | Cut shot | `10.14` | `+0.34` (OK) | `1.8°` | OK | **PASS** |
| `16-26-41_10` | Guide | `10.77` | `+0.96` (OK) | `0.3°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_15` | Guide | `9.99` | `+0.19` (OK) | `2.1°` | FLAG (>0.8 rad/s) | **PASS** |
| `16-26-41_17` | Flick shot | `9.52` | `+0.29` (OK) | `1.0°` | OK | **PASS** |
| `16-26-41_18` | Glance | `9.91` | `+0.10` (OK) | `0.8°` | FLAG (>0.8 rad/s) | **PASS** |

## 3. Biomechanical Family Kinematic Summary

| Shot Family | Target Pitch (°) | Target Roll Behavior | Mean Observed Pitch (°) | Mean Observed Roll (°) | Plausibility |
|---|---|---|---|---|---|
| **Vertical Bat** | 25° – 90° | Controlled / Square | `34.0°` | `+15.2°` | **78.6%** (11/14) |
| **Cross-Bat** | 0° – 38° | High Pronation | `19.3°` | `+69.9°` | **92.9%** (13/14) |
| **Lateral Punch** | 8° – 45° | Square / Guiding | `24.1°` | `-23.0°` | **71.4%** (5/7) |

## 4. Visual Verification Artifact

A publication-grade 3-trace visualization comparing a Straight Drive to a Pull Shot has been saved to:
- `docs/figures/bat_orientation_drive_vs_pull.png`
