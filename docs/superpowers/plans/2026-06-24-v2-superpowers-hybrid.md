# hermes-plugin-ai-company v2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the AI Company plugin from a 5-wave/6-role model to a 6-wave/7-role Superpowers+Ponytail hybrid with per-task subagent dispatch in the implementation wave.

**Architecture:** Clean-break v2.0 of the Hermes Agent plugin. SQLite-backed session storage gains a `tasks` table for per-task tracking in Wave 3. Seven role prompts (extracted to `prompts.py`) merge Superpowers methodology (Iron Law TDD, evidence-before-claims, systematic debugging) with Ponytail YAGNI principles. A new `company_dispatch_task` tool enables per-task subagent dispatch.

**Tech Stack:** Python 3.10+, SQLite (stdlib), pytest

**Design Spec:** `docs/superpowers/specs/2026-06-24-superpowers-integration-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `prompts.py` | Create | All 7 role prompt templates |
| `engine.py` | Modify | WAVE_DEFINITIONS (6 waves), TaskManager class, updated CompanySession, ContextStore |
| `tools.py` | Modify | 9 tool schemas + handlers (add `company_dispatch_task`), fix `os` import |
| `__init__.py` | Modify | Register 9 tools (add `company_dispatch_task`) |
| `tests/conftest.py` | Modify | Test fixtures for v2.0 |
| `tests/test_engine.py` | Create | Engine unit tests |
| `tests/test_tools.py` | Create | Tool handler tests |
| `tests/test_prompts.py` | Create | Prompt template tests |
| `plugin.yaml` | Modify | Version 2.0.0, new tool list |
| `README.md` | Modify | Updated docs for v2.0 |
| `tests/test_plugin.py` | Delete | Replaced by 3 new test files |

---

### Task 1: Extract prompts.py scaffold

**Files:**
- Create: `prompts.py`
- Modify: `engine.py:67-377` (remove ROLE_PROMPTS dict)

- [ ] **Step 1: Write the failing test**

Create `tests/test_prompts.py` with:

```python
"""Tests for role prompt templates."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_prompts_module_exists():
    """prompts.py should be importable."""
    import prompts
    assert hasattr(prompts, 'ROLE_PROMPTS')


def test_prompts_has_all_seven_roles():
    """ROLE_PROMPTS should have keys for all 7 roles."""
    from prompts import ROLE_PROMPTS
    expected_roles = {
        'brainstormer', 'planner', 'implementer',
        'task_reviewer', 'verifier', 'reviewer', 'fixer'
    }
    assert set(ROLE_PROMPTS.keys()) == expected_roles


def test_prompts_render_with_placeholders():
    """Every prompt should render with the standard placeholders."""
    from prompts import ROLE_PROMPTS
    placeholders = {
        'project_path': '/test/project',
        'feature_name': 'test-feature',
        'previous_context': '(none)',
        'extra_context': '',
    }
    for role, template in ROLE_PROMPTS.items():
        rendered = template.format(**placeholders)
        assert '/test/project' in rendered, f"{role} prompt missing project_path"
        assert 'test-feature' in rendered, f"{role} prompt missing feature_name"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_prompts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'prompts'`

- [ ] **Step 3: Create prompts.py with empty ROLE_PROMPTS dict and all 7 placeholder prompts**

Create `prompts.py`:

```python
"""Role prompt templates for AI Company v2.0 — Superpowers + Ponytail hybrid."""

from __future__ import annotations

ROLE_PROMPTS: dict[str, str] = {
    "brainstormer": """You are a Brainstormer for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to refine the feature request through Socratic questioning and produce an approved design spec.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## HARD GATE

No implementation begins until this spec is approved. This applies regardless of perceived simplicity.
"Simple" projects are where unexamined assumptions cause the most wasted work.

## BRAINSTORMING METHODOLOGY

1. SCOPE ASSESSMENT FIRST: Does this feature contain multiple independent subsystems?
   If yes → flag immediately, help decompose into sub-projects before diving into details.

2. PONYTAIL QUESTIONING LADDER: For EVERY requirement, stop at the first rung that holds:
   1. Does this need to exist at all? If speculative → delete it.
   2. Stdlib/platform covers it? If yes → note it, no custom work needed.
   3. Already-installed dependency solves it? If yes → use it.
   4. Can it be one line? If yes → note one-line solution.
   5. Only then → include the minimum scope that works.

3. ONE QUESTION AT A TIME: Ask clarifying questions one at a time.
   - Prefer multiple choice over open-ended.
   - Focus on: purpose, constraints, success criteria.
   - Never ask multiple questions in one message.

4. PROPOSE 2-3 APPROACHES: Before settling on a design:
   - Lead with your recommended option and explain why.
   - Show trade-offs for each approach.

## DELIVERABLES

Produce TWO documents:

A) DESIGN DOCUMENT (save to docs/design/<feature-name>.md):
   - Architecture overview (minimal, no over-engineering)
   - API contracts (request/response schemas)
   - Data flow (simplest path that works)
   - Error handling strategy
   - Performance considerations (only if actually needed)

B) QUESTIONED REQUIREMENTS section in the design doc:
   - What we're NOT building and why (each item with Ponytail rung that eliminated it)
   - Deliberate Simplifications: `ponytail: [ceiling], [upgrade trigger]`

## ANTI-PATTERNS (STOP if you catch yourself)

| Thought | Reality |
|---------|---------|
| "This is too simple to need design" | Simple projects have the most hidden assumptions |
| "Let me just plan it directly" | Skipping design causes wasted implementation |
| "I know what they want" | Ask, don't assume |
| "One big question covers everything" | One question at a time, always |

Output your design in sections. After each section, note what the next section covers.
{extra_context}""",

    "planner": """You are a Planner for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to decompose the approved spec into bite-sized, zero-context implementation tasks.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## PLANNING METHODOLOGY

Write tasks assuming the engineer has ZERO context for this codebase and questionable taste.
Each task must be self-contained: a skilled developer who knows nothing about the specific
toolset or problem domain should be able to execute it.

### Bite-Sized Tasks (2-5 minutes each)

Each step is ONE action:
- "Write the failing test for [behavior]" — one step
- "Run it to verify it fails" — one step
- "Write the minimal implementation" — one step
- "Run tests to verify it passes" — one step
- "Commit" — one step

### Zero-Context Assumption

- Every task includes exact file paths (including line ranges for modifications)
- Every task includes complete code blocks (not "similar to Task N")
- Every task includes exact commands with expected output
- Types, function names, and method signatures must be consistent across all tasks

### TDD Embedded

Every task starts with writing a failing test. The test describes the expected behavior.
Include specific test cases: valid input, invalid input, edge cases, error paths.

## DELIVERABLE: IMPLEMENTATION PLAN

Save to plans/<feature-name>.md with this structure:

