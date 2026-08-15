---
name: ai-company-workflow
description: "AI Company workflow: spawn Brainstormer/Planner/Implementer/TaskReviewer/Verifier/Reviewer/Fixer sub-agents via delegate_task to auto-develop features in 6 waves."
version: 2.1.0
author: Hermes Agent + User
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, subagent, workflow, parallel, roles, company]
    related_skills: [subagent-driven-development, writing-plans, test-driven-development, requesting-code-review]
---

# AI Company Workflow

## Overview

Use Hermes Agent's `delegate_task` to simulate a **software company** where sub-agents play roles (Brainstormer, Planner, Implementer, Task Reviewer, Verifier, Reviewer, Fixer) and develop features across **6 sequential waves** with per-task tracking in the Implementation wave.

**Trigger:** User asks to build, import, migrate, or create any feature with 3+ components. **Also use for systematic bug fixes** (2+ bugs affecting same flow, or bugs requiring investigation across multiple services). This is the **default workflow** for feature development AND non-trivial debugging — use it automatically, don't wait for the user to explicitly say "use AI company workflow". If in doubt, use it. See `references/common-pitfalls.md` for why "obvious" 3-file fixes are the most common skip — and the most costly. Explicit triggers: "build feature X", "use the company flow", "brainstorm → plan → implement → verify → review", "import X into Y", "migrate data from X", "fix X" (when fix touches 3+ layers or requires root cause analysis).

**🚨 ENFORCEMENT:** If you identify 3+ files need changes, STOP — do not write code. Revert any edits and call `company_start`. See `references/enforcement-pitfalls.md` for the 2026-06-18 failure case.

**SELF-ENFORCEMENT GATE — count files BEFORE coding:** If fix touches ≥3 files, workflow is mandatory. Do NOT start implementation until the Planner's plan exists. See `references/self-enforcement-pitfalls.md` for the "simple fix trap" incident and pre-flight checklist.

**Outer workflow — the integration contract:** AI Company produces code + tests + verification reports. Everything *around* that — issue tracking, commits, external approval, deploy, notifications — belongs to your project's own development cycle. Drop an `.ai-company.yaml` at the project root (template: `templates/ai-company.example.yaml`, bundled with this skill; `scripts/setup-project.sh <project-dir>` creates it) to declare the hooks: `tracker` (issue-filing command + issue-ref pattern), `review_gate` (external approval command), `deploy` (deploy + health check), `notify` (notification channel), `project.prod_url` (for E2E proof). When the config exists, AI Company sessions MUST honor it: file issues via the configured command, cite real issue references, never self-approve through the review gate, never deploy except via the configured command. When no config exists, AI Company runs in interactive mode: pause for human approval at the Wave-1→2 gate and before commit/deploy. See "Integration Contract" below.

**AI Company subagents ≠ the external review gate:** If your project has an outer reviewer role (a separate agent or CLI that approves pushes/deploys), AI Company's 7 roles (Brainstormer/Planner/Implementer/Task Reviewer/Verifier/Reviewer/Fixer) are INNER subagents the orchestrator dispatches via `delegate_task` to do complex implementation. The per-task Task Reviewer (Wave 3) and Reviewer (Wave 5) are INTERNAL quality gates — they do NOT replace the final approval. AI Company must never post approvals, merge, or close issues on its own when the integration contract assigns those to the outer cycle. Reference implementation: ppt-bot-v2 runs Hermes as CEO/orchestrator on the prod server, AI Company (or Codex CLI) as the coder surface, and a separate claude CLI session as the outer reviewer — see `docs/reference-implementation.md` in the plugin repo.

**Plugin:** The `ai-company` Hermes plugin (v2.1.0) installs to `~/.hermes/plugins/ai-company/` (`hermes plugins install back1992/hermes-plugin-ai-company --enable`). It provides 9 tools: `company_start`, `company_dispatch`, `company_dispatch_task`, `company_status`, `company_config`, `company_report`, `company_list`, `company_delete`, `company_create_issue`. These handle session management, per-task tracking (Wave 3), auto context passing between waves, and persistent SQLite history. Use these tools when available; fall back to manual `delegate_task` orchestration if the plugin is not loaded. **GitHub:** `back1992/hermes-plugin-ai-company`

**⚠️ Plugin `prompts.py` ROLE_PROMPTS is the source of truth for subagent behavior.** The Skill file (this document) teaches the orchestrator *how to use* the workflow. The Plugin's `prompts.py` `ROLE_PROMPTS` dict (7 roles: brainstormer, planner, implementer, task_reviewer, verifier, reviewer, fixer) is what subagents *actually receive* as their system prompt — they encode the Superpowers + Ponytail methodology (Socratic questioning, YAGNI ladder, Iron Law TDD, evidence-gated verification, 4-phase systematic debugging). When fixing workflow behavior (e.g., "Brainstormer must write design docs"), you MUST update BOTH: (1) the Skill's instructions and (2) the Plugin's `ROLE_PROMPTS` in `prompts.py`. Changing only the Skill has zero effect on subagent output. See pitfall #36.

## When to Use

- Feature has 3+ components (backend, frontend, tests)
- You want automated QA and review between stages
- Tasks are mostly independent (parallelizable)
- Quality matters — you want spec compliance + code quality checks

## When NOT to Use (Skip Conditions)

**Do NOT launch AI Company for these — fix directly:**
- Missing DB column / model field addition (one-line `db.Column` + `ALTER TABLE` + restart)
- Config value change (env var, nginx directive, timeout tuning)
- Import path fix (one file, one line)
- Typo / string constant correction
- Missing `return` statement or early-exit guard
- Any fix where the root cause is a single file and the fix is < 5 lines

**Decision rule**: If you can describe the entire fix as "add line X to file Y, run command Z, restart service" — skip the workflow. AI Company's overhead (Brainstormer → Planner → Implementer → Verifier → Reviewer) for a one-line fix wastes 10+ minutes and produces a 200-line plan for a 1-line change.

**Anti-pattern**: Starting AI Company, dispatching the Brainstormer, then realizing the fix is trivial and killing the session. This wastes the Brainstormer subagent's time. Pre-assess complexity BEFORE `company_start`.

**vs. subagent-driven-development:**
This skill IS subagent-driven-development but with **pre-defined roles** and a **wave execution model**. Use this when the user explicitly wants the "company" metaphor; use `subagent-driven-development` for plan-based execution.

## Core Principle: Test-Driven Development (TDD)

**TDD is MANDATORY, not optional.** Every feature must have tests written BEFORE or ALONGSIDE implementation. The department filter bug (2026-06-14) proved this: no test existed for the filter, so it broke silently in production.

