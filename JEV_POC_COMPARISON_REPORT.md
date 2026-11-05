# Jev (`jev-1.13`) System One Stage 3 Decision Model Evaluation Report

**Generated**: 2026-11-03 UTC  
**Initial POC Cohort**: **211 physical shots** (`session_2026-07-20_12-42-16`, `07-21_12-43-37`, `07-24_12-52-29`, `07-25_15-16-32` + 39-shot Sept 2026 `BAT_HANDLE` AHRS subset — comprising 8 training-split sessions and 1 validation session from [`dataset_splits.json`](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/dataset_splits.json))  
**Authoritative Holdout Verification**: **656 detected shots across the 12-session Holdout Test Set** (`HOLDOUT_TEST_SESSIONS`) and **4,637 detected shots across the 89-session Clean Benchmark**  
**Evaluated Models**:
- **Column A**: Raw Stage 2 TCN (`BatPlaneGeometryThreeFamilyTCN`, Argmax + Dual-Path Sweep Gate)
- **Column B**: Legacy Stage 3 Heuristic Gates (`telemetry_engine.py` Gate 2.5 / Non-Bat Sweep→Glance + Bat AHRS rules)
- **Column C**: Stage 3 Jev (`jev-1.13`) Choice Arbitration via OpenCode System One
- **Column D**: Confidence-Gated Hybrid (Jev invoked when Macro Gate Margin < 0.35 or Subhead Conflict)

---

## 1. Overall Accuracy & Macro-F1 Comparison (211-Shot Initial POC Cohort)

| Pipeline Method | Total Shots | Correct Shots | Overall Accuracy (%) | Macro-F1 (%) |
|---|:---:|:---:|:---:|:---:|
| **Column A: Raw Stage 2 TCN (Argmax)** | 211 | 179 | 🏆 **84.8%** | 🏆 **84.1%** |
| **Column B: Legacy Heuristic Gates (Gate 2.5)** | 211 | 178 | **84.4%** | **83.7%** |
| **Column C: Stage 3 Jev (`jev-1.13`) Choice** | 211 | 132 | **62.6%** | **60.2%** |
| **Column D: Confidence-Gated Hybrid** | 211 | 162 | **76.8%** | **77.8%** |

---

## 2. Per-Class Accuracy Breakdown Table (211-Shot Initial POC Cohort)

| Shot Class | Ground Truth Shots | Raw TCN (Col A) | Legacy Heuristics (Col B) | Jev Choice (Col C) | Confidence Hybrid (Col D) |
|---|:---:|:---:|:---:|:---:|:---:|
| **PULL/HOOK/SLOG** | 55 | 76.4% | 76.4% | **78.2%** | **78.2%** |
| **DRIVE/DEFENCE** | 40 | **85.0%** | **85.0%** | 45.0% | 72.5% |
| **GLANCE/FLICK** | 30 | 83.3% | **86.7%** | 40.0% | 46.7% |
| **CUT/PUNCH** | 16 | 62.5% | 62.5% | **87.5%** | 81.2% |
| **DEFLECTION/GUIDE** | 23 | **91.3%** | **91.3%** | 26.1% | **91.3%** |
| **POWER DRIVE** | 20 | **100.0%** | **100.0%** | 60.0% | 75.0% |
| **SWEEP** | 27 | **100.0%** | 92.6% | **100.0%** | **100.0%** |

---

## 3. Edge-Case Deep Dive Table (15 Most Informative Disagreements)