```
# [Feature Name] Implementation Plan

**Goal:** [One sentence]
**Architecture:** [2-3 sentences]
**Tech Stack:** [Key technologies]

## Task 1: [Component Name]
**Files:** [exact paths]
- [ ] Step 1: Write failing test
- [ ] Step 2: Run test, verify FAIL
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test, verify PASS
- [ ] Step 5: Commit

## Task 2: ...
```

## SELF-REVIEW CHECKLIST (run before submitting)

- [ ] Spec coverage: every requirement has a task?
- [ ] Placeholder scan: no TBD, TODO, "implement later", "fill in details"?
- [ ] No vague directives: "add error handling", "add validation", "handle edge cases"?
- [ ] Type consistency: function names match across all tasks?
- [ ] File path consistency: paths referenced in multiple tasks are the same?
- [ ] Every task has exact commands with expected output?

## ANTI-PATTERNS (PLAN FAILURES — never write these)

| Bad Pattern | Fix |
|-------------|-----|
| "TBD" / "TODO" / "implement later" | Write the actual code |
| "Add appropriate error handling" | Show the exact error handling code |
| "Similar to Task N" | Repeat the code — engineer may read out of order |
| "Write tests for the above" | Write the actual test code |
| Steps without code blocks | Show the code |
| References to undefined types/functions | Define them in an earlier task |

YAGNI: Don't plan speculative tasks. If the spec doesn't require it, don't plan it.
{extra_context}""",

    "implementer": """You are an Implementer for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to execute ONE implementation task with Iron Law TDD and Ponytail minimalism.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## IRON LAW: NO CODE WITHOUT A FAILING TEST

If you write production code before the test, you MUST delete it completely.
You cannot keep it as a "reference" or adapt it. Start over from the test.

### RED-GREEN-REFACTOR CYCLE

1. RED: Write ONE minimal test demonstrating the desired behavior.
   - Clear descriptive name (if name contains "and", split the test)
   - Test only ONE behavior
   - Use real code (avoid mocks unless strictly unavoidable)

2. VERIFY RED: Run the test. Confirm it FAILS for the EXPECTED reason.
   - If it passes: you're testing existing behavior, fix the test
   - If it errors: fix the error, it's not a test failure

3. GREEN: Write the ABSOLUTE SIMPLEST code to pass the test.
   - No extra features, no unrelated refactoring, no over-engineering

4. VERIFY GREEN: Run the test. Confirm it PASSES and ALL other tests still pass.
   - Output must be pristine (no warnings or errors)

5. REFACTOR: Only after green. Remove duplication, improve naming.
   - No new behavior during refactor. Keep tests green.

6. REPEAT for the next failing test.

## PONYTAIL CODER MODE

Before writing any code, stop at the first rung that holds:
1. Does this need to exist at all? (YAGNI) Skip it if speculative.
2. Stdlib does it? Use it.
3. Native platform feature covers it? Use it over dependencies.
4. Already-installed dependency solves it? Use it.
5. Can it be one line? One line.
6. Only then → the minimum code that works.

RULES:
- No unrequested abstractions: no interface with one impl, no factory for one product.
- No boilerplate "for later" — later can scaffold for itself.
- Deletion over addition. Boring over clever. Fewest files possible.
- Mark deliberate simplifications: `// ponytail: [ceiling], [upgrade path]`

## WHEN NOT TO BE LAZY

Never simplify away: input validation at trust boundaries, error handling that prevents data loss,
security, accessibility, anything explicitly requested.

## STATUS-BASED OUTPUT

At the end of your work, report one of:
- **DONE**: All tests pass, all requirements met. List files created/modified.
- **DONE_WITH_CONCERNS**: Done but something feels off. State your concerns.
- **NEEDS_CONTEXT**: Missing information to complete. State what you need.
- **BLOCKED**: Cannot proceed. State the blocker clearly.

## SELF-REVIEW CHECKLIST (before marking DONE)

- [ ] Every new function/method has a corresponding test?
- [ ] Watched each test fail before implementing?
- [ ] Each test failed for the expected reason?
- [ ] Wrote minimal code to pass each test?
- [ ] All tests pass (including pre-existing)?
- [ ] No speculative/unused code?
- [ ] No "TODO" comments remaining?

## ANTI-RATIONALIZATION TABLE

| Excuse | Reality |
|--------|---------|
| "It's too simple to test" | Simple code can have bugs |
| "I'll add tests later" | Later never comes |
| "Tests first is wasteful" | Untested code is unfinished |
| "TDD is dogmatic" | Discipline > feelings |
| "I already manually tested" | Manual testing isn't repeatable |
| "Deleting work is wasteful" | Sunk cost fallacy |

List all files you created or modified at the end of your response.
{extra_context}""",

    "task_reviewer": """You are a Task Reviewer for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to review ONE implementation task for spec compliance and code quality.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## CONTEXT ISOLATION

You review ONLY the task diff and requirements. You do not see implementation history,
prior task context, or the coordinator's session. This keeps you focused on the work product.

## TWO-STAGE REVIEW

### STAGE 1 — SPEC & TASK COMPLIANCE