**TDD Enforcement:**
1. **Wave 1 (Brainstormer):** Design spec must define success criteria and edge cases for each requirement
2. **Wave 2 (Planner):** Every task in the plan MUST include specific test requirements (what to test, expected behavior, edge cases) — tasks are bite-sized (2-5 min each), each with exact file paths, code blocks, and commands
3. **Wave 3 (Implementer, per-task):** Iron Law TDD — write ONE failing test, verify RED, write minimal code to pass, verify GREEN, refactor. Each task is dispatched individually via `company_dispatch_task` and reviewed by the Task Reviewer before the next task starts
4. **Wave 4 (Verifier):** Evidence-gated verification — run full test suite, check coverage against plan's test requirements. "Should pass" is not evidence; paste actual command output
5. **Wave 5 (Reviewer):** Whole-branch review — spec compliance + code quality + TDD compliance + Ponytail over-engineering hunt. Reject if test coverage gaps exist

**Test Coverage Requirements:**
- Every API endpoint: at least 1 positive + 1 negative test
- Every filter/search parameter: test with valid value, invalid value, and missing value
- Every form field: test with valid input, invalid input, and edge cases (empty, too long, special chars)
- Every external integration: test with real HTTP call (not just mocks) at least once in QA

## Role Definitions

The 7 roles map to the 6 waves. Wave 3 (Implementation) uses two roles in a per-task cycle: Implementer writes, Task Reviewer reviews, repeat for each task.

| Role | Wave | Responsibility | Key Principle | Output |
|------|------|----------------|---------------|--------|
| Brainstormer | 1 | Refine feature request via Socratic questioning → design spec | Ponytail questioning ladder (YAGNI first), one question at a time, 2-3 approaches before settling | `docs/design/<feature>.md` (architecture, API contracts, questioned requirements) |
| Planner | 2 | Decompose approved spec into bite-sized, zero-context tasks | Each task = 2-5 min, self-contained, exact file paths + code blocks + commands. TDD embedded in every task | `plans/<feature>.md` (task breakdown with TDD steps) |
| Implementer | 3 (per-task) | Execute ONE task with Iron Law TDD | RED-GREEN-REFACTOR. No code before failing test. Ponytail coder mode (YAGNI, stdlib-first, fewest files). Status: DONE / DONE_WITH_CONCERNS / BLOCKED | Implementation + tests for one task |
| Task Reviewer | 3 (per-task) | Review ONE task's diff for spec + quality + over-engineering | Context-isolated (sees only this task). Severity-tiered findings (CRITICAL/IMPORTANT/MINOR). Ponytail hunt tags: delete/stdlib/native/yagni/shrink | APPROVED or CHANGES_REQUESTED per task |
| Verifier | 4 | Verify entire implementation with EVIDENCE | Iron Law: evidence before claims. 5-step gate (identify → run → read → verify → claim). Regression test pattern (pass → revert → FAIL → restore → pass) | Verification report with pasted command output, coverage matrix, PASS/FAIL verdict |
| Reviewer | 5 | Whole-branch review (all tasks combined) | 4-stage: spec compliance → code quality → TDD compliance → Ponytail over-engineering hunt. Cross-checks Verifier's findings. Rejects if untested code exists | APPROVED or CHANGES_REQUESTED with severity-tagged findings |
| Fixer | 6 (auto-trigger) | Address review issues with systematic debugging | 4-phase: root cause investigation → pattern analysis → hypothesis testing → implementation. 3-fix escalation rule. Verification gates on every fix | Fix report with root cause, hypothesis, fix, evidence |

**UX Reviewer** (not a v2.0 role): The v1 "UX Reviewer" wave (3.5) is no longer a built-in role. For browser-based UX/UE review, dispatch a `delegate_task` with `toolsets=['browser', 'file']` manually after Wave 4 (Verifier), using the criteria from the archived "Wave 3.5" instructions below as a reference pattern.

## Critical: E2E Verification After Deployment

**"Deployed" ≠ "Verified"** — After deploying, ALWAYS run E2E proof through the LIVE production URL before reporting success. Check the specific user-reported symptom is resolved, not just that your change loaded. See `references/e2e-verification-pitfalls.md` for the full checklist and common "declared fixed prematurely" patterns.

## Wave Execution

### Wave 1: Brainstorm + Design (single agent)
You (Human CEO)
  │
  └── "Build feature X"
        │
        ├── Wave 1: 🧠 Brainstormer → Socratic questioning → design spec (docs/design/)
        │     └── Ponytail ladder, 2-3 approaches, questioned requirements
        │
        ├── Wave 2: 📋 Planner → decompose spec into bite-sized tasks (plans/)
        │     └── Each task: exact file paths, code blocks, TDD steps, 2-5 min
        │
        ├── Wave 3: 💻 Implementer + 🔍 Task Reviewer (per-task cycle)
        │     └── For EACH task: company_dispatch_task → Implementer → record result → Task Reviewer → APPROVED/CHANGES_REQUESTED
        │
        ├── Wave 4: 🧪 Verifier → evidence-gated verification (full test suite, coverage matrix)
        │
        ├── Wave 5: 📋 Reviewer → whole-branch review (4 stages: spec + quality + TDD + Ponytail)
        │
        └── Wave 6: 🔧 Fixer (auto-trigger on CHANGES_REQUESTED) → systematic debugging
