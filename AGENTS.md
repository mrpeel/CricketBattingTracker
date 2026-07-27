# Pitch Analytix Pro — Agent System Configuration & Entrypoint

Welcome to the Pitch Analytix Pro (Cricket Batting Tracker) workspace. This file serves as the universal bootstrap context for agent execution across all runtime harnesses (including Antigravity and OpenCode).

## 👥 Roles & Governance
- **Architect (User)**: Defines high-level design, product requirements, and features. Reviewer of plans.
- **Executor (Agent)**: Reads files, proposes plans, executes implementation tasks, runs verification checks, and commits code.

## 📂 Memory Layout & Universal Bootloader Protocol
All state and memory documents reside under the `.agents/` folder. 

CRITICAL INITIALIZATION DIRECTIVE: Before processing any user request, generating execution plans, or modifying code, the executor MUST use its file-reading tools to read the following workspace documents to fully populate its active context window. Do not attempt to guess the project layout:
1. Read `AGENTS.md` (This file) to establish system boundaries.
2. Read `.agents/ACTIVE_CONTEXT.md` to fetch active phase objectives and the feature backlog.
3. Read `.agents/ARCHITECTURE.md` to map the Kotlin/Python multi-sensor pipeline layout.
4. Read `.agents/LEARNINGS.md` to ingest historical bugs and architectural discoveries.
5. Read `.agents/rules/operating_protocol.md` to load the step-by-step execution rules.

## Context Management & Token Quota Optimization
To prevent chat bloat, terminal lag, and context window exhaustion, you must actively police your working context for topic drift:

1. **Detect Topic Shifts**: Before executing a new task or sub-task, analyze whether the previous turn's code outputs or logs are required. Strive to isolate your immediate context window to the current task.
2. **Environment-Appropriate Context Pruning**:
   - *In Interactive Environments (e.g., Antigravity)*: If a topic shift occurs, halt and explicitly ask the user: *"I notice we are shifting focus to [New Topic]. Should we prune our short-term chat context to save your token quota?"* If confirmed, sync progress to `.agents/ACTIVE_CONTEXT.md` and instruct the user to refresh the thread.
   - *In Autonomous/CLI Environments (e.g., OpenCode)*: Do not halt execution loops. Rely strictly on reading the targeted workspace markdown files (`.agents/` directory) rather than maintaining an extensive shell command history log. Keep terminal output clean and concise.

## 🚫 Strictly Forbidden Tools
- **DO NOT USE WHISPER AI**: Local Whisper models (like Whisper `base` or `tiny`) are strictly forbidden for audio narration transcription. They are highly fragile under continuous background noise (such as bowling machine hum), leading to hallucinated repetition loops and missing anchors. Gemini's direct audio transcription must always be used instead, with systematic clock drift resolved mathematically at the sensor alignment layer (e.g., using 2D Joint Offset and Linear Drift Rate Optimization).

## 🚫 Strictly Forbidden Metrics Reporting
- **NEVER report training-set or cross-validation accuracy as model performance**. Scikit-learn `cross_val_score`, training accuracy, or any metric computed on data used for training (including synthetic/augmented data) is a training diagnostic only. It must NEVER be presented to the user as the model's accuracy or used to justify model quality.
- **ONLY report real-world ground truth accuracy** from `SwingDetectorGroundTruthTest.kt` scorecard results (or the authoritative `score_phone_pipeline.py` script output). This is the single source of truth for model performance.
- When reporting accuracy improvements, always compare the **ground truth scorecard before vs after** — never synthetic CV metrics.