| Shot ID | Ground Truth | TCN Pred (A) | Heuristic Pred (B) | Jev Pred (C) + Conf | Jev Hand Score vs UI Score | Fault Takeover Prob |
|---|---|---|---|---|:---:|:---:|
| `12-42-16_1` | **SWEEP** | SWEEP | GLANCE/FLICK | **SWEEP** (0.88) | `25` vs `30` | `20%` |
| `12-42-16_2` | **SWEEP** | SWEEP | GLANCE/FLICK | **SWEEP** (0.91) | `15` vs `30` | `11%` |
| `12-42-16_3` | **GLANCE/FLICK** | SWEEP | GLANCE/FLICK | **SWEEP** (0.72) | `13` vs `30` | `15%` |
| `15-16-32_2` | **PULL/HOOK/SLOG** | POWER DRIVE | POWER DRIVE | **PULL/HOOK/SLOG** (0.66) | `64` vs `25` | `6%` |
| `15-16-32_20` | **PULL/HOOK/SLOG** | POWER DRIVE | POWER DRIVE | **PULL/HOOK/SLOG** (0.68) | `24` vs `25` | `4%` |
| `15-16-32_23` | **PULL/HOOK/SLOG** | POWER DRIVE | POWER DRIVE | **PULL/HOOK/SLOG** (0.44) | `45` vs `50` | `5%` |
| `15-16-32_34` | **PULL/HOOK/SLOG** | POWER DRIVE | POWER DRIVE | **PULL/HOOK/SLOG** (0.81) | `42` vs `50` | `5%` |
| `15-16-32_38` | **PULL/HOOK/SLOG** | POWER DRIVE | POWER DRIVE | **PULL/HOOK/SLOG** (0.67) | `24` vs `25` | `5%` |
| `12-14-46_22` | **PULL/HOOK/SLOG** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.50) | `16` vs `90` | `10%` |
| `12-14-46_31` | **PULL/HOOK/SLOG** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.56) | `40` vs `90` | `12%` |
| `12-14-46_33` | **PULL/HOOK/SLOG** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.56) | `22` vs `90` | `11%` |
| `12-42-16_30` | **GLANCE/FLICK** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.81) | `37` vs `30` | `4%` |
| `12-43-37_1` | **GLANCE/FLICK** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.70) | `44` vs `55` | `3%` |
| `12-43-37_3` | **GLANCE/FLICK** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.25) | `45` vs `55` | `3%` |
| `12-43-37_15` | **GLANCE/FLICK** | GLANCE/FLICK | GLANCE/FLICK | **PULL/HOOK/SLOG** (0.63) | `48` vs `30` | `3%` |

---

## 4. Latency & Token Cost Summary

- **Endpoint**: `https://opencode.ai/inference/systemone/v1/systemone`
- **Active Model Resolution**: Defaulted to `jev-1.13-free` with automatic fallback to `jev-1.13` ($0.042/1M input tokens)
- **Average Network Latency**: `1,172.1 ms` per shot without connection pooling; **`435.2 ms` median (`418.6 ms` compact 1-question schema)** with persistent `requests.Session()` connection pooling
- **Per-Shot Input Tokens**: `1,669` tokens (4-question schema) / `1,168` tokens (1-question schema)
- **Per-Shot Output Tokens**: `152` tokens
- **Cached Evaluations**: `211 / 211` shots stored in [`jev_poc_cache.jsonl`](file:///Users/neilkloot/Code/CricketBattingTracker/jev_poc_cache.jsonl)

---

## 5. Architectural Findings & Decision Recommendation

1. **Raw Stage 2 TCN Outperforms Broad Cloud Arbitration**:
   Across the 211-shot cohort, **Raw Stage 2 TCN (84.8%)** outperforms both standalone Jev (**62.6%**) and the broad Confidence-Gated Hybrid (**76.8%**), because wrist-mounted IMU kinematics without 3D bat AHRS cannot be disambiguated purely from scalar summary prompts on `GLANCE/FLICK`, `DEFLECTION/GUIDE`, and `POWER DRIVE`.
2. **Discovery of a High-Impact Stage 3 Heuristic Regression**:
   Jev's agreement with Raw TCN on `12-42-16_1` and `12-42-16_2` exposed a systemic flaw in `non_bat_sweep_to_glance` (`telemetry_engine.py` lines 818–824). On genuine `SWEEP` shots, the inactive vertical-bat subhead (`head_sub0`) places conditional probability on `GLANCE/FLICK` (`p_sub0_glance >= 0.55`), causing the heuristic to corrupt **17 genuine Sweep shots (net -13 shots across the 89-session Clean Benchmark, and net -3 shots on the 12-session Holdout Test Set)**.
3. **Role of Jev Going Forward — Training-Pipeline Shadow Auditor**:
   Rather than calling Jev at runtime on the phone, Jev is integrated into the offline training and evaluation pipeline ([`pipelines/jev_auditor.py`](file:///Users/neilkloot/Code/CricketBattingTracker/pipelines/jev_auditor.py)) to audit Stage 3 rule health and surface newly emerging failure regimes whenever the scorecard is evaluated.
