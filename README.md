# Hermes Plugin: AI Company v2.0

An orchestration plugin for [Hermes Agent](https://hermes-agent.nousresearch.com/) that implements a **Superpowers + Ponytail** development methodology — spawning sub-agents through 6 disciplined waves with per-task implementation.

## Install

```bash
hermes plugins install back1992/hermes-plugin-ai-company --enable
```

## Philosophy

| Principle | Source |
|-----------|--------|
| **Ponytail ladder** | YAGNI questioning: delete → stdlib → dependency → one-line → minimum |
| **Iron Laws** | No code without failing test, no fix without root cause, no completion without evidence |
| **Evidence before claims** | Every assertion backed by fresh verification output |
| **Anti-rationalization** | Preemptive excuse tables in every role prompt |

## Tools (9)

| Tool | Description |
|------|-------------|
| `company_start` | Initialize a new AI Company session |
| `company_dispatch` | Build context for a wave (Wave 3 returns per-task plan) |
| `company_dispatch_task` | Dispatch a single implementation task (NEW in v2.0) |
| `company_status` | Check session progress (includes per-task breakdown) |
| `company_config` | Override role prompts |
| `company_report` | Generate final session report |
| `company_list` | List all sessions |
| `company_delete` | Delete a session |
| `company_create_issue` | Create Linear issues for discovered bugs |

## How It Works

```
Wave 1: 🧠 Brainstorm+Design → Socratic refinement, produces approved spec
Wave 2: 📋 Planning          → Bite-sized tasks with TDD requirements
Wave 3: 💻 Implementation    → Per-task subagents (Iron Law TDD + two-stage review)
Wave 4: 🧪 Verification      → Evidence-gated QA (nothing passes without proof)
Wave 5: 📝 Review            → Two-stage review + Ponytail over-engineering hunt
Wave 6: 🔧 Fix+Finish        → Systematic debugging + verification + merge decision
```

### Per-Task Implementation (Wave 3)

Wave 3 uses a per-task subagent model:

1. `company_dispatch(session_id, wave_number=3)` returns the task list
2. For each task:
   - `company_dispatch_task(session_id, task_index=N)` → implementer prompt
   - Delegate to implementer sub-agent
   - `company_dispatch_task(session_id, task_index=N, result={...})` → task_reviewer prompt
   - Delegate to task_reviewer sub-agent
   - If CHANGES_REQUESTED: fix → re-review
3. After all tasks complete, dispatch Wave 4

### Fix Wave Auto-Trigger

When Wave 5 (Review) completes with `CHANGES_REQUESTED`, the dispatch result includes a `fix_wave_hint` for Wave 6.

## Roles (7)

| Role | Wave | Methodology |
|------|------|-------------|
| Brainstormer | 1 | Socratic design + Ponytail questioning |
| Planner | 2 | Zero-context task decomposition + TDD |
| Implementer | 3 | Iron Law TDD + Ponytail minimalism |
| Task Reviewer | 3 | Two-stage review per task |
| Verifier | 4 | Evidence-before-claims QA |
| Reviewer | 5 | Whole-branch review + over-engineering hunt |
| Fixer | 6 | 4-phase systematic debugging |

## Session Persistence

Sessions stored in SQLite at `~/.hermes/ai-company-sessions.db` (v2.0 schema).

## License

MIT