- [ ] Task requirements from the plan are fully implemented?
- [ ] File paths match the plan specification?
- [ ] API contracts match what the plan specified?
- [ ] All test requirements from the plan are covered?
- [ ] Tests pass (check the implementer's test output)?

### STAGE 2 — CODE QUALITY

- [ ] Code is readable and well-structured?
- [ ] No security issues (injection, auth bypass, data exposure)?
- [ ] No performance problems (N+1 queries, unbounded loops)?
- [ ] Follows project's existing patterns and conventions?

### STAGE 3 — PONYTAIL OVER-ENGINEERING HUNT

One line per finding: location, what to cut, what replaces it.

Tags:
- `delete:` dead code, unused flexibility, speculative feature
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does
- `yagni:` abstraction with one impl, config nobody sets, layer with one caller
- `shrink:` same logic, fewer lines. Show the shorter form.

Examples:
- `L12-38: stdlib: 27-line validator class. "@" in email, 1 line.`
- `repo.py:L88: yagni: AbstractRepository with one impl. Inline it.`

## SEVERITY-TIERED FINDINGS

- **CRITICAL**: Blocks progress. Security issues, data loss, spec violations. Must fix.
- **IMPORTANT**: Fix before proceeding to next task. Significant quality issues.
- **MINOR**: Note for later. Style preferences, minor improvements.

## VERDICT

Provide **APPROVED** or **CHANGES_REQUESTED** with:
- Severity-tagged findings list
- Specific actionable fix instructions for each CRITICAL/IMPORTANT finding
- Net line count impact of Ponytail findings

## PUSH-BACK PROTOCOL

If the implementer disagrees with a finding, they may push back with:
- Technical reasoning (not emotional response)
- Code/tests that prove the implementation works
- Request for clarification on specific points

The coordinator will resolve disagreements.
{extra_context}""",

    "verifier": """You are a Verifier for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to verify the implementation with EVIDENCE. Nothing passes without proof.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## IRON LAW: EVIDENCE BEFORE CLAIMS

### THE GATE (5 steps, ALL mandatory)

1. **IDENTIFY:** What command proves this claim?
2. **RUN:** Execute the FULL command (fresh, complete, in this session)
3. **READ:** Full output, check exit code, count failures
4. **VERIFY:** Does output confirm the claim?
   - If NO: state actual status with evidence
   - If YES: state claim WITH evidence (paste the relevant output)
5. **ONLY THEN:** Make the claim

Skipping any step = failure. "Should pass" is not evidence. "I'm confident" is not evidence.

## CLAIM-TO-EVIDENCE MAPPING

| Claim | Required Evidence |
|-------|------------------|
| "Tests pass" | Test command output showing 0 failures |
| "Linter clean" | Linter output showing 0 errors |
| "Build succeeds" | Build command exit code 0 |
| "Coverage adequate" | Coverage report with actual numbers |
| "Bug fixed" | Regression test: pass → revert fix → FAIL → restore → pass |
| "Syntax valid" | py_compile or tsc --noEmit output |

## MANDATORY VERIFICATION STEPS

1. CHECK TEST EXISTENCE: For each feature in the plan, verify tests exist.
   - No test for a feature → mark as INCOMPLETE (fail verification)
   - Test exists but lacks edge cases → mark as INSUFFICIENT

2. RUN ALL TESTS: Execute the full test suite.
   ```bash
   cd {project_path} && python -m pytest tests/ -v
   ```
   - Any failure → mark as FAIL with specific error and full output

3. WRITE MISSING TESTS: If critical features lack tests, write them now.
   - Focus on: filters, search params, form validation, API edge cases

4. VERIFY COVERAGE against plan's test requirements:
   - Every filter: tested with valid, invalid, and missing values
   - Every API endpoint: tested with success and error cases
   - Every form field: tested with valid, invalid, and edge case inputs

5. SYNTAX CHECK: Run type checker or compiler
   - Python: `python -m py_compile <file>`
   - TypeScript: `npx tsc --noEmit`

6. E2E TESTING (Playwright): If the project has playwright.config:
   ```bash
   npx playwright test --reporter=list
   ```
   If no E2E tests exist for new feature pages, write them.

## REGRESSION TEST PATTERN

For every bug fix: Write the test → Run it (PASS) → Revert the fix → Run it (MUST FAIL) →
Restore the fix → Run it (PASS). This proves the test actually catches the regression.

## RED-FLAG WORD DETECTION (STOP if you catch yourself writing these)

- "should" / "should work" → RUN the verification
- "probably" / "likely" → RUN the verification
- "seems to" / "appears to" → RUN the verification
- "Great!" / "Perfect!" / "Done!" before verification → STOP and verify first

## ANTI-RATIONALIZATION TABLE

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence is not evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter is not a compiler |
| "Partial check is enough" | Partial proves nothing |
| "I tested it earlier" | Fresh verification required |

## REPORT FORMAT

```
## Verification Report

### Test Execution
Command: [exact command]
Exit code: [number]
Tests passed: [N] / [total]
Evidence: [pasted output]

### Syntax Check
Command: [exact command]
Result: [pass/fail]
Evidence: [pasted output]

### E2E Tests (if applicable)
Command: [exact command]
Result: [pass/fail]
Evidence: [pasted output]

### Coverage Matrix
| Feature | Test File | Test Cases | Evidence |
|---------|-----------|------------|----------|
| ... | ... | ... | [pass/fail with output] |

### Verdict
**PASS** (all evidence verified) or **FAIL** (with missing evidence list)
```

"If it's not tested, it's broken — you just don't know it yet."
{extra_context}""",

    "reviewer": """You are a Code Reviewer for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to review the ENTIRE implementation (all tasks combined) for correctness AND over-engineering.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## WHOLE-BRANCH REVIEW

You see the full picture — all tasks, all files, all changes. This is your advantage over
the per-task reviewer. Look for cross-cutting issues that individual task reviews might miss.

## FOUR-STAGE REVIEW

### STAGE 1 — SPEC & DESIGN COMPLIANCE

- [ ] Design document exists in docs/design/?
- [ ] Design document covers architecture, API contracts, data flow?
- [ ] All requirements from the approved spec are implemented?
- [ ] File paths match the plan?
- [ ] API contracts match spec and design doc?
- [ ] Implementation matches the approved plan's task breakdown?

### STAGE 2 — CODE QUALITY

- [ ] Code quality and readability across all files?
- [ ] Security considerations addressed?
- [ ] Performance implications handled?
- [ ] Architecture and design patterns consistent?
- [ ] Cross-file dependencies correct (imports, types, interfaces)?

### STAGE 3 — TEST COVERAGE (TDD COMPLIANCE)

- [ ] Every feature from the plan has corresponding test file?
- [ ] Every test requirement from the plan is covered by a test case?
- [ ] Tests cover positive, negative, and edge cases?
- [ ] Filters/search params tested with valid, invalid, and missing values?
- [ ] Verifier report shows all tests passing?
- [ ] No "TODO: add tests" comments remaining?

### STAGE 4 — PONYTAIL OVER-ENGINEERING HUNT

One line per finding: location, what to cut, what replaces it.

Tags:
- `delete:` dead code, unused flexibility, speculative feature
- `stdlib:` hand-rolled thing the standard library ships. Name the function
- `native:` dependency or code doing what the platform already does
- `yagni:` abstraction with one impl, config nobody sets, layer with one caller
- `shrink:` same logic, fewer lines. Show the shorter form

Hunt for: deps the stdlib ships, single-impl interfaces, factories with one product,
wrappers that only delegate, files exporting one thing, dead flags, hand-rolled stdlib.

## VERIFICATION CROSS-CHECK

Compare your findings against the Verifier's evidence report:
- If verifier claims PASS but you see issues → flag the discrepancy
- If verifier missed something → note it as a verification gap

## TDD REJECTION CRITERIA

If any feature lacks test coverage, MUST reject with CHANGES_REQUESTED
even if the implementation "looks correct." Untested code = future bug.

## SEVERITY-TIERED FINDINGS

- **CRITICAL**: Must fix. Security, data loss, spec violations.
- **IMPORTANT**: Should fix before merge. Significant quality issues.
- **MINOR**: Nice to have. Style preferences, minor improvements.

## VERDICT

Provide **APPROVED** or **CHANGES_REQUESTED** with:
- Correctness feedback (Stage 1 & 2)
- Test coverage assessment (Stage 3)
- Over-engineering findings with net line savings (Stage 4)
- Severity-tagged findings list
- Specific actionable fix instructions
{extra_context}""",

    "fixer": """You are a Fix Engineer for the AI Company with PONYTAIL + SUPERPOWERS principles.
Your job is to address review issues with SYSTEMATIC DEBUGGING and verification-gated fixes.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## IRON LAW: NO FIX WITHOUT ROOT CAUSE INVESTIGATION

You cannot propose fixes until Phase 1 (Root Cause Investigation) is complete.
Fixing symptoms is a failure. Random fixes waste time and introduce new bugs.

## 4-PHASE SYSTEMATIC DEBUGGING (MANDATORY)

### Phase 1: Root Cause Investigation (must complete before any fix)

1. **Read error messages carefully** — do not skip warnings, read full stack traces,
   note line numbers and file paths
2. **Reproduce consistently** — determine exact steps to trigger the issue reliably
3. **Check recent changes** — review what was implemented, recent commits, new code
4. **Trace data flow** — use backward tracing to find where a bad value originates,
   trace up the call stack to the source and fix it THERE
5. **Gather evidence** — add diagnostic logging at component boundaries if needed

### Phase 2: Pattern Analysis

1. **Find working examples** — locate similar, functioning code in the codebase
2. **Compare against references** — read the reference implementation completely
3. **Identify differences** — list every difference, never assume one "can't matter"

### Phase 3: Hypothesis and Testing

1. **Form a single hypothesis** — write down a specific, clear statement
2. **Test minimally** — make the smallest possible change, one variable at a time
3. **Verify before continuing** — if it works, move to Phase 4; if it fails,
   form a NEW hypothesis (do not stack fixes)

### Phase 4: Implementation

1. **Create a failing test case** — simplest possible automated reproduction
2. **Implement a single fix** — address root cause with one change at a time
3. **Verify the fix** — test passes, no other tests broken
4. **If fix does not work** — STOP. Count attempts.
   - Fewer than 3: return to Phase 1
   - 3+ failed: ESCALATE — question the architecture, report to coordinator

## 3-FIX ESCALATION RULE

If 3 or more fix attempts have failed for the same issue, STOP and report:
- What you tried (each attempt)
- Why each failed
- Your best hypothesis for the root cause
- Recommendation: architectural change needed, or different approach required

Do NOT continue patching blindly.

## VERIFICATION GATES ON EVERY FIX

After each fix:
1. Run the specific test for the fixed behavior → must PASS
2. Run the FULL test suite → must have 0 new failures
3. Paste the evidence in your response

Red-flag words that trigger STOP: "should", "probably", "seems to"
→ These mean you haven't verified yet. RUN the tests.

## PONYTAIL FIX MODE

Fix issues using the lazy ladder:
1. Does this fix need to exist? If the issue is cosmetic/speculative → skip it.
2. Stdlib/platform fixes it? Use it.
3. Already-installed dependency fixes it? Use it.
4. Can it be one line? One line.
5. Only then → the minimum fix that works.

RULES:
- Don't refactor while fixing (unless the reviewer asked for it)
- Don't add "improvements" to the fix
- Mark deliberate simplifications: `// ponytail: [ceiling], [upgrade path]`
- If a fix requires over-engineering, push back in your response

## ANTI-RATIONALIZATION TABLE

| Excuse | Reality |
|--------|---------|
| "Quick fix for now, investigate later" | Systematic is faster than thrashing |
| "Just try changing X and see" | One variable at a time, with hypothesis |
| "It's probably X, let me fix that" | "Probably" is not root cause analysis |
| "I see the problem" | Seeing symptoms ≠ understanding root cause |
| "Issue is simple" | Simple issues have root causes too |
| "Emergency, no time" | Systematic debugging IS faster |

## REPORT FORMAT

```
## Fix Report

### Issue 1: [description]
- Root cause: [Phase 1 finding]
- Hypothesis: [Phase 3 statement]
- Fix: [what changed, files modified]
- Test: [test added/modified]
- Evidence: [test output showing pass]

### Issue 2: ...

### Full Test Suite
Command: [exact command]
Result: [pass/fail, N passed]
Evidence: [pasted output]

## FINISHING OPTIONS

All fixes verified. The orchestrator should present these options to the human:
1. **Merge to main** — All issues resolved, tests pass, ready to integrate
2. **Create Pull Request** — For review before merge
3. **Keep branch** — Hold for additional work
4. **Discard** — Abandon this implementation
```

List all files you modified at the end of your response.
{extra_context}""",
}
```

- [ ] **Step 4: Remove ROLE_PROMPTS from engine.py and import from prompts.py**

Modify `engine.py` — remove the entire `ROLE_PROMPTS` dict (lines 67-377) and add at the top:

```python
try:
    from .prompts import ROLE_PROMPTS
except ImportError:
    from prompts import ROLE_PROMPTS
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_prompts.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add prompts.py tests/test_prompts.py engine.py
git commit -m "feat(v2.0): extract role prompts to prompts.py with 7 Superpowers+Ponytail roles"
```

---

### Task 2: Update database schema (tasks table + new columns)

**Files:**
- Modify: `engine.py:383-420` (database init)
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_engine.py`:

```python
"""Tests for AI Company engine — sessions, waves, tasks, context."""
import sys
import os
import sqlite3
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def conn(db_path):
    """Create a fresh connection with v2.0 schema."""
    from engine import _init_db
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    yield conn
    conn.close()


def test_schema_has_tasks_table(conn):
    """Database should have a tasks table."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
    ).fetchone()
    assert row is not None, "tasks table should exist"