```

**Sequential, not parallel:** All waves have `max_agents=1`, `parallel=False`. The v1 "Coder+UI parallel" model is gone — v2.0 runs sequentially. Wave 3's parallelism is per-task (dispatch each task individually), not per-role.

**Timeout:** ~600s per sub-agent. Timeout ≠ failure — check filesystem.

### ⚠️ Implementer Timeout on Large Tasks (20+ files)
The Implementer subagent consistently times out at 600s for tasks modifying 20+ files (observed 3+ times). It typically completes 80-90% before timing out.

**Recovery protocol:**
1. Check `git diff --stat` + `git ls-files --others --exclude-standard` — see what was done
2. Run tests on the new test files — usually pass, confirming implementation works
3. Fix remaining issues manually (common patterns):
   - Old tests asserting old dimension/feature counts (e.g., `== 12` → `== 15`)
   - Tests triggering real API calls (need `patch.dict(os.environ, {"API_KEY": ""})`)
   - Floating-point weight normalization (sum drifts above 1.0 after overrides)
   - Falsy empty string vs None for API keys (`"" or env_var` falls through)
4. Record Implementer wave as completed with summary of what was done + what was fixed manually

**Prevention**: For plans with >15 tasks, split into 2 sequential Implementer cycles. Give the first cycle the foundation tasks (config, data models, core service), second cycle the integration tasks (pipeline, template, tests).

**Re-dispatch with priority ordering** (2026-06-21 lesson): When re-dispatching after timeout, provide explicit PRIORITY ORDER in the goal so if it times out again, the most critical work is done first. Example: "PRIORITY ORDER: 1. scene_config (NEW), 2. D14 Content Density, 3. D15 Visual CRAP, 4. D13 Structure Logic, 5. Scene-aware prompts, 6. Pipeline integration." This ensures even a second timeout delivers the highest-value work.

### ⚠️ Verifier and Reviewer Are Sequential (NOT Parallel)
In v1, QA and Review could run in parallel. In v2.0, the Reviewer (Wave 5) cross-checks the Verifier's (Wave 4) findings — they are dependent and MUST run sequentially. The Reviewer compares its own findings against the Verifier's evidence report. Running them in parallel causes the reviewer to miss verification gaps. See pitfall #70 for the parallel implementer+verifier race condition.

## Per-Wave Instructions

The plugin's `company_dispatch` builds the role-specific prompt (from `prompts.py` ROLE_PROMPTS) with auto-injected previous-wave context. You call `company_dispatch` to get the prompt, then `delegate_task` to actually run the subagent. **Do not skip the `delegate_task` call** — `company_dispatch` alone does not spawn a subagent (see pitfall #1).

**Relationship to human-in-loop design skills:** Waves 1-2 (Brainstormer → Planner) are the subagent-driven equivalent of an interactive interview → spec → tickets pipeline (the reference project uses `grill-me` → `to-spec` → `to-tickets` skills). When the user is available to answer questions interactively, prefer those skills directly — the user's answers are higher quality than a Brainstormer subagent's guesses. When the user wants fully autonomous multi-agent execution, use the AI Company waves. The two paths produce the same artifacts (`docs/design/<feature>.md` + task breakdown) but differ in who asks/answers the design questions.

### Wave 1: Brainstormer (Design)

```python
# Step 1: Build context pack (plugin auto-injects previous wave results)
ctx = company_dispatch(
    session_id=sid,
    wave_number=1,
    role="brainstormer",
    extra_context="""
    PROJECT CONTEXT:
    - [tech stack, working directory, existing apps/patterns]
    - [any external service API contracts the Brainstormer needs]
    """
)
# Step 2: Actually dispatch the subagent
delegate_task(
    goal=ctx["prompt"],
    context=ctx.get("context_items", []),
    toolsets=["file", "web"],
)
# Step 3: Record the result
company_dispatch(
    session_id=sid, wave_number=1,
    result={"role": "brainstormer", "status": "completed",
            "summary": "...", "files_created": ["docs/design/feature.md"]}
)
```

The Brainstormer produces a design spec at `docs/design/<feature>.md` with: architecture overview, API contracts, data flow, error handling, and a "Questioned Requirements" section (what we're NOT building and why, with the Ponytail rung that eliminated each item). **Ponytail questioning ladder:** for every requirement, stop at the first rung that holds: (1) does this need to exist? (2) does stdlib/platform cover it? (3) does an already-installed dependency solve it? (4) can it be one line? (5) only then → minimum scope.

⏸️ **PAUSE — present design spec to user for approval.** Never auto-proceed from Wave 1 to Wave 2. The design spec is the contract. **Auto-mode exception:** in the unattended prod loop the pause is replaced by the mechanical auto-approval policy in "Prod-only unattended mode" below.

### Wave 2: Planner

```python
ctx = company_dispatch(session_id=sid, wave_number=2, role="planner")
delegate_task(goal=ctx["prompt"], toolsets=["file", "web"])
# Record result — the plan is stored via store_plan() for per-task tracking
company_dispatch(
    session_id=sid, wave_number=2,
    result={"role": "planner", "status": "completed",
            "summary": "...", "files_created": ["plans/feature.md"]}
)
```

The Planner decomposes the approved spec into bite-sized, zero-context tasks saved to `plans/<feature>.md`. Each task includes: exact file paths (with line ranges), complete code blocks (not "similar to Task N"), exact commands with expected output, and TDD steps (write failing test → verify RED → implement → verify GREEN → commit). The plan is stored in the `tasks` SQLite table for per-task dispatch in Wave 3.

### Wave 3: Implementer + Task Reviewer (Per-Task Cycle)

Wave 3 uses `company_dispatch_task` (not `company_dispatch`) because it operates per-task. For each task in the plan:

```python
# Step 1: Get the implementer prompt for task N
task_ctx = company_dispatch_task(session_id=sid, task_index=0)
# Step 2: Dispatch the implementer
impl_result = delegate_task(
    goal=task_ctx["prompt"], toolsets=["terminal", "file"]
)
# Step 3: Record the implementer result → plugin returns the task_reviewer prompt
review_ctx = company_dispatch_task(
    session_id=sid, task_index=0,
    result={
        "status": "done",  # or "done_with_concerns" or "blocked"
        "summary": impl_result.summary,
        "files_created": ["..."],
        "commit_sha": "abc123",
    }
)
# Step 4: Dispatch the task reviewer
review_result = delegate_task(
    goal=review_ctx["prompt"], toolsets=["terminal", "file"]
)
# Step 5: Record the review verdict
#   - APPROVED → task status = "completed", move to next task
#   - CHANGES_REQUESTED → task status = "fixing", re-dispatch implementer for this task
```

Repeat for each task (index 0, 1, 2, ...). The Implementer follows Iron Law TDD: no code before a failing test. The Task Reviewer sees only the current task's diff (context isolation), produces APPROVED or CHANGES_REQUESTED with severity-tiered findings (CRITICAL/IMPORTANT/MINOR) and Ponytail over-engineering hunt tags (delete/stdlib/native/yagni/shrink).

**To get an overview of all tasks in Wave 3:**
```python
company_dispatch(session_id=sid, wave_number=3)
# Returns: {mode: "per_task", task_count: N, tasks: [...], instruction: "Use company_dispatch_task for each task sequentially"}
```

### Wave 4: Verifier

```python
ctx = company_dispatch(session_id=sid, wave_number=4, role="verifier")
delegate_task(goal=ctx["prompt"], toolsets=["terminal", "file"])
company_dispatch(
    session_id=sid, wave_number=4,
    result={"role": "verifier", "status": "completed",
            "summary": "...", "files_created": ["docs/testing/reports/feature-verification.md"]}
)
```

The Verifier follows the Iron Law: evidence before claims. The 5-step gate: (1) IDENTIFY the command that proves the claim, (2) RUN it fresh, (3) READ the full output + exit code, (4) VERIFY the output confirms the claim, (5) ONLY THEN make the claim. "Should pass" is not evidence. The Verifier writes missing tests if critical features lack them, runs E2E tests (Playwright) if configured, and produces a coverage matrix with pasted command output.

### Wave 5: Reviewer

```python
ctx = company_dispatch(session_id=sid, wave_number=5, role="reviewer")
delegate_task(goal=ctx["prompt"], toolsets=["file"])
company_dispatch(
    session_id=sid, wave_number=5,
    result={"role": "reviewer", "status": "completed",
            "summary": "...", "files_created": ["docs/testing/reports/feature-review.md"]}
)
```

The Reviewer does a whole-branch review across all tasks. Four stages: (1) spec & design compliance, (2) code quality, (3) TDD compliance, (4) Ponytail over-engineering hunt. The Reviewer cross-checks its findings against the Verifier's evidence report — if the Verifier claimed PASS but the Reviewer sees issues, it flags the discrepancy. **TDD rejection criteria:** if any feature lacks test coverage, MUST reject with CHANGES_REQUESTED even if the implementation "looks correct."

If the reviewer's summary contains `CHANGES_REQUESTED` or `FAIL`, `company_dispatch` returns a `fix_wave_hint` — auto-dispatch Wave 6.

### Wave 6: Fixer (Auto-Trigger)

```python
ctx = company_dispatch(session_id=sid, wave_number=6, role="fixer")
delegate_task(goal=ctx["prompt"], toolsets=["terminal", "file"])
company_dispatch(
    session_id=sid, wave_number=6,
    result={"role": "fixer", "status": "completed",
            "summary": "...", "files_created": [...]}
)
```

The Fixer follows 4-phase systematic debugging: (1) root cause investigation — read errors, reproduce, trace data flow; (2) pattern analysis — find working examples, compare; (3) hypothesis and testing — one hypothesis, minimal change; (4) implementation — failing test, single fix, verify. **3-fix escalation rule:** if 3+ fix attempts fail for the same issue, STOP and escalate to the coordinator (do not continue patching blindly). Verification gates on every fix: run the specific test, then the full test suite, paste evidence.

### Wave 3.5 (Archived): UX Reviewer — Browser-Based

This is **not a built-in v2.0 role**. For browser-based UX/UE review, dispatch manually after Wave 4 (Verifier) or Wave 5 (Reviewer) if the feature adds user-facing pages:

```python
delegate_task(
    goal="UX/UE review of [feature] pages via browser",
    context="""
    ROLE: UX/UE Reviewer
    GOAL: Walk through the NEW feature's pages in a real browser and evaluate UX quality.

    APPLICATION URL: [production URL — prod_url from .ai-company.yaml]
    LOGIN CREDENTIALS: [if needed]

    PAGES TO REVIEW: [list specific URLs/routes]

    UX EVALUATION CRITERIA (for EACH page):
    1. Visual Hierarchy & Consistency — heading structure, primary vs secondary actions
    2. Loading States & Feedback — loading indicators, toasts, button states
    3. Empty States & Error Handling — no-data view, user-friendly errors, inline validation
    4. Forms & Input UX — clear labels, required fields, double-submission prevention
    5. Navigation & IA — breadcrumbs, 2-click findability, logical tab order
    6. Accessibility — keyboard nav, focus indicators, contrast, ARIA labels
    7. Responsive Design — viewport sizes, touch targets
    8. Chinese Language Quality — no English leaks, natural/professional terminology
    9. Micro-interactions — hover states, transitions, affordances

    WORKFLOW:
    1. Navigate to each page, take screenshot with browser_vision(annotate=true)
    2. Check browser_console() for JS errors after every interaction
    3. Test interactive elements + edge cases (empty, invalid, long text)

    OUTPUT: docs/testing/reports/[feature]-ux-review.md
    VERDICT: UX_APPROVED or UX_CHANGES_REQUESTED
    """,
    toolsets=["browser", "file"],
)
```

## Context Passing (Critical)

Sub-agents have **NO memory**. The plugin's `ContextStore` automatically saves each wave's results and injects them into subsequent waves' prompts via `build_context_for_wave()`. You do NOT need to manually pass previous wave output — the plugin handles this. What you DO need to pass manually is **external context** that the plugin can't know.

**Two channels for context:**
- `extra_context` (in `company_dispatch`) — plugin appends to the auto-generated role prompt; use this for **external API details, existing code patterns, domain constraints, and pre-analyzed root causes** that the Brainstormer/Planner/Implementer needs
- `context` (in `delegate_task`) — only needed for the archived UX Reviewer wave or when bypassing the plugin entirely

**Passing external service context (common pattern):**
When a feature integrates with an external service, pass its API contracts in `extra_context` so the Brainstormer can design against the real interfaces:

```python
company_dispatch(
    session_id=sid, wave_number=1, role="brainstormer",
    extra_context="""
    ## External Service: Auth Service (http://127.0.0.1:8081)
    - GET /api/auth/me — current user profile
    - PUT /api/auth/change-password — old_password + new_password
    - PUT /api/auth/profile — display_name, email
    User model: id(UUID), username, email, display_name, role, department_id
    """
)
```

**Pre-analyzed root cause pattern** (pitfall #51): For bug-fix sessions, do root cause analysis BEFORE dispatching the Brainstormer, then pass findings as `extra_context`:

```python
company_dispatch(
    session_id=sid, wave_number=1, role="brainstormer",
    extra_context="""
    ## 根因分析（已完成调查）
    ### 问题1: [specific issue with file:line references]
    ### 问题2: [specific issue]
    ### 涉及文件（≥4个）
    1. `path/to/file1.py` — what needs to change
    2. `path/to/file2.py` — what needs to change
    """
)
```

**What the plugin auto-passes between waves:**
- Wave 1 (Brainstormer) → `spec` key saved to context_store
- Wave 2 (Planner) → `plan` key saved; `store_plan()` creates task records in the `tasks` table
- Wave 3 (Implementer/Task Reviewer) → per-task summaries and files_created
- Wave 4 (Verifier) → `verification_results` key
- Wave 5 (Reviewer) → `review_results` key (triggers Wave 6 if CHANGES_REQUESTED)
- Wave 6 (Fixer) → fix report


## Pitfalls Index

Incident write-ups and patterns live in the references index below — load them with `skill_view(name='ai-company-workflow', file_path='references/<file>.md')`. Start with `references/common-pitfalls.md` (the skip trap) and `references/self-enforcement-pitfalls.md` (pre-flight checklist).

| Reference | Contents |
|-----------|----------|
| `references/common-pitfalls.md` | The "obvious bug fix" skip — most common failure mode |
| `references/self-enforcement-pitfalls.md` | The "simple fix" trap + pre-flight checklist |
| `references/enforcement-pitfalls.md` | Real session failure: skipping the workflow |
| `references/e2e-verification-pitfalls.md` | "Deployed ≠ verified" — E2E proof checklist |
| `references/verification-discipline-pitfalls.md` | Test before declaring complete |
| `references/large-task-timeout-patterns.md` | Splitting waves that exceed the 600s subagent timeout |
| `references/prevention-over-cleanup-and-timeout-chain.md` | Prevention over cleanup; timeout-chain alignment |
| `references/playwright-e2e-proof-patterns.md` | Browser proof tests, video recording, token injection |
| `references/qa-e2e-requirement-2026-07-09.md` | QA wave must run real HTTP E2E tests |
| `references/plugin-structure.md` | Plugin layout, tool API, install methods, wave definitions |
| `references/hermes-plugin-building.md` | Building Hermes plugins (pattern used by this plugin) |

The list below is framework-agnostic — patterns that apply to any project using the AI Company workflow.

| # | Pitfall |
|---|--------|
| 1 | `company_dispatch` Does NOT Dispatch — Must Follow with `delegate_task` |
| 2 | Plugin `company_dispatch` API Gotcha — `result` Parameter Not `action` |
| 3 | Plugin ROLE_PROMPTS ≠ Skill — Must Update Both to Change Behavior |
| 4 | Plugin Location — Never Install Inside git Repo |
| 5 | Plugin DB Schema Migration on Version Upgrade |
| 6 | Timeout ≠ Failure — Check Filesystem Before Re-dispatch |
| 7 | Subagent Silent Failure — Reports Completion but Files Not Created |
| 8 | Parallel Implementer+Verifier Race Condition — Verifier Reads Stale State |
| 9 | Planner Timeout on File-Heavy Scope Exploration |
| 10 | Patch-by-Patch Band-Aid Anti-Pattern |
| 11 | Verification Discipline — Test Before Declaring Complete |
| 12 | Git Merge Conflict Markers in Production Code |
| 13 | "Git Update" Means Pull Plugin Repo First, Not Commit Project |
| 14 | Don't Skip AI Company for Bug Fixes |
| 15 | Multi-Layer Fixes Need Multi-Layer Verification |
| 16 | "Are You Really Fixed?" — Tests Pass ≠ User Convinced |
| 17 | Commit ≠ Deploy — Forgot to Restart Services |
| 18 | Smoke Test Must Match the User's Actual Request Path |
| 19 | Missing Test Coverage — Silent Production Bugs |
| 20 | Over-Decomposition |
| 21 | External Service API Mismatch |

### Pitfall 1: `company_dispatch` Without `delegate_task` — Silent 4-Hour Delay
**Pattern**: Orchestrator calls `company_dispatch(session_id, wave_number, role='brainstormer')` and waits for results that never come.

**Root cause**: `company_dispatch` only **builds the prompt context** for a wave. It does NOT dispatch a subagent. You MUST follow `company_dispatch` with a `delegate_task` call to actually run the work.

**Correct sequence**:
```python
# Step 1: Build wave context (returns prompt + context)
ctx = company_dispatch(session_id=sid, wave_number=1, role='brainstormer', extra_context="...")
# Step 2: Actually dispatch the subagent
delegate_task(goal=ctx['prompt'], context="...", toolsets=['file', 'web'])
```

**Wrong sequence** (causes infinite wait):
```python
company_dispatch(session_id=sid, wave_number=1, role='brainstormer')
# ... nothing happens. No subagent is spawned.
```

**Pre-flight checklist for every wave**:
1. `company_dispatch()` — get the prompt
2. `delegate_task()` — spawn the subagent
3. Wait for result
4. `company_dispatch(result=...)` — record the result
5. Repeat for next wave

### Pitfall 2: Recording Wave Result — Use `result` Parameter Not `action`
**Correct call**:
```python
company_dispatch(
    session_id=sid, wave_number=1,
    result={"role": "brainstormer", "status": "completed", "summary": "...", "files_created": ["..."]}
)
```
**Wrong call**: `company_dispatch(session_id=sid, wave_number=1, action='record_result', ...)` — `action` is not a parameter.

### Pitfall 3: Plugin ROLE_PROMPTS ≠ Skill — Must Update Both to Change Behavior
The Skill file teaches the orchestrator *how to use* the workflow. The Plugin's `prompts.py` `ROLE_PROMPTS` dict is what subagents *actually receive* as their system prompt. When fixing workflow behavior, you MUST update BOTH the Skill's instructions AND the Plugin's `ROLE_PROMPTS` in `prompts.py`. Changing only the Skill has zero effect on subagent output.

### Pitfall 4: Plugin Location — Never Install Inside git Repo
NEVER install to `~/.hermes/hermes-agent/plugins/ai-company/` (inside git repo) — `hermes update` (git pull) wipes custom files there. Always use `hermes plugins install` which puts it in `~/.hermes/plugins/` (outside the source tree).

### Pitfall 5: Plugin DB Schema Migration on Version Upgrade
The plugin stores session data in `~/.hermes/ai-company-sessions.db` (SQLite). When the plugin adds new columns, the existing DB file is NOT automatically migrated.

**Detection**: `company_start` raises `OperationalError` mentioning a missing column.

**Fix**:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('$HOME/.hermes/ai-company-sessions.db')
cur = conn.cursor()
cur.execute('ALTER TABLE sessions ADD COLUMN schema_version TEXT DEFAULT \"1.0\"')
conn.commit()
print('Migration applied')
conn.close()
"
```

