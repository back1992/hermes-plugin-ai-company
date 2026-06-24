# Design Spec: hermes-plugin-ai-company v2.0 — Superpowers + Ponytail Hybrid

**Date:** 2026-06-24
**Version:** 2.0.0
**Status:** Approved for implementation planning
**Reference:** [obra/superpowers](https://github.com/obra/superpowers)

---

## 1. Overview

### What Is This

A complete v2.0 restructure of the `hermes-plugin-ai-company` Hermes Agent plugin, merging the [Superpowers](https://github.com/obra/superpowers) agentic development methodology with the existing Ponytail/YAGNI philosophy.

### Core Identity

**"Ponytail meets Superpowers"** — A minimalist, evidence-driven development workflow where YAGNI questioning happens at every stage and Iron Law discipline governs implementation.

### Philosophy (Merged)

| Principle | Source | Description |
|-----------|--------|-------------|
| **Ponytail ladder** | Original | Question every requirement: delete → stdlib → dependency → one-line → minimum |
| **Iron Laws** | Superpowers | No code without failing test, no fix without root cause, no completion without evidence |
| **Evidence before claims** | Superpowers | Every assertion backed by fresh verification output |
| **Anti-rationalization** | Superpowers | Preemptive excuse tables in every role prompt |
| **Context isolation** | Superpowers | Each sub-agent gets only the context it needs |
| **YAGNI** | Both | You Aren't Gonna Need It — enforced at every wave |

### Clean Break

This is a v2.0 with no backward compatibility:
- New wave structure (6 waves, was 5)
- New tool API (9 tools, was 8; new `company_dispatch_task`)
- New role set (7 roles, was 6; adds `task_reviewer`)
- New database schema (adds `tasks` table, `plan_text` column)
- Old SQLite sessions are not migrated

---

## 2. Pipeline (6 Waves)

```
Wave 1: 🧠 Brainstorm+Design → Produces approved spec (Ponytail ladder applied)
Wave 2: 📋 Planning          → Bite-sized tasks with TDD requirements, exact file paths
Wave 3: 💻 Implementation    → Per-task subagents (Iron Law TDD, two-stage review each)
Wave 4: 🧪 Verification      → QA + evidence-before-claims gates, regression tests
Wave 5: 📝 Review            → Two-stage (spec compliance + quality) + Ponytail hunt
Wave 6: 🔧 Fix+Finish        → Systematic debugging + verification + merge decision
```

### Wave Definitions

```python
WAVE_DEFINITIONS = [
    {"number": 1, "name": "Brainstorm + Design", "roles": ["brainstormer"],
     "parallel": False, "max_agents": 1, "auto_trigger": None},
    {"number": 2, "name": "Planning", "roles": ["planner"],
     "parallel": False, "max_agents": 1, "auto_trigger": None},
    {"number": 3, "name": "Implementation", "roles": ["implementer", "task_reviewer"],
     "parallel": False, "max_agents": 1, "auto_trigger": None, "per_task": True},
    {"number": 4, "name": "Verification", "roles": ["verifier"],
     "parallel": False, "max_agents": 1, "auto_trigger": None},
    {"number": 5, "name": "Review", "roles": ["reviewer"],
     "parallel": False, "max_agents": 1, "auto_trigger": None},
    {"number": 6, "name": "Fix + Finish", "roles": ["fixer"],
     "parallel": False, "max_agents": 1, "auto_trigger": "on_review_fail"},
]
```

### Auto-Trigger Rules

- **Wave 6** triggers when Wave 5 (Review) completes with `CHANGES_REQUESTED` in summary
- **Wave 4** skips if Wave 3 has 0 completed tasks (nothing to verify)

### Context Flow

```
Wave 1 (Brainstorm) → spec stored as context
Wave 2 (Plan)       → receives spec, produces task list stored as context + tasks table
Wave 3 (Impl)       → each task receives: plan excerpt for THAT task + spec context
Wave 4 (Verify)     → receives: all task results + files created + test outputs
Wave 5 (Review)     → receives: all task results + verifier evidence + plan
Wave 6 (Fix)        → receives: review findings + verifier evidence + plan
```

---

## 3. Roles (7 Agents)

### 3.1 Brainstormer (Wave 1)

**Identity:** Socratic design refiner + Ponytail questioner. Produces an approved spec, not a plan.

**Methodology:**
- Hard gate: No implementation begins until spec is approved
- One-question-at-a-time Socratic method to refine requirements
- Ponytail ladder applied to every requirement before it enters the spec
- Scope assessment first — if the feature has multiple independent subsystems, flag it

**Deliverables:**
- Design doc saved to `docs/design/<feature>.md`
- Questioned Requirements section (what we're NOT building and why)
- Deliberate Simplifications (ponytail: [ceiling], [upgrade trigger])

**Anti-patterns:** "This is too simple to need design", "Let me just plan it directly"

### 3.2 Planner (Wave 2)

**Identity:** Task decomposer. Breaks the approved spec into bite-sized, zero-context tasks.

**Methodology:**
- Bite-sized tasks (2-5 min each) — "Write failing test" is one step, "Run it" is another
- Zero-context assumption — each task is self-contained with exact file paths, complete code snippets
- TDD embedded — every task starts with "Write failing test for [behavior]"
- Self-review checklist before delivery: spec coverage, no TBD/TODO, type consistency

**Deliverables:**
- Plan saved to `plans/<feature>.md`
- Header: Goal, Architecture (2-3 sentences), Tech Stack
- Numbered task list with: exact file paths, exact commands with expected output, TDD steps

**Anti-patterns:** "TBD", "Add appropriate error handling", "Similar to Task N", "Write tests for the above"

### 3.3 Implementer (Wave 3, per-task)

**Identity:** Task executor with Iron Law TDD + Ponytail minimalism.

**Methodology:**
- Iron Law: Absolutely no production code without a failing test first. If code written before test → must be completely deleted
- Red-Green-Refactor cycle — Write test → Verify it fails → Write minimal code → Verify it passes → Refactor
- Ponytail coder mode — Simplification ladder before every piece of code
- Status-based output: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
- Self-review checklist before marking DONE: tests exist, all pass, no speculative code

**Anti-rationalization table:**
| Excuse | Reality |
|--------|---------|
| "It's too simple to test" | Simple code can have bugs |
| "I'll add tests later" | Later never comes |
| "Tests first is wasteful" | Untested code is unfinished |
| "TDD is dogmatic" | Discipline > feelings |

### 3.4 Task Reviewer (Wave 3, per-task)

**Identity:** Per-task quality gate. Reviews spec compliance + code quality for each implementation task.

**Methodology:**
- Two-stage review:
  - Stage 1: Spec compliance — Does the task match the plan? Are all requirements met?
  - Stage 2: Code quality — Readability, security, performance, patterns
- Ponytail over-engineering hunt — scoped to this task
- Severity-tiered findings: Critical (block), Important (fix before next task), Minor (note)
- Context isolation — Reviews only the diff + task requirements, not implementation history
- Push-back protocol — If finding seems wrong, implementer can push back with technical evidence

**Verdict:** APPROVED / CHANGES_REQUESTED (with severity-tagged findings)

### 3.5 Verifier (Wave 4)

**Identity:** Evidence-gated QA engineer. Nothing passes without proof.

**Methodology:**
- Evidence-before-claims gate: IDENTIFY → RUN → READ → VERIFY → CLAIM. Skipping any step = failure.
- Claim-to-evidence mapping:
  | Claim | Required Evidence |
  |-------|------------------|
  | "Tests pass" | Test command output showing 0 failures |
  | "Linter clean" | Linter output showing 0 errors |
  | "Build succeeds" | Build exit 0 |
  | "Coverage adequate" | Coverage report with numbers |
  | "Bug fixed" | Regression test: pass→revert→fail→restore→pass |
- Regression test pattern — Must prove the test catches the regression
- Red-flag word detection — "should", "probably", "seems to" trigger STOP
- Playwright E2E retained from v1.3.1

**Anti-rationalization table:** "Should work now", "I'm confident", "Partial check is enough"

**Verdict:** PASS (all evidence verified) / FAIL (with missing evidence list)

### 3.6 Reviewer (Wave 5)

**Identity:** Whole-branch reviewer. Two-stage review + Ponytail over-engineering hunt.

**Methodology:**
- Two-stage review (same as task reviewer but at whole-branch level)
- Ponytail Stage 4 — Over-engineering hunt across all files
- Verification cross-check — Compare reviewer findings against verifier's evidence
- TDD rejection criteria — Any feature lacking test coverage = CHANGES_REQUESTED
- Severity-tiered findings — Critical/Important/Minor

**Key change from v1:** Reviews the whole branch (all tasks combined) rather than individual files.

### 3.7 Fixer (Wave 6)

**Identity:** Systematic debugger + verification-gated fixer.

**Methodology:**
- 4-phase systematic debugging (mandatory):
  1. Root Cause Investigation — Read errors, reproduce, check recent changes, trace data flow
  2. Pattern Analysis — Find working examples, compare differences
  3. Hypothesis & Testing — Single hypothesis, minimal change, one variable at a time
  4. Implementation — Failing test → single fix → verify
- 3-fix escalation rule — If 3+ fix attempts fail, escalate to architecture discussion
- Verification gates on every fix — Must show evidence the fix works before claiming it does

**Anti-rationalization table:** "Quick fix for now", "Just try changing X", "I see the problem"

**Finishing decision:** After fixes are verified, the fixer agent's output includes a "FINISHING_OPTIONS" section listing: merge to main, create PR, keep branch, discard. The orchestrator agent presents these options to the human and acts on their choice.

---

## 4. Tool API (v2.0)

### Tools (9 total)

| Tool | Description | v1→v2 Change |
|------|-------------|---------------|
| `company_start` | Create session | Same API, new internal waves |
| `company_dispatch` | Build context for wave/role, or record results | Changed: Wave 3 returns task list, not single prompt |
| `company_dispatch_task` | **NEW** — Dispatch single implementation task | New tool |
| `company_status` | Check session progress | Changed: includes per-task progress |
| `company_config` | Override role prompts | Same |
| `company_report` | Final session report | Changed: includes per-task breakdown |
| `company_list` | List sessions | Same |
| `company_delete` | Delete session | Same |
| `company_create_issue` | Linear issue creation | Same (+ fix missing `os` import) |

### `company_dispatch_task` Schema

```json
{
  "name": "company_dispatch_task",
  "description": "Dispatch a single implementation task from the plan. Returns the implementer prompt + context. After implementation, pass result to record completion and trigger task review.",
  "parameters": {
    "type": "object",
    "properties": {
      "session_id": {
        "type": "string",
        "description": "The session ID"
      },
      "task_index": {
        "type": "integer",
        "description": "0-based index into the plan's task list"
      },
      "result": {
        "type": "object",
        "description": "Record task result: {status: done|done_with_concerns|blocked, summary, files_created, commit_sha}"
      }
    },
    "required": ["session_id", "task_index"]
  }
}
```

### Task Lifecycle in Wave 3

```
For each task in plan:
  1. company_dispatch_task(session_id, task_index)
     → Engine calls start_task(). Returns implementer prompt with task context.
  2. [Orchestrator delegates to implementer sub-agent]
  3. company_dispatch_task(session_id, task_index, result={status:"done", ...})
     → Engine calls complete_task() then start_task_review().
     → Returns task_reviewer prompt with implementation context.
  4. [Orchestrator delegates to task_reviewer sub-agent]
  5. If review has Critical/Important issues:
     → Orchestrator calls company_dispatch_task with task_index again (no result)
       → Engine calls start_task_fix(). Returns implementer prompt for fix.
     → Fix sub-agent runs, result recorded again via step 3.
     → Re-review cycle continues until APPROVED.
  6. Engine calls complete_task_review() with APPROVED verdict.
     Mark task complete, proceed to next task.
```

### `company_dispatch` for Wave 3

When dispatching Wave 3 via `company_dispatch`, it returns a plan summary with task list instead of a single prompt:

```json
{
  "session_id": "...",
  "wave_number": 3,
  "wave_name": "Implementation",
  "mode": "per_task",
  "task_count": 5,
  "tasks": [
    {"index": 0, "description": "Add user model with tests", "files": ["src/models/user.py"]},
    {"index": 1, "description": "Implement auth endpoint with tests", "files": ["src/api/auth.py"]}
  ],
  "instruction": "Use company_dispatch_task for each task sequentially"
}
```

---

## 5. Engine & Database

### Database Schema (v2.0)

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    config TEXT DEFAULT '{}',
    plan_text TEXT DEFAULT '',
    task_count INTEGER DEFAULT 0,
    schema_version INTEGER DEFAULT 2
);

CREATE TABLE waves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    number INTEGER NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    summary TEXT DEFAULT '',
    files_created TEXT DEFAULT '[]',
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    task_index INTEGER NOT NULL,
    description TEXT NOT NULL,
    files TEXT DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending',
    implementer_summary TEXT DEFAULT '',
    reviewer_verdict TEXT DEFAULT '',
    reviewer_findings TEXT DEFAULT '[]',
    files_created TEXT DEFAULT '[]',
    commit_sha TEXT DEFAULT '',
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE context_store (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    wave_number INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_waves_session ON waves(session_id);
CREATE INDEX idx_context_session ON context_store(session_id, wave_number);
CREATE INDEX idx_tasks_session ON tasks(session_id);
```

### New Engine Methods

**Task management:**
- `create_tasks(session_id, tasks: list[dict])` — Called after planning wave completes
- `get_task(session_id, task_index)` — Get single task info
- `get_all_tasks(session_id)` — Get all tasks with progress
- `start_task(session_id, task_index)` — Mark as implementing
- `complete_task(session_id, task_index, result)` — Mark task done
- `start_task_review(session_id, task_index)` — Mark as reviewing
- `complete_task_review(session_id, task_index, verdict, findings)` — Record review
- `start_task_fix(session_id, task_index)` — Mark as fixing
- `all_tasks_complete(session_id) → bool` — Check if Wave 3 is done

**Plan storage:**
- `store_plan(session_id, plan_text, tasks)` — Save plan text and create task records

**Report enhancement:**
- `generate_report()` now includes per-task breakdown for Wave 3

### Schema Versioning

A `schema_version` integer in the `sessions` table (defaulting to 2) to detect v1 vs v2 databases. Old v1 data is left as-is; new sessions always use v2 schema.

---

## 6. File Structure

```
hermes-plugin-ai-company/
  __init__.py          — Plugin registration (9 tools)
  engine.py            — Core engine: SQLite, wave/task management, context passing
  tools.py             — Tool schemas + handler functions (9 tools)
  prompts.py           — NEW: All role prompts extracted to separate file
  tests/
    conftest.py        — Test config
    test_engine.py     — NEW: Engine unit tests
    test_tools.py      — NEW: Tool handler tests
    test_prompts.py    — NEW: Prompt template tests
  plugin.yaml          — Version 2.0.0
  README.md            — Updated docs
  LICENSE              — Same MIT
```

**Key structural change:** Role prompts extracted from `engine.py` into `prompts.py`. The current code has ~300 lines of prompt strings in the engine — separating them makes prompts easier to iterate on independently.

---

## 7. Testing Strategy

### test_engine.py
- Session CRUD (create, get, list, delete)
- Wave lifecycle (pending → running → completed/failed)
- Task management (create, start, complete, review, fix cycle)
- Context store (save/retrieve, wave ordering)
- Plan storage and task creation
- Auto-trigger logic (Wave 6 on review fail)
- Report generation with task breakdown
- All-tasks-complete check

### test_tools.py
- All 9 tool handlers with valid input
- All 9 tool handlers with invalid/missing input
- `company_dispatch_task` lifecycle (dispatch → result → review trigger)
- `company_dispatch` Wave 3 per-task mode response
- Error handling and edge cases
- Import fallback behavior

### test_prompts.py
- All 7 role prompts render with required placeholders (`project_path`, `feature_name`, `previous_context`, `extra_context`)
- Anti-rationalization tables present in: implementer, verifier, fixer
- Iron Law language present in: implementer
- Evidence-before-claims gate present in: verifier
- Ponytail ladder present in: all 7 roles
- Systematic debugging phases present in: fixer
- No placeholder text (TBD/TODO) in any prompt
- Self-review checklists present in: planner, implementer

---

## 8. Bug Fixes

- **Missing `os` import** in `tools.py:592` — `_handle_company_create_issue` uses `os.path.expanduser` but `os` is never imported. Fixed in v2.0.

---

## 9. Migration Notes

- Old SQLite DB at `~/.hermes/ai-company-sessions.db` is not migrated
- v1 sessions remain readable but cannot be dispatched (old wave structure)
- New sessions always use v2 schema
- `company_list` shows both v1 and v2 sessions (schema_version distinguishes them)