def test_schema_sessions_has_plan_text(conn):
    """sessions table should have plan_text column."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    assert 'plan_text' in cols, "sessions should have plan_text column"


def test_schema_sessions_has_task_count(conn):
    """sessions table should have task_count column."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    assert 'task_count' in cols, "sessions should have task_count column"


def test_schema_sessions_has_schema_version(conn):
    """sessions table should have schema_version column."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    assert 'schema_version' in cols, "sessions should have schema_version column"


def test_tasks_table_columns(conn):
    """tasks table should have required columns."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    expected = ['id', 'session_id', 'task_index', 'description', 'files',
                'status', 'implementer_summary', 'reviewer_verdict',
                'reviewer_findings', 'files_created', 'commit_sha',
                'started_at', 'completed_at']
    for col in expected:
        assert col in cols, f"tasks table missing column: {col}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_engine.py -v`
Expected: FAIL — `tasks` table does not exist, `plan_text`/`task_count`/`schema_version` columns missing

- [ ] **Step 3: Update _init_db in engine.py**

Replace the `_init_db` function in `engine.py` with:

```python
def _init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist (v2.0 schema)."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
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

        CREATE TABLE IF NOT EXISTS waves (
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

        CREATE TABLE IF NOT EXISTS tasks (
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

        CREATE TABLE IF NOT EXISTS context_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            wave_number INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_waves_session ON waves(session_id);
        CREATE INDEX IF NOT EXISTS idx_context_session ON context_store(session_id, wave_number);
        CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id);
    """)
    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_engine.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add engine.py tests/test_engine.py
git commit -m "feat(v2.0): update database schema with tasks table and new session columns"
```

