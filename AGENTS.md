# Antigravity Agent Configuration

Welcome to the Pitch Analytix Pro (Cricket Batting Tracker) workspace. This file serves as the bootstrap context for agent execution.

## 👥 Roles & Governance
- **Architect (User)**: Defines high-level design, product requirements, and features. Reviewer of plans.
- **Executor (Agent)**: Reads files, proposes plans, executes implementation tasks, runs verification checks, and commits code.

## 📂 Memory Layout
All state and memory documents reside under the `.agents/` folder:
- **`ACTIVE_CONTEXT.md`**: Contains system objectives, technical approach, active phase objectives, feature backlog catalog, and verification criteria.
- **`ARCHITECTURE.md`**: Maps the system structure, data flow diagrams, WearOS real-time kinematics state machine, and directory layout.
- **`LEARNINGS.md`**: Tracks key decisions, bugs resolved, and performance scorecard historical summaries.
- **`rules/`**: Workspace directives and constraints.
  - **`operating_protocol.md`**: The step-by-step execution protocol (CLARIFY, PLAN, EXECUTE, VERIFY, COMMIT) and stateless operations rules.

Before starting any task, the executor must read `AGENTS.md`, `.agents/ACTIVE_CONTEXT.md`, `.agents/ARCHITECTURE.md`, `.agents/LEARNINGS.md`, and `.agents/rules/operating_protocol.md` to load the current workspace state.
