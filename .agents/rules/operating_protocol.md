---
trigger: always_on
---

# Operating Protocol: Pitch Analytix Pro

## Core Directives

1. **Stateless Operations**: I am the architect; you are the executor. You must read AGENTS.md and .agents/ACTIVE_CONTEXT.md before performing any task. This constraint applies equally to interactive development sessions and autonomous terminal execution loops.
2. **State Gatekeeping**: Do not modify any core code unless the current phase in `.agents/ACTIVE_CONTEXT.md` matches the intended operation.
3. **Memory Persistence**: After every session, update `.agents/LEARNINGS.md` with a summary of the technical decisions made.
4. **Verification**: Every code-change task must end with a self-verification check against `.agents/ACTIVE_CONTEXT.md`.

---

## Ideal Workflow Stages

### 1. CLARIFY
* **Action**: The model reviews the task requirements.
* **Tooling / Guardrail**: The model reviews the task requirements. Propose a clarification loop (using the /grill-me tool if available, or providing a explicit list of technical assumptions if running inside a headless terminal engine) to seek architectural direction from the architect.
* **Pre-Code Internal Debate**: Before formulating a final plan, state your technical assumptions explicitly. Actively attempt to find edge cases, race conditions, or logic flaws in your own proposed solution. If you cannot decisively refute your own counter-hypothesis, halt and use `/grill-me` to workshop it with the user before proceeding.

### 2. PLAN
* **Action**: Write an Implementation Plan document (including any open questions or breaking design choices) to the artifact directory.
* **Approval Gate**: Await explicit user approval before modifying any code.

### 3. EXECUTE
* **Action**: Propose and apply the code modifications.
* **Confinement**: Keep context clean; apply changes incrementally. If using subagents or spawning nested execution processes (e.g., OpenCode sub-agents), delegate isolated tasks within highly constrained context limits, ensuring resource usage stays within a strict 30% ceiling of the host session configuration.

### 4. VERIFY
* **Action**: Validate the correctness of the code changes.
* **Tooling**: Run automated test suites (such as `SwingDetectorGroundTruthTest`), execute checking scripts, or inspect logs. Self-verify outputs against target metrics.
* **Adversarial Test-Debater Guardrail**: Never declare a task complete based on passing test outputs alone. You must temporarily adopt a "Test-Debater" persona and audit your own test code. You must explicitly verify:
    1. *"Am I just testing the happy path, or am I actively trying to break this code?"*
    2. *"Does this test actually assert the fix, or is it written so broadly that it passes even if the underlying bug is still present?"*
    3. *"Are there hidden edge cases, null states, or kinematic variations this test is ignoring?"*
    
    Achieving a green terminal status AND passing this internal Test-Debating audit is the strict prerequisite to changing any state in `.agents/ACTIVE_CONTEXT.md` or proceeding to the COMMIT stage.

### 5. COMMIT
* **Action**: Commit changes to local version control.
* **Standard**: Use atomic commits with descriptive commit messages. Stage only modified/new files relevant to the active task.