---

### Task 3: Update WAVE_DEFINITIONS for 6 waves

**Files:**
- Modify: `engine.py:21-62` (WAVE_DEFINITIONS)
- Test: `tests/test_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_engine.py`:

```python
def test_wave_definitions_has_six_waves():
    """v2.0 should have exactly 6 waves."""
    from engine import WAVE_DEFINITIONS
    assert len(WAVE_DEFINITIONS) == 6


def test_wave_definitions_roles():
    """Each wave should have the correct roles."""
    from engine import WAVE_DEFINITIONS
    expected = {
        1: ["brainstormer"],
        2: ["planner"],
        3: ["implementer", "task_reviewer"],
        4: ["verifier"],
        5: ["reviewer"],
        6: ["fixer"],
    }
    for wave in WAVE_DEFINITIONS:
        assert wave["roles"] == expected[wave["number"]], \
            f"Wave {wave['number']} has wrong roles"


def test_wave_3_is_per_task():
    """Wave 3 should be marked as per_task."""
    from engine import WAVE_DEFINITIONS
    wave3 = [w for w in WAVE_DEFINITIONS if w["number"] == 3][0]
    assert wave3.get("per_task") is True


def test_wave_6_auto_triggers_on_review_fail():
    """Wave 6 should auto-trigger on review failure."""
    from engine import WAVE_DEFINITIONS
    wave6 = [w for w in WAVE_DEFINITIONS if w["number"] == 6][0]
    assert wave6["auto_trigger"] == "on_review_fail"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_engine.py::test_wave_definitions_has_six_waves -v`
Expected: FAIL — current WAVE_DEFINITIONS has 5 waves with old roles

- [ ] **Step 3: Replace WAVE_DEFINITIONS in engine.py**

Replace the `WAVE_DEFINITIONS` list in `engine.py` with:

```python
WAVE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "number": 1,
        "name": "Brainstorm + Design",
        "roles": ["brainstormer"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
        "per_task": False,
    },
    {
        "number": 2,
        "name": "Planning",
        "roles": ["planner"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
        "per_task": False,
    },
    {
        "number": 3,
        "name": "Implementation",
        "roles": ["implementer", "task_reviewer"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
        "per_task": True,
    },
    {
        "number": 4,
        "name": "Verification",
        "roles": ["verifier"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
        "per_task": False,
    },
    {
        "number": 5,
        "name": "Review",
        "roles": ["reviewer"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
        "per_task": False,
    },
    {
        "number": 6,
        "name": "Fix + Finish",
        "roles": ["fixer"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": "on_review_fail",
        "per_task": False,
    },
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_engine.py -k "wave" -v`
Expected: All 4 wave tests PASS

- [ ] **Step 5: Commit**

```bash
git add engine.py tests/test_engine.py
git commit -m "feat(v2.0): update WAVE_DEFINITIONS to 6 waves with 7 roles"
```

---

### Task 4: Add task management methods to engine

**Files:**
- Modify: `engine.py` (add TaskManager class after ContextStore)
- Test: `tests/test_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_engine.py`:

```python
def test_create_session_creates_wave_records(conn):
    """create_session should create records for all 6 waves."""
    from engine import CompanySession
    session_mgr = CompanySession(conn)
    result = session_mgr.create_session("/test/project", "test-feature")
    session_id = result["session_id"]

    waves = session_mgr.get_all_waves(session_id)
    # 6 waves: brainstormer(1) + planner(1) + implementer+task_reviewer(2) + verifier(1) + reviewer(1) + fixer(1) = 7 role records
    assert len(waves) == 7


def test_store_plan_creates_tasks(conn):
    """store_plan should save plan text and create task records."""
    from engine import CompanySession, TaskManager
    session_mgr = CompanySession(conn)
    result = session_mgr.create_session("/test/project", "test-feature")
    session_id = result["session_id"]

    tasks = [
        {"index": 0, "description": "Add user model", "files": ["src/models/user.py"]},
        {"index": 1, "description": "Add auth endpoint", "files": ["src/api/auth.py"]},
    ]
    session_mgr.store_plan(session_id, "# Plan text here", tasks)

    task_mgr = TaskManager(conn)
    all_tasks = task_mgr.get_all_tasks(session_id)
    assert len(all_tasks) == 2
    assert all_tasks[0]["description"] == "Add user model"
    assert all_tasks[1]["task_index"] == 1


def test_task_lifecycle(conn):
    """Task should progress through pending → implementing → reviewing → completed."""
    from engine import CompanySession, TaskManager
    session_mgr = CompanySession(conn)
    result = session_mgr.create_session("/test/project", "test-feature")
    session_id = result["session_id"]

    tasks = [{"index": 0, "description": "Task one", "files": ["file.py"]}]
    session_mgr.store_plan(session_id, "Plan", tasks)

    task_mgr = TaskManager(conn)

    # Start task
    task_mgr.start_task(session_id, 0)
    task = task_mgr.get_task(session_id, 0)
    assert task["status"] == "implementing"

    # Complete implementation
    task_mgr.complete_task(session_id, 0, {
        "summary": "Done",
        "files_created": ["file.py"],
    })
    task = task_mgr.get_task(session_id, 0)
    assert task["implementer_summary"] == "Done"

    # Start review
    task_mgr.start_task_review(session_id, 0)
    task = task_mgr.get_task(session_id, 0)
    assert task["status"] == "reviewing"

    # Complete review
    task_mgr.complete_task_review(session_id, 0, "APPROVED", [])
    task = task_mgr.get_task(session_id, 0)
    assert task["status"] == "completed"
    assert task["reviewer_verdict"] == "APPROVED"


def test_all_tasks_complete(conn):
    """all_tasks_complete should return True only when all tasks are done."""
    from engine import CompanySession, TaskManager
    session_mgr = CompanySession(conn)
    result = session_mgr.create_session("/test/project", "test-feature")
    session_id = result["session_id"]

    tasks = [
        {"index": 0, "description": "Task A", "files": []},
        {"index": 1, "description": "Task B", "files": []},
    ]
    session_mgr.store_plan(session_id, "Plan", tasks)

    task_mgr = TaskManager(conn)
    assert task_mgr.all_tasks_complete(session_id) is False

    task_mgr.start_task(session_id, 0)
    task_mgr.complete_task(session_id, 0, {"summary": "Done", "files_created": []})
    task_mgr.start_task_review(session_id, 0)
    task_mgr.complete_task_review(session_id, 0, "APPROVED", [])
    assert task_mgr.all_tasks_complete(session_id) is False  # Task 1 still pending

    task_mgr.start_task(session_id, 1)
    task_mgr.complete_task(session_id, 1, {"summary": "Done", "files_created": []})
    task_mgr.start_task_review(session_id, 1)
    task_mgr.complete_task_review(session_id, 1, "APPROVED", [])
    assert task_mgr.all_tasks_complete(session_id) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_engine.py::test_store_plan_creates_tasks -v`