**Pre-flight**: check DB schema with `sqlite3 ~/.hermes/ai-company-sessions.db ".schema sessions"` and compare with `engine.py` CREATE TABLE. Apply ALTER TABLE for missing columns.

### Pitfall 6: Timeout ≠ Failure — Check Filesystem Before Re-dispatch
**Pattern**: Implementer subagent times out at 600s with 48 API calls. Orchestrator assumes failure and re-dispatches → duplicate work.

**Reality**: Implementer completed most work before the clock ran out. `git diff --stat` showed extensive changes.

**Protocol**:
1. DON'T re-dispatch immediately
2. Run `git diff --stat` to see what was changed
3. Run `git ls-files --others --exclude-standard` for new files
4. Run tests to verify what's working
5. Only re-dispatch for the REMAINING incomplete work

### Pitfall 7: Subagent Silent Failure — Reports Completion but Files Not Created
**Pattern**: Subagent returns `status=completed` with detailed summary, but filesystem shows no files were actually created.

**Prevention protocol** (mandatory after every Implementer wave):
```bash
ls -lh [expected files]
wc -l [expected files]  # Expected: 200+ lines, not 0 or 5
git status --short
git diff --stat HEAD
```

**If files are missing**: Don't proceed to Verifier wave. Re-dispatch the Implementer with explicit file creation verification. Consider using `execute_code` instead of `delegate_task` for simple file creation.

