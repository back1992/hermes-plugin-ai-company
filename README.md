# Hermes Plugin: AI Company v2.0

An orchestration plugin for [Hermes Agent](https://hermes-agent.nousresearch.com/) that implements a **Superpowers + Ponytail** development methodology — spawning sub-agents through 6 disciplined waves with per-task implementation.

## Install

```bash
hermes plugins install back1992/hermes-plugin-ai-company --enable
```

## Quick Start

This plugin does NOT call agents directly. It manages **state** and builds **context** — you (the orchestrator agent) use the tools to get context packs, then call `delegate_task` yourself.

```
Step 1: company_start         → create session, get session_id
Step 2: company_dispatch(wave=1) → brainstormer prompt
        delegate_task(roles=["brainstormer"]) → spec
        company_dispatch(wave=1, role="brainstormer", status="completed", result={summary: "..."})
Step 3: company_dispatch(wave=2) → planner prompt
        delegate_task(roles=["planner"]) → plan + tasks
        company_dispatch(wave=2, role="planner", status="completed", result={summary: "...", files_created: [...]})
Step 4: company_dispatch(wave=3) → returns task list
        FOR each task:
          company_dispatch_task(task_index=N) → implementer prompt
          delegate_task(roles=["implementer"]) → done
          company_dispatch_task(task_index=N, result={status: "done", summary: "...", files_created: [...]})
          delegate_task(roles=["task_reviewer"]) → verdict
          IF CHANGES_REQUESTED: fix → re-review
Step 5: company_dispatch(wave=4) → verifier prompt
        delegate_task(roles=["verifier"]) → verification
        company_dispatch(wave=4, role="verifier", status="completed", result={summary: "..."})
Step 6: company_dispatch(wave=5) → reviewer prompt
        delegate_task(roles=["reviewer"]) → review
        company_dispatch(wave=5, role="reviewer", status="completed", result={summary: "..."})
Step 7: IF review failed → company_dispatch(wave=6) → fixer prompt (auto-suggested)
        delegate_task(roles=["fixer"]) → fixes
Step 8: company_report → final report
```

## Philosophy

| Principle | Source |
|-----------|--------|
| **Ponytail ladder** | YAGNI questioning: delete → stdlib → dependency → one-line → minimum |
| **Iron Laws** | No code without failing test, no fix without root cause, no completion without evidence |
| **Evidence before claims** | Every assertion backed by fresh verification output |
| **Anti-rationalization** | Preemptive excuse tables in every role prompt |

## Tool Reference

### `company_start` — Initialize a session

Starts a new development session. Creates wave records for all 6 waves and sets status to `active`.

```json
{
  "project_path": "/path/to/project",
  "feature_name": "Add user authentication",
  "auto_start": true
}
```

**Returns:**
```json
{
  "session_id": "abc-123",
  "project_path": "/path/to/project",
  "feature_name": "Add user authentication",
  "wave_count": 6,
  "status": "active",
  "next_action": "dispatch_wave_1"
}
```

---

### `company_dispatch` — Build context for a wave

**Two modes:**

1. **Get prompt** (no `role`): Returns the role-specific prompt with auto-injected previous context
2. **Record result** (with `role`, `status`, `result`): Records wave completion and saves result to context store

#### Mode 1: Get Prompt

```json
{
  "session_id": "abc-123",
  "wave_number": 1
}
```

Returns the brainstormer prompt with context from previous waves injected automatically.

#### Mode 2: Record Result

```json
{
  "session_id": "abc-123",
  "wave_number": 1,
  "role": "brainstormer",
  "status": "completed",
  "result": {
    "summary": "Approved spec: JWT-based auth with refresh tokens",
    "files_created": ["docs/design/auth.md"]
  }
}
```

**Auto-trigger detection:** If a verifier or reviewer result contains keywords like `FAIL`, `CHANGES_REQUESTED`, `NEEDS_FIX`, the response includes a `fix_wave_hint` field suggesting Wave 6 dispatch.

**Special: Wave 3 without role** returns per-task mode (see below).

---

### `company_dispatch_task` — Dispatch a single implementation task (Wave 3)

Wave 3 uses per-task subagents instead of per-wave. This tool has two modes:

#### Mode 1: Get implementer prompt for a task

```json
{
  "session_id": "abc-123",
  "task_index": 0
}
```

Returns:
```json
{
  "role": "implementer",
  "prompt": "...",
  "task": {
    "description": "Add user model",
    "files": ["src/models/user.py"]
  }
}
```

#### Mode 2: Record task result and get task_reviewer prompt

```json
{
  "session_id": "abc-123",
  "task_index": 0,
  "result": {
    "status": "done",
    "summary": "User model implemented with SQLAlchemy, all tests passing",
    "files_created": ["src/models/user.py", "tests/test_user.py"],
    "commit_sha": "a1b2c3d"
  }
}
```

Returns the task_reviewer prompt for reviewing that specific task.

**Task statuses:** `done`, `done_with_concerns`, `blocked`

---

### `company_status` — Check session progress

```json
{
  "session_id": "abc-123"
}
```

Returns wave statuses, counts, and if tasks exist, a per-task breakdown:

```json
{
  "session_id": "abc-123",
  "status": "active",
  "progress": { "completed": 2, "running": 1, "pending": 3, "total": 7 },
  "waves": [...],
  "tasks": [
    { "index": 0, "description": "Add user model", "status": "completed" },
    { "index": 1, "description": "Add auth endpoint", "status": "reviewing" }
  ],
  "task_progress": { "completed": 1, "total": 2 }
}
```

---

### `company_config` — Override role prompts

```json
{
  "session_id": "abc-123",
  "roles_yaml": "implementer: |\n  You are a TDD expert...\nreviewer: |\n  You focus on security..."
}
```

---

### `company_report` — Generate final report

```json
{
  "session_id": "abc-123"
}
```

Returns a formatted report with all wave results, file counts, and session duration. Marks session as `completed`.

---

### `company_list` — List sessions

```json
{
  "project_path": "/path/to/project",
  "status": "active",
  "limit": 20
}
```

---

### `company_delete` — Delete a session

```json
{
  "session_id": "abc-123"
}
```

---

### `company_create_issue` — Create Linear issues for bugs

When a sub-agent discovers a bug, call this to create a Linear issue with dedup checking.

```json
{
  "title": "[QA] Auth fails when token expires",
  "description": "Steps to reproduce:\n1. Login\n2. Wait 1h\n3. Click profile → 500 error",
  "priority": 2,
  "team": "LIN",
  "labels": "bug,auth",
  "session_id": "abc-123"
}
```

Requires `LINEAR_API_KEY` environment variable.

---

## Complete Workflow Example

### 1. Start session

```bash
company_start(project_path="/my/app", feature_name="Add payment integration")
# → session_id: "xyz-456"
```

### 2. Wave 1: Brainstorm + Design

```bash
# Get brainstormer prompt (includes project context)
company_dispatch(session_id="xyz-456", wave_number=1)
# → returns prompt for brainstormer role

# Delegate to brainstormer sub-agent
delegate_task(roles=["brainstormer"], prompt=<returned_prompt>)
# → returns: "Approved spec: Stripe integration with webhooks..."

# Record the result
company_dispatch(
  session_id="xyz-456",
  wave_number=1,
  role="brainstormer",
  status="completed",
  result={
    summary: "Approved spec: Stripe integration with webhook handlers",
    files_created: ["docs/design/payments.md"]
  }
)
```

### 3. Wave 2: Planning

```bash
# Get planner prompt (includes Wave 1 spec in previous_context)
company_dispatch(session_id="xyz-456", wave_number=2)
# → returns prompt for planner role

# Delegate to planner sub-agent
delegate_task(roles=["planner"], prompt=<returned_prompt>)
# → returns: "# Implementation Plan\n## Tasks\n1. Create Payment model..."

# Store the plan and create tasks
company_dispatch(
  session_id="xyz-456",
  wave_number=2,
  role="planner",
  status="completed",
  result={
    summary: "# Implementation Plan\nTasks: 0) Payment model, 1) Stripe client, 2) Webhook handler",
    files_created: ["docs/plan.md"]
  }
)
```

### 4. Wave 3: Implementation (Per-Task)

```bash
# Get task list
company_dispatch(session_id="xyz-456", wave_number=3)
# → returns: { mode: "per_task", task_count: 3, tasks: [...] }

# --- Task 0: Payment model ---
# Get implementer prompt
company_dispatch_task(session_id="xyz-456", task_index=0)
# → returns implementer prompt

delegate_task(roles=["implementer"], prompt=<implementer_prompt>)
# → implements the task

# Record result, get task_reviewer prompt
company_dispatch_task(
  session_id="xyz-456",
  task_index=0,
  result={
    status: "done",
    summary: "Payment model with SQLAlchemy, migrations created",
    files_created: ["src/models/payment.py", "migrations/001_payment.py"],
    commit_sha: "abc123"
  }
)
# → returns task_reviewer prompt

delegate_task(roles=["task_reviewer"], prompt=<reviewer_prompt>)
# → "APPROVED"

# --- Task 1: Stripe client (same pattern) ---
# --- Task 2: Webhook handler (same pattern) ---
```

### 5. Wave 4: Verification

```bash
company_dispatch(session_id="xyz-456", wave_number=4)
delegate_task(roles=["verifier"], prompt=<verifier_prompt>)
# → runs tests, collects evidence

company_dispatch(
  session_id="xyz-456",
  wave_number=4,
  role="verifier",
  status="completed",
  result={
    summary: "All 47 tests passing. Evidence attached.",
    files_created: []
  }
)
```

### 6. Wave 5: Review

```bash
company_dispatch(session_id="xyz-456", wave_number=5)
delegate_task(roles=["reviewer"], prompt=<reviewer_prompt>)
# → reviews all changes

company_dispatch(
  session_id="xyz-456",
  wave_number=5,
  role="reviewer",
  status="completed",
  result={
    summary: "APPROVED. Code quality good. Minor style nit fixed.",
    files_created: []
  }
)
# → if CHANGES_REQUESTED, response includes fix_wave_hint for Wave 6
```

### 7. Wave 6: Fix + Finish (if needed)

Only dispatched if Wave 5 review found issues:

```bash
company_dispatch(session_id="xyz-456", wave_number=6)
delegate_task(roles=["fixer"], prompt=<fixer_prompt>)
# → systematic debugging + fixes
```

### 8. Generate report

```bash
company_report(session_id="xyz-456")
# → formatted final report, marks session as completed
```

## 6-Wave Pipeline

```
Wave 1: 🧠 Brainstorm+Design → Socratic refinement, produces approved spec
Wave 2: 📋 Planning          → Bite-sized tasks with TDD requirements
Wave 3: 💻 Implementation    → Per-task subagents (Iron Law TDD + two-stage review)
Wave 4: 🧪 Verification      → Evidence-gated QA (nothing passes without proof)
Wave 5: 📝 Review            → Two-stage review + Ponytail over-engineering hunt
Wave 6: 🔧 Fix+Finish        → Systematic debugging + verification + merge decision
```

## 7 Roles

| Role | Wave | Methodology |
|------|------|-------------|
| Brainstormer | 1 | Socratic design + Ponytail questioning |
| Planner | 2 | Zero-context task decomposition + TDD |
| Implementer | 3 | Iron Law TDD + Ponytail minimalism |
| Task Reviewer | 3 | Two-stage review per task |
| Verifier | 4 | Evidence-before-claims QA |
| Reviewer | 5 | Whole-branch review + over-engineering hunt |
| Fixer | 6 | 4-phase systematic debugging |

## Fix Wave Auto-Trigger

When Wave 5 (Review) completes with `CHANGES_REQUESTED`, the dispatch result includes a `fix_wave_hint` for Wave 6:

```json
{
  "fix_wave_hint": {
    "wave": 6,
    "reason": "Reviewer requested changes",
    "dispatch_args": { "session_id": "...", "wave_number": 6 }
  }
}
```

The orchestrator should check for this and automatically dispatch Wave 6.

## Session Persistence

Sessions stored in SQLite at `~/.hermes/ai-company-sessions.db` (v2.0 schema). Use `company_list` to browse and `company_delete` to clean up old sessions.

## License

MIT