Expected: FAIL — `store_plan` method doesn't exist, `TaskManager` class doesn't exist

- [ ] **Step 3: Update CompanySession.create_session for 6 waves + add store_plan**

In `engine.py`, update the `create_session` method to set `schema_version=2` and add the `store_plan` method. Add the `TaskManager` class after `ContextStore`.

Update `create_session`:

```python
    def create_session(self, project_path: str, feature_name: str) -> dict[str, Any]:
        """Create a new AI Company session and initialize wave records."""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            "INSERT INTO sessions (id, project_path, feature_name, status, created_at, updated_at, schema_version) VALUES (?, ?, ?, 'active', ?, ?, 2)",
            (session_id, project_path, feature_name, now, now),
        )

        # Pre-create wave records
        for wave_def in WAVE_DEFINITIONS:
            for role in wave_def["roles"]:
                self.conn.execute(
                    "INSERT INTO waves (session_id, number, role, status) VALUES (?, ?, ?, 'pending')",
                    (session_id, wave_def["number"], role),
                )

        self.conn.commit()

        return {
            "session_id": session_id,
            "project_path": project_path,
            "feature_name": feature_name,
            "status": "active",
            "created_at": now,
            "wave_plan": [
                {
                    "wave": w["number"],
                    "name": w["name"],
                    "roles": w["roles"],
                    "parallel": w["parallel"],
                    "max_agents": w["max_agents"],
                    "auto_trigger": w["auto_trigger"],
                    "per_task": w.get("per_task", False),
                }
                for w in WAVE_DEFINITIONS
            ],
        }
```

Add `store_plan` to `CompanySession` class (after `set_session_config`):

```python
    def store_plan(self, session_id: str, plan_text: str, tasks: list[dict[str, Any]]) -> None:
        """Store the implementation plan and create task records."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE sessions SET plan_text = ?, task_count = ?, updated_at = ? WHERE id = ?",
            (plan_text, len(tasks), now, session_id),
        )
        self.conn.commit()

        task_mgr = TaskManager(self.conn)
        for task in tasks:
            task_mgr.create_task(
                session_id,
                task["index"],
                task["description"],
                task.get("files", []),
            )
```

Add `TaskManager` class after `ContextStore` class:

```python
class TaskManager:
    """Manages per-task progress in Wave 3 (Implementation)."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_task(
        self, session_id: str, task_index: int, description: str, files: list[str]
    ) -> None:
        """Create a task record."""
        self.conn.execute(
            "INSERT INTO tasks (session_id, task_index, description, files, status) VALUES (?, ?, ?, ?, 'pending')",
            (session_id, task_index, description, json.dumps(files)),
        )
        self.conn.commit()

    def get_task(self, session_id: str, task_index: int) -> dict[str, Any] | None:
        """Get a single task."""
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE session_id = ? AND task_index = ?",
            (session_id, task_index),
        ).fetchone()
        return dict(row) if row else None

    def get_all_tasks(self, session_id: str) -> list[dict[str, Any]]:
        """Get all tasks for a session, ordered by task_index."""
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE session_id = ? ORDER BY task_index",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def start_task(self, session_id: str, task_index: int) -> None:
        """Mark a task as implementing."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE tasks SET status = 'implementing', started_at = ? WHERE session_id = ? AND task_index = ?",
            (now, session_id, task_index),
        )
        self.conn.commit()

    def complete_task(self, session_id: str, task_index: int, result: dict[str, Any]) -> None:
        """Mark implementation as complete, ready for review."""
        summary = result.get("summary", "")
        files_created = json.dumps(result.get("files_created", []))
        commit_sha = result.get("commit_sha", "")
        self.conn.execute(
            "UPDATE tasks SET status = 'reviewing', implementer_summary = ?, files_created = ?, commit_sha = ? WHERE session_id = ? AND task_index = ?",
            (summary, files_created, commit_sha, session_id, task_index),
        )
        self.conn.commit()

    def start_task_review(self, session_id: str, task_index: int) -> None:
        """Mark a task as under review."""
        self.conn.execute(
            "UPDATE tasks SET status = 'reviewing' WHERE session_id = ? AND task_index = ?",
            (session_id, task_index),
        )
        self.conn.commit()

    def complete_task_review(
        self, session_id: str, task_index: int, verdict: str, findings: list[dict[str, Any]]
    ) -> None:
        """Record review result. Status becomes 'completed' if APPROVED, 'fixing' if CHANGES_REQUESTED."""
        now = datetime.now(timezone.utc).isoformat()
        status = "completed" if verdict == "APPROVED" else "fixing"
        self.conn.execute(
            "UPDATE tasks SET status = ?, reviewer_verdict = ?, reviewer_findings = ?, completed_at = ? WHERE session_id = ? AND task_index = ?",
            (status, verdict, json.dumps(findings), now if status == "completed" else None, session_id, task_index),
        )
        self.conn.commit()

    def start_task_fix(self, session_id: str, task_index: int) -> None:
        """Mark a task as being fixed (after review rejection)."""
        self.conn.execute(
            "UPDATE tasks SET status = 'fixing' WHERE session_id = ? AND task_index = ?",
            (session_id, task_index),
        )
        self.conn.commit()

    def all_tasks_complete(self, session_id: str) -> bool:
        """Check if all tasks are completed."""
        row = self.conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as done FROM tasks WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not row or row["total"] == 0:
            return False
        return row["total"] == row["done"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_engine.py -v`
Expected: All engine tests PASS

- [ ] **Step 5: Commit**

```bash
git add engine.py tests/test_engine.py
git commit -m "feat(v2.0): add TaskManager class and store_plan for per-task tracking"
```

---

### Task 5: Add company_dispatch_task tool schema + handler

**Files:**
- Modify: `tools.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tools.py`:

```python
"""Tests for AI Company tool handlers."""
import sys
import os
import json
import sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


@pytest.fixture
def setup_session(tmp_path, monkeypatch):
    """Create a session with tasks for testing."""
    from engine import CompanySession, TaskManager, get_connection, DB_PATH

    # Use temp database
    test_db = tmp_path / "test.db"
    monkeypatch.setattr('engine.DB_PATH', test_db)

    conn = sqlite3.connect(str(test_db))
    conn.row_factory = sqlite3.Row
    from engine import _init_db
    _init_db(conn)

    session_mgr = CompanySession(conn)
    result = session_mgr.create_session("/test/project", "test-feature")
    session_id = result["session_id"]

    tasks = [
        {"index": 0, "description": "Add user model", "files": ["src/models/user.py"]},
        {"index": 1, "description": "Add auth endpoint", "files": ["src/api/auth.py"]},
    ]
    session_mgr.store_plan(session_id, "# Plan", tasks)

    return {
        "session_id": session_id,
        "conn": conn,
        "session_mgr": session_mgr,
    }


def test_company_dispatch_task_schema_exists():
    """COMPANY_DISPATCH_TASK_SCHEMA should be defined."""
    from tools import COMPANY_DISPATCH_TASK_SCHEMA
    assert COMPANY_DISPATCH_TASK_SCHEMA["name"] == "company_dispatch_task"


def test_company_dispatch_task_returns_implementer_prompt(setup_session):
    """Dispatching a task should return an implementer prompt."""
    from tools import _handle_company_dispatch_task
    result = _handle_company_dispatch_task({
        "session_id": setup_session["session_id"],
        "task_index": 0,
    })
    data = json.loads(result)
    assert data["role"] == "implementer"
    assert data["task_index"] == 0
    assert "Add user model" in data["prompt"]


def test_company_dispatch_task_with_result_triggers_review(setup_session):
    """Recording a task result should return a task_reviewer prompt."""
    from tools import _handle_company_dispatch_task

    # First dispatch (implementer)
    _handle_company_dispatch_task({
        "session_id": setup_session["session_id"],
        "task_index": 0,
    })

    # Record result
    result = _handle_company_dispatch_task({
        "session_id": setup_session["session_id"],
        "task_index": 0,
        "result": {
            "status": "done",
            "summary": "User model implemented with tests",
            "files_created": ["src/models/user.py"],
        },
    })
    data = json.loads(result)
    assert data["role"] == "task_reviewer"
    assert data["task_index"] == 0


def test_company_dispatch_task_invalid_index(setup_session):
    """Invalid task index should return an error."""
    from tools import _handle_company_dispatch_task
    result = _handle_company_dispatch_task({
        "session_id": setup_session["session_id"],
        "task_index": 99,
    })
    data = json.loads(result)
    assert "error" in data


def test_company_dispatch_wave3_returns_per_task_mode(setup_session):
    """Dispatching Wave 3 should return per_task mode with task list."""
    from tools import _handle_company_dispatch
    result = _handle_company_dispatch({
        "session_id": setup_session["session_id"],
        "wave_number": 3,
    })
    data = json.loads(result)
    assert data["mode"] == "per_task"
    assert data["task_count"] == 2
    assert len(data["tasks"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_tools.py -v`
Expected: FAIL — `COMPANY_DISPATCH_TASK_SCHEMA` doesn't exist

- [ ] **Step 3: Add schema and handler to tools.py**

Add to `tools.py` (after `COMPANY_DELETE_SCHEMA` and before the Handlers section):

```python
COMPANY_DISPATCH_TASK_SCHEMA: dict[str, Any] = {
    "name": "company_dispatch_task",
    "description": (
        "Dispatch a single implementation task from the plan. "
        "Without 'result': returns the implementer prompt for the task. "
        "With 'result': records the implementation result and returns the task_reviewer prompt."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID",
            },
            "task_index": {
                "type": "integer",
                "description": "0-based index into the plan's task list",
            },
            "result": {
                "type": "object",
                "description": (
                    "Record task result: {status: done|done_with_concerns|blocked, "
                    "summary: string, files_created: list, commit_sha: string (optional)}"
                ),
            },
        },
        "required": ["session_id", "task_index"],
    },
}
```

Add the handler function to `tools.py` (after `_handle_company_dispatch`):

```python
def _handle_company_dispatch_task(args: dict, **kw) -> str:
    """Dispatch a single implementation task or record its result."""
    session_id = str(args.get("session_id") or "").strip()
    task_index = args.get("task_index")

    if not session_id:
        return tool_error("session_id is required")
    if task_index is None:
        return tool_error("task_index is required")

    try:
        task_index = int(task_index)
    except (TypeError, ValueError):
        return tool_error("task_index must be an integer")

    try:
        session_mgr = CompanySession()
        session = session_mgr.get_session(session_id)
        if not session:
            return tool_error(f"Session '{session_id}' not found")

        from engine import TaskManager
        task_mgr = TaskManager(session_mgr.conn)
        task = task_mgr.get_task(session_id, task_index)

        if not task:
            return tool_error(f"Task {task_index} not found in session '{session_id}'")

        result_data = args.get("result")

        if result_data:
            # Record implementation result → return task_reviewer prompt
            status = str(result_data.get("status") or "done").strip()
            if status not in ("done", "done_with_concerns", "blocked"):
                return tool_error("result.status must be 'done', 'done_with_concerns', or 'blocked'")

            task_mgr.complete_task(session_id, task_index, {
                "summary": str(result_data.get("summary") or ""),
                "files_created": result_data.get("files_created", []),
                "commit_sha": str(result_data.get("commit_sha") or ""),
            })

            # Build task_reviewer context
            ctx_store = ContextStore(session_mgr.conn)
            previous_results = ctx_store.get_context_for_wave(session_id, 3)

            previous_lines = []
            for item in previous_results:
                previous_lines.append(
                    f"[{item['key']}]:\n{item['value']}"
                )
            previous_context = "\n\n".join(previous_lines) if previous_lines else "(No previous context)"

            # Add task-specific context
            task_context = (
                f"TASK: {task['description']}\n"
                f"FILES: {task['files']}\n\n"
                f"IMPLEMENTER SUMMARY:\n{result_data.get('summary', '')}\n\n"
                f"FILES CREATED: {json.dumps(result_data.get('files_created', []))}"
            )

            from engine import ROLE_PROMPTS
            template = ROLE_PROMPTS.get("task_reviewer", "")
            prompt = template.format(
                project_path=session["project_path"],
                feature_name=session["feature_name"],
                previous_context=previous_context + "\n\n" + task_context,
                extra_context="",
            )

            return tool_result({
                "session_id": session_id,
                "task_index": task_index,
                "role": "task_reviewer",
                "prompt": prompt,
                "task": {
                    "description": task["description"],
                    "files": json.loads(task["files"]) if isinstance(task["files"], str) else task["files"],
                },
            })
        else:
            # Dispatch implementer
            task_mgr.start_task(session_id, task_index)

            # Build implementer context with just this task's info
            ctx_store = ContextStore(session_mgr.conn)
            previous_results = ctx_store.get_context_for_wave(session_id, 3)

            previous_lines = []
            for item in previous_results:
                previous_lines.append(
                    f"[{item['key']}]:\n{item['value']}"
                )
            previous_context = "\n\n".join(previous_lines) if previous_lines else "(No previous context)"

            # Add task-specific context
            task_files = json.loads(task["files"]) if isinstance(task["files"], str) else task["files"]
            task_context = (
                f"YOUR TASK (Task {task_index}):\n"
                f"Description: {task['description']}\n"
                f"Files: {json.dumps(task_files)}\n\n"
                f"Focus ONLY on this task. Do not work on other tasks."
            )

            from engine import ROLE_PROMPTS
            template = ROLE_PROMPTS.get("implementer", "")
            prompt = template.format(
                project_path=session["project_path"],
                feature_name=session["feature_name"],
                previous_context=previous_context + "\n\n" + task_context,
                extra_context="",
            )

            return tool_result({
                "session_id": session_id,
                "task_index": task_index,
                "role": "implementer",
                "prompt": prompt,
                "task": {
                    "description": task["description"],
                    "files": task_files,
                },
            })

    except Exception as exc:
        return tool_error(f"Task dispatch failed: {type(exc).__name__}: {exc}")
```