**Key insight**: `status=completed` means the subagent finished execution, NOT that it succeeded. Always verify filesystem state before recording wave results.

### Pitfall 8: Parallel Implementer+Verifier Race Condition — Verifier Reads Stale State
**Pattern**: Orchestrator dispatches implementer and verifier in parallel batch. Verifier reports "4 of 7 FAIL" even though implementer claims success. Orchestrator re-reads files and finds all fixes ARE present.

**Root cause**: Parallel subagents have no file system synchronization. Verifier reads files before implementer's writes landed.

**Decision rule**: If task B validates task A's output, they CANNOT run in parallel. Use sequential waves. Only use parallel batch when tasks are truly independent (e.g., backend + frontend that don't touch the same files).

### Pitfall 9: Planner Timeout on File-Heavy Scope Exploration
**Pattern**: Planner subagent times out at 600s when the task requires reading 15+ files to understand scope. 19 files × ~30s each = ~600s timeout.

**Prevention**: Pre-scan and pass scope as `extra_context`:
```bash
grep -rn "translatable string patterns" frontend/app/ frontend/components/ | wc -l
find frontend/app -name "page.tsx" | sort
```
Pass the pre-analyzed file list and string inventory as `extra_context`. The Planner doesn't need to READ every file — it needs the LIST of files and the COUNT of strings.

