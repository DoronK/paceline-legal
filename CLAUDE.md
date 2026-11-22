# CLAUDE.md

## Which issues an agent may pick up (owner, 2026-11-22)

An agent picks up only GitHub issues that carry its own work label:

- `Claude-work`: Claude Code agents (local sessions, their subagents, cloud sessions, auto-pilot).
- `Instinct-work`: Instinct.

Only the owner adds work labels; an agent never adds one, including on issues it files. Lane notes (`instinct`, `Claude Agent`), priority and ROADMAP order never make an issue workable. An issue without your work label may be worked only when the owner names it in the current request. If no issue carries your work label, say so and stop. Reviewing, merging or releasing work the owner asks for directly is not pickup.