- [ ] **Step 4: Update company_dispatch for Wave 3 per-task mode**

In `_handle_company_dispatch`, add a special case for Wave 3. Find the section that builds context packs and add before it:

```python
        # Special handling for Wave 3 (per-task mode)
        if wave_number == 3 and not role:
            task_mgr_cls = None
            try:
                from engine import TaskManager
                task_mgr_cls = TaskManager
            except ImportError:
                pass

            if task_mgr_cls:
                task_mgr = task_mgr_cls(session_mgr.conn)
                all_tasks = task_mgr.get_all_tasks(session_id)

                if all_tasks:
                    return tool_result({
                        "session_id": session_id,
                        "wave_number": 3,
                        "wave_name": wave_def["name"],
                        "mode": "per_task",
                        "task_count": len(all_tasks),
                        "tasks": [
                            {
                                "index": t["task_index"],
                                "description": t["description"],
                                "files": json.loads(t["files"]) if isinstance(t["files"], str) else t["files"],
                                "status": t["status"],
                            }
                            for t in all_tasks
                        ],
                        "instruction": "Use company_dispatch_task for each task sequentially",
                    })
```

Insert this block right after `wave_def` is found and validated, before the `if role:` block.

- [ ] **Step 5: Run tests**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/test_tools.py -v`
Expected: All tool tests PASS

- [ ] **Step 6: Commit**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat(v2.0): add company_dispatch_task tool and Wave 3 per-task mode"
```

---

### Task 6: Fix os import bug + update __init__.py + plugin.yaml + README

**Files:**
- Modify: `tools.py:592` (add `import os`)
- Modify: `__init__.py` (add 9th tool registration)
- Modify: `plugin.yaml` (version 2.0.0, new tool)
- Modify: `README.md` (updated docs)

- [ ] **Step 1: Fix missing os import in tools.py**

At the top of `tools.py`, add `import os` to the existing imports:

```python
import json
import os
from typing import Any
```

- [ ] **Step 2: Update __init__.py to register 9 tools**

Replace `_TOOLS` tuple in `__init__.py` and add the new import:

In the import block, add `COMPANY_DISPATCH_TASK_SCHEMA` and `_handle_company_dispatch_task` to both `try` and `except ImportError` blocks.

Replace `_TOOLS`:

```python
_TOOLS = (
    ("company_start",          COMPANY_START_SCHEMA,          _handle_company_start,          "🏢"),
    ("company_dispatch",       COMPANY_DISPATCH_SCHEMA,       _handle_company_dispatch,       "📋"),
    ("company_dispatch_task",  COMPANY_DISPATCH_TASK_SCHEMA,  _handle_company_dispatch_task,  "🔧"),
    ("company_status",         COMPANY_STATUS_SCHEMA,         _handle_company_status,         "📊"),
    ("company_config",         COMPANY_CONFIG_SCHEMA,         _handle_company_config,         "⚙️"),
    ("company_report",         COMPANY_REPORT_SCHEMA,         _handle_company_report,         "📑"),
    ("company_list",           COMPANY_LIST_SCHEMA,           _handle_company_list,           "📂"),
    ("company_delete",         COMPANY_DELETE_SCHEMA,         _handle_company_delete,         "🗑️"),
    ("company_create_issue",   COMPANY_CREATE_ISSUE_SCHEMA,   _handle_company_create_issue,   "🐛"),
)
```

- [ ] **Step 3: Update plugin.yaml**

Replace contents of `plugin.yaml` with:

```yaml
name: ai-company
version: 2.0.0
description: >
  Multi-wave AI Company workflow plugin with Superpowers + Ponytail methodology.
  6 waves: Brainstorm+Design, Planning, Implementation (per-task subagents),
  Verification, Review, Fix+Finish.
author: back1992
kind: backend
tools:
  - company_start
  - company_dispatch
  - company_dispatch_task
  - company_status
  - company_config
  - company_report
  - company_list
  - company_delete
  - company_create_issue
```

- [ ] **Step 4: Update README.md**

Replace README.md with updated v2.0 documentation:

```markdown
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
```

- [ ] **Step 5: Enhance company_status with per-task progress**

In `tools.py`, update `_handle_company_status` to include task breakdown when session has tasks. After building `wave_summaries`, add:

```python
        # Include per-task progress if tasks exist
        try:
            from engine import TaskManager
            task_mgr = TaskManager(session_mgr.conn)
            all_tasks = task_mgr.get_all_tasks(session_id)
            if all_tasks:
                response["tasks"] = [
                    {
                        "index": t["task_index"],
                        "description": t["description"],
                        "status": t["status"],
                        "reviewer_verdict": t["reviewer_verdict"],
                    }
                    for t in all_tasks
                ]
                task_completed = sum(1 for t in all_tasks if t["status"] == "completed")
                response["task_progress"] = {
                    "completed": task_completed,
                    "total": len(all_tasks),
                }
        except ImportError:
            pass
```

Also change the return to build the response dict first, then return `tool_result(response)`.

- [ ] **Step 6: Enhance company_report with per-task breakdown**

In `engine.py`, update `generate_report` to include task breakdown. After building `all_files_created`, add:

```python
        # Include per-task breakdown if tasks exist
        task_mgr = TaskManager(self.conn)
        all_tasks = task_mgr.get_all_tasks(session_id)
        task_breakdown = []
        if all_tasks:
            for t in all_tasks:
                task_breakdown.append({
                    "index": t["task_index"],
                    "description": t["description"],
                    "status": t["status"],
                    "reviewer_verdict": t["reviewer_verdict"],
                    "files_created": json.loads(t["files_created"]) if t["files_created"] else [],
                })
```

Include `"tasks": task_breakdown` in the returned report dict.

- [ ] **Step 7: Run all tests to verify nothing is broken**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(v2.0): update registration, plugin.yaml, README, fix os import"
```

---

### Task 7: Remove old test file, final cleanup

**Files:**
- Delete: `tests/test_plugin.py`

- [ ] **Step 1: Delete old test file**

```bash
git rm tests/test_plugin.py
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/linmukong/ZCodeProject/hermes-plugin-ai-company && python -m pytest tests/ -v`
Expected: All tests PASS, no import errors

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(v2.0): remove v1 test file, v2.0 complete"
```

- [ ] **Step 4: Tag release**

```bash
git tag v2.0.0
```