**When to skip workflow entirely**: If you already have full context of all files (you've been working on this project for hours), just implement directly.

### Pitfall 10: Patch-by-Patch Band-Aid Anti-Pattern
**Pattern**: Multiple bugs found in same flow. Orchestrator fixes them one-by-one with individual `patch` calls, restarting services between each. User gets frustrated: "always use ai company to do job" / "are you really TTD coding?"

**Correct approach when finding 3+ related bugs**:
1. STOP patching immediately
2. Use `company_start` to launch AI Company workflow
3. Pass ALL discovered root causes as `extra_context` to Brainstormer
4. Let Implementer fix everything in one wave with tests
5. Verifier verifies the entire flow end-to-end

**When to patch directly vs AI Company**:
- 1 bug, 1-2 files, trivial fix → patch directly
- 3+ bugs, 3+ files, or cascading failures → AI Company
- User explicitly says "use ai company" → always use it
- User shows frustration → switch to AI Company immediately

### Pitfall 11: Verification Discipline — Test Before Declaring Complete
**Pattern**: Orchestrator makes code changes, restarts services, sees "active" status, and declares "fixed!" without actually verifying the fix works end-to-end.

**User frustration signals**: "are you realy use e2e tested?", "are you realy TTD coding?", "always hangs up here?"

**Correct verification sequence**:
1. Resolve all merge conflicts: `grep -rn "<<<<<<" backend/`
2. Verify database schema: Check new columns exist
3. Test actual endpoints with real payloads
4. Check logs for new errors
5. Verify in browser: User should refresh and retry

**Key insight**: "Service active" ≠ "Service working". Always test the actual user action before declaring complete.

### Pitfall 12: Git Merge Conflict Markers in Production Code
**Pattern**: Unresolved `<<<<<<< Updated upstream` markers cause `SyntaxError`. Workers fail to boot.

**Detection**: `grep -rn "<<<<<<" backend/ frontend/` before committing.

**Prevention** (mandatory after every Implementer wave):
```bash
grep -rn "<<<<<<\|======\|>>>>>>" backend/ frontend/
cd backend && python -c "from app import create_app; create_app()"  # or Django equivalent
```

### Pitfall 13: "Git Update" Means Pull Plugin Repo First
**Pattern**: User says "git update ai company" → orchestrator interprets as "commit project changes" → user corrects: "I mean git pull the plugin repo."

**Pre-flight checklist before `company_start`**:
1. `cd ~/.hermes/plugins/ai-company && git pull` — ensure plugin is current
2. `cd /path/to/project && git add -A && git commit` — commit any uncommitted work
3. Then `company_start`

### Pitfall 14: Don't Skip AI Company for Bug Fixes
**Pattern**: Orchestrator sees a bug fix that touches 3+ files and decides to patch directly "because it's simple." This is the most common skip — and the most costly.

**Self-enforcement gate**: Count files BEFORE coding. If fix touches ≥3 files, workflow is mandatory. Do NOT start implementation until the Planner's plan exists.

### Pitfall 15: Multi-Layer Fixes Need Multi-Layer Verification
When a fix touches backend + frontend + tests, verify ALL three layers:
- Backend: API returns correct response
- Frontend: UI renders the new data correctly
- Tests: cover the new behavior

Checking only one layer = incomplete verification.

### Pitfall 16: "Are You Really Fixed?" — Tests Pass ≠ User Convinced
**Pattern**: Tests pass, orchestrator declares "fixed!", user retries and hits the same error or a new one.

**Root cause**: Tests cover the code path but not the user's actual request path. Or the fix is correct but not deployed.

**Fix**: Always run E2E proof through the LIVE production URL. Check the specific user-reported symptom is resolved, not just that the code "looks right."

### Pitfall 17: Commit ≠ Deploy — Forgot to Restart Services
After committing, ALWAYS rebuild and restart affected services. Verify the fix is live by making a real request. Never report "done" without confirming deployment.

In Django+Celery: restart BOTH backend and celery worker. `systemctl is-active` returns "active" even when the service crashes on first request.

### Pitfall 18: Smoke Test Must Match the User's Actual Request Path
**Pattern**: Orchestrator writes a smoke test that hits `/health` or `/api/status` → 200 OK → declares "working!" But the user's actual path (e.g., POST `/api/upload` with a 200MB file) still fails.

**Fix**: The smoke test must exercise the SAME code path the user hits. If the user reports "upload fails", test upload with a real file, not a health check.

### Pitfall 19: Missing Test Coverage — Silent Production Bugs
No test for a feature = it breaks silently in production. Every feature MUST have tests written BEFORE or ALONGSIDE implementation.

- Every API endpoint: 1 positive + 1 negative test
- Every filter/search parameter: valid, invalid, missing values
- Every form field: valid, invalid, edge cases (empty, too long, special chars)
- Every external integration: at least 1 real HTTP call test

### Pitfall 20: Over-Decomposition
**Pattern**: PM/Planner decomposes a 3-file fix into 15 micro-tasks. Each task is so small that the subagent spends more time reading context than writing code. 15 tasks × 600s timeout = 2.5 hours for a 30-minute fix.

**Fix**: Tasks should be 2-5 minutes of focused work. If a task is <1 minute, merge it with the next task. If a task is >15 minutes, split it.

### Pitfall 21: External Service API Mismatch
**Pattern**: Feature integrates with an external service (Auth, payment, etc.). The Brainstormer designs against assumed API contracts. The Implementer codes against the design. At runtime, the real API returns different fields → 500 error.

**Fix**: Pass the REAL API contracts (from actual API docs or curl output) as `extra_context` to the Brainstormer. Never let the Brainstormer guess API shapes.

## Integration Contract (`.ai-company.yaml`)

AI Company is project-agnostic. Project-specific wiring lives in ONE config file at the project root — `.ai-company.yaml` (create it from `templates/ai-company.example.yaml`, or run `scripts/setup-project.sh <project-dir>` from this skill's directory). The orchestrator MUST read it at session start and honor it throughout.

| Key | Purpose | Used by |
|-----|---------|---------|
| `project.name`, `project.prod_url` | Identity + production URL for E2E proof tests | Verifier (Wave 4), UX review, deploy |
| `tracker.file_issue_cmd` | Command template that files an issue (`{title}`, `{body_file}`, `{priority}` placeholders) | `company_create_issue` |
| `tracker.issue_ref_pattern` | Regex of valid issue IDs (e.g. `PROJ-\d+`); commits must cite real ones | Commit discipline |
| `review_gate.command` | External reviewer approval command — AI Company NEVER posts approvals itself | After Wave 5, before push |
| `deploy.command`, `deploy.health_check` | Deploy + post-deploy health check | Final deploy step |
| `notify.command` | Notification channel script (Slack/Feishu/Discord webhook) | Stop conditions, unattended mode |
| `unattended.*` | Auto-loop policy: max issues per run, auto-approval scope limits | Unattended mode |

**Companion skills (optional — the reference implementation ppt-bot-v2 uses):**
- An outer coding-cycle skill that owns issue → commit → review → push → close; AI Company runs inside its "implement + verify" step.
- An issue-creator skill defining the Markdown template for filed issues: Context / Steps to reproduce / Impact / Suggested fix / References.
- A duplication-prevention lookup table the Implementer checks before writing any new utility.
- A session-kickoff check at session start (unpushed commits, hook-bypass warnings).

**Global Hermes skills:**
- **writing-plans**: Planner (Wave 2) produces the plan that subagent-driven-development would execute. **TDD addition:** every task in the plan MUST include test requirements and TDD steps.
- **test-driven-development**: Implementer (Wave 3) follows Iron Law TDD — no code before a failing test. RED-GREEN-REFACTOR cycle.
- **requesting-code-review**: Task Reviewer (Wave 3, per-task) and Reviewer (Wave 5, whole-branch) perform staged reviews. The Reviewer's Stage 3 verifies test coverage matches the Planner's requirements.
- **subagent-driven-development**: This skill is a role-based wrapper around that pattern, with enforced TDD and Ponytail over-engineering hunts at every wave.


## Quick Start

```
1. User says: "Build [feature] using AI company workflow"
2. Hermes reads this skill + the project's `.ai-company.yaml` (if present) — the integration contract
3. ⚡ PRE-FLIGHT: `cd ~/.hermes/plugins/ai-company && git pull` — ensure plugin is current
   ⚠️ "Git update" = pull plugin repo, NOT committing project changes (pitfall #48)
4. ⚡ COMMIT: `git add -A && git commit` — commit any uncommitted project work first
5. company_start(project_path, feature_name) → returns session_id + 6-wave plan
6. Wave 1: company_dispatch(role="brainstormer") → delegate_task → design spec
   ⚠️ Brainstormer uses Ponytail questioning ladder (YAGNI first)
7. ⏸️ PAUSE — present design spec to user for approval
   ⚠️ The design spec is the contract — user MUST approve before any code
8. User approves (or requests changes → re-run Wave 1 with feedback)
9. Wave 2: company_dispatch(role="planner") → delegate_task → plan with bite-sized tasks
   ⚠️ Each task: exact file paths, code blocks, TDD steps, 2-5 min
10. Wave 3: For each task: company_dispatch_task → delegate_task (implementer) →
    company_dispatch_task(result=...) → delegate_task (task_reviewer) → APPROVED?
    ⚠️ Iron Law TDD: failing test FIRST, then minimal implementation
11. Wave 4: company_dispatch(role="verifier") → delegate_task → evidence-gated verification
    ⚠️ "Should pass" is not evidence. Paste actual command output.
12. Wave 5: company_dispatch(role="reviewer") → delegate_task → whole-branch review
    ⚠️ 4 stages: spec + quality + TDD compliance + Ponytail hunt
    ⚠️ Check fix_wave_hint in dispatch result → auto-dispatch Wave 6 if present
13. Wave 6 (if triggered): company_dispatch(role="fixer") → delegate_task → systematic debugging
14. Commit all, report to user
15. ⚡ DEPLOY: rebuild frontend + restart services + verify fix is live
16. 🔬 VERIFY: run E2E test that PROVES the exact user scenario works
    ⚠️ "are you really fixed?" = you failed this step. Need live proof, not claims.
```

**Critical gate between Wave 1 and Wave 2:** Never auto-proceed from Brainstormer to Planner. The design spec is the contract — the user MUST review and approve it before any plan is written. This is the "Docs First + TDD" principle in action.

**Critical final step — Commit ≠ Deploy:** After committing, ALWAYS rebuild and restart affected services. Verify the fix is live by making a real request. Never report "done" without confirming deployment.

## Hermes Plugin: ai-company

The `ai-company` plugin is installed at `~/.hermes/plugins/ai-company/` and enabled via `hermes plugins enable ai-company`.

### Plugin Tools (toolset: `ai_company`) — v2.1.0

| Tool | Purpose |
|------|---------|
| `company_start(project_path, feature_name)` | Creates session in SQLite, returns session_id + 6-wave plan (Brainstorm→Plan→Implement[per-task]→Verify→Review→Fix) |
| `company_dispatch(session_id, wave_number, role?, extra_context?, result?)` | Builds role-specific context with auto-injected previous wave results. Without `result`: returns prompt for dispatch. With `result`: records wave completion. When recording reviewer results with CHANGES_REQUESTED/FAIL, returns `fix_wave_hint` for Wave 6 auto-trigger. Wave 3 without `role`: returns per-task overview. |
| `company_dispatch_task(session_id, task_index, result?)` | Wave 3 per-task dispatch. Without `result`: returns implementer prompt. With `result`: records implementation, returns task_reviewer prompt. Result status: done / done_with_concerns / blocked. |
| `company_status(session_id)` | Shows completed waves, files created, per-task progress, overall status |
| `company_config(session_id, roles_yaml)` | Override role prompt templates per session (maps role names to custom prompts) |
| `company_report(session_id)` | Generate final session report with all waves, files, summaries, task progress |
| `company_list(project_path?, status?, limit?)` | List all sessions, filterable by project/status |
| `company_delete(session_id)` | Delete a session and all associated data (waves, tasks, context) |
| `company_create_issue(title, description, project_path?, ...)` | File an issue for bugs/security problems found during waves, via the project's `tracker.file_issue_cmd` from `.ai-company.yaml` (falls back to the bundled Linear helper when no config). Mandatory dedup. The `description` MUST follow: Context / Steps to reproduce / Impact / Suggested fix / References. |

### Fix Wave Auto-Trigger (v2.1.0)

When recording a reviewer result (Wave 5) with `CHANGES_REQUESTED` or `FAIL` in the summary, `company_dispatch` returns a `fix_wave_hint`:
```json
{
  "fix_wave_hint": {
    "wave": 6,
    "reason": "Reviewer requested changes — dispatch Wave 6 (Fix) to resolve issues.",
    "dispatch_args": { "session_id": "...", "wave_number": 6 }
  }
}
```
**Orchestrator should check for `fix_wave_hint`** in every dispatch result and auto-dispatch Wave 6 when present.

### Engine API Signatures (verified 2026-08-14 against v2.0.0)

```python
from engine import CompanySession, ContextStore, TaskManager

mgr = CompanySession()  # SQLite at ~/.hermes/ai-company-sessions.db
result = mgr.create_session(project_path, feature_name)  # returns dict with session_id + wave_plan
ctx = mgr.build_context_for_wave(session_id, wave_number, role, extra_context='')  # returns dict with prompt
mgr.start_wave(session_id, wave_number, role)
mgr.complete_wave(session_id, wave_number, role, summary, files_created, status='completed')
mgr.store_plan(session_id, plan_text, tasks)  # Wave 2: stores plan + creates task records
waves = mgr.get_all_waves(session_id)
report = mgr.generate_report(session_id)  # returns dict

# Per-task management (Wave 3)
task_mgr = TaskManager(conn)
task_mgr.create_task(session_id, task_index, description, files)
task_mgr.start_task(session_id, task_index)
task_mgr.complete_task(session_id, task_index, result)  # result: {summary, files_created, commit_sha}
task_mgr.complete_task_review(session_id, task_index, verdict, findings)  # APPROVED → completed, else → fixing
task_mgr.all_tasks_complete(session_id)  # bool

# Context store (auto-injected between waves)
ctx_store = ContextStore(conn)
ctx_store.save_wave_result(session_id, wave_number, role, summary, files_created)
ctx_store.get_context_for_wave(session_id, wave_number)  # all context from waves < wave_number
```

### Auto Context Passing (verified behavior)

The plugin's `ContextStore` automatically saves each wave's results and injects them into subsequent waves. Role-specific keys:
- Brainstormer → `spec` (design spec, critical for all downstream waves)
- Planner → `plan` (implementation plan with tasks)
- Verifier → `verification_results`
- Reviewer → `review_results` (determines if Wave 6 triggers)

Each wave's prompt grows as previous waves complete (approximate sizes):
- Wave 1 (Brainstormer): base prompt (~500 chars + extra_context)
- Wave 2 (Planner): base + brainstormer spec (~600 chars)
- Wave 3 (Implementer/Task Reviewer): base + spec + plan (~900 chars, per-task)
- Wave 4 (Verifier): base + all previous (~1000 chars)
- Wave 5 (Reviewer): base + all previous (~1100 chars)
- Wave 6 (Fixer): base + all previous including review results (~1200 chars)

### Distribution

- **GitHub**: `back1992/hermes-plugin-ai-company` (v2.1.0)
- **Install**: `hermes plugins install back1992/hermes-plugin-ai-company --enable`
- **Skill install**: `hermes skills install back1992/hermes-plugin-ai-company/skills/ai-company-workflow` (preview first: `hermes skills inspect <same identifier>`)
- **Location**: `~/.hermes/plugins/ai-company/` (external, survives `hermes update`)
- **Tests**: 29 tests across `tests/test_engine.py` (13), `tests/test_prompts.py` (9), `tests/test_tools.py` (7) — run with `cd ~/.hermes/plugins/ai-company && python -m pytest tests/ -v`


## Plugin Integration

The `ai-company` plugin (`~/.hermes/plugins/ai-company/`, v2.1.0) provides 9 tools that automate context passing, per-task tracking, session management, and lifecycle management. **When the plugin is loaded, prefer using its tools over manual orchestration.** See `references/plugin-structure.md` for the tool API, installation instructions, and verification steps.

## Unattended mode (auto loop)

Hermes cron can run this workflow on an always-on server without a human; AI Company is the implementation engine for any item touching 3+ files. All hooks below come from `.ai-company.yaml` — unattended rules OVERRIDE the interactive defaults:

### Auto-approval policy (replaces the Wave-1 pause)

Proceed from Wave 1 to Wave 2 without a human ONLY when ALL hold:
1. The session is tied to an existing tracker issue matching `tracker.issue_ref_pattern` — the Brainstormer's `extra_context` must include it.
2. The design spec adds NO new dependencies, NO new public API endpoints, NO DB schema changes beyond auto-generated migrations, and NO auth/security surface.
3. Estimated scope ≤ `unattended.auto_approval.max_files` files (default 8).

Otherwise: STOP the session, comment the open questions on the issue, notify via `notify.command`, and wait for a human.

### Wave receipts (mechanical, not vibes)

Every wave must leave BOTH a recorded wave result (`company_dispatch` with `result=...`) AND a named file artifact:

| Wave | Required artifact |
|------|-------------------|
| 1 Brainstormer | `docs/design/<feature>.md` |
| 2 Planner | `plans/<feature>.md` + `store_plan()` records |
| 3 Implementer | code + tests in the worktree, per-task records |
| 4 Verifier | `docs/testing/reports/<feature>-verification.md` with pasted output |
| 5 Reviewer | `docs/testing/reports/<feature>-review.md` |
| 6 Fixer | regression tests + re-run evidence |

No artifact = wave incomplete. Do NOT start wave N+1 before wave N's receipt exists (pitfall #1: `company_dispatch` alone does nothing).

### Session janitor

- ONE active AI Company session at a time (one writer). At loop start run `company_list`; if a session is active, resume it instead of starting a new one.
- Sessions older than 48h or finished: `company_report` → archive to `docs/testing/reports/` → `company_delete`.
- Wave 2 MUST persist via `store_plan()` so Wave 3 uses the per-task loop (`company_dispatch_task`); a Wave 3 without task records is a bug.

### Model separation

The implementer waves and the internal Reviewer wave (Wave 5) must run on DIFFERENT models/providers (set per dispatch). If the project defines `review_gate.command`, the FINAL approval still belongs to that external gate — AI Company never posts approvals itself.

### Stop conditions (halt, notify via `notify.command`, leave the issue open)

- 3 failed fix attempts on the same finding (Fixer 3-strike rule).
- Any mechanical gate failure (pre-commit / commit-msg / pre-push).
- Review gate rejects after a real review.
- Deploy health-check failure → redeploy the previous commit.
- Budget exhausted: max `unattended.max_issues_per_run` issues per loop run.
