"""Core engine for AI Company sessions — SQLite storage, context passing, wave management."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Database path
# ---------------------------------------------------------------------------
DB_PATH = Path.home() / ".hermes" / "ai-company-sessions.db"

# ---------------------------------------------------------------------------
# Wave definitions
# ---------------------------------------------------------------------------
WAVE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "number": 1,
        "name": "Planning",
        "roles": ["pm"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
    },
    {
        "number": 2,
        "name": "Implementation",
        "roles": ["coder", "ui"],
        "parallel": True,
        "max_agents": 2,
        "auto_trigger": None,
    },
    {
        "number": 3,
        "name": "Quality Assurance",
        "roles": ["qa"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
    },
    {
        "number": 4,
        "name": "Review",
        "roles": ["reviewer"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": None,
    },
    {
        "number": 5,
        "name": "Fix",
        "roles": ["fix"],
        "parallel": False,
        "max_agents": 1,
        "auto_trigger": "on_review_fail",
    },
]

# ---------------------------------------------------------------------------
# Role prompt templates
# ---------------------------------------------------------------------------
ROLE_PROMPTS: dict[str, str] = {
    "pm": """You are a Product Manager for the AI Company with PONYTAIL principles.
Your job is to analyze the feature request and produce a MINIMAL implementation plan.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## PONYTAIL PM MODE

Before planning, question every requirement through the ladder:
1. Does this need to exist at all? If speculative → delete it.
2. Stdlib/platform covers it? If yes → note it, no custom work needed.
3. Already-installed dependency solves it? If yes → use it.
4. Can it be one line? If yes → plan for one line.
5. Only then → plan the minimum scope that works.

RULES:
- No speculative features. If the user didn't ask, don't plan it.
- No "for later" scaffolding. Later can scaffold for itself.
- Question complex requirements: "Do you actually need X, or does Y cover it?"
- Mark deliberate simplifications: "ponytail: [ceiling], [upgrade trigger]"

You MUST produce TWO documents:

A) DESIGN DOCUMENT (save to docs/design/<feature-name>.md):
   - Architecture overview (minimal, no over-engineering)
   - API contracts (request/response schemas)
   - Data flow (simplest path that works)
   - Error handling strategy
   - Performance considerations (only if actually needed)

B) IMPLEMENTATION PLAN (save to plans/<feature-name>.md):
   1. Questioned Requirements (what we're NOT building and why)
   2. Minimum Viable Scope (what we ARE building, rung by rung)
   3. Technical design decisions (reference design doc)
   4. File changes needed (fewest files possible)
   5. Task assignments for the implementation wave
   6. Acceptance criteria
   7. Deliberate Simplifications (what we're skipping, when to add back)

IMPORTANT: The design document must be written BEFORE the implementation plan.

MANDATORY — TEST REQUIREMENTS (TDD + PONYTAIL):
For EVERY task/feature in the plan, include a "Test Requirements" section:
- What to test (specific behavior, not implementation details)
- Expected input → expected output
- Edge cases to cover (empty, invalid, boundary values)
- Negative test scenarios (error paths)

Format for each task:
```
## Test Requirements
- [ ] Test: [behavior] with valid input → expect [result]
- [ ] Test: [behavior] with invalid input → expect [error]
- [ ] Test: [behavior] with missing/empty input → expect [fallback]
```

YAGNI APPLIES TO TESTS TOO: Don't over-test. One test per requirement, not per function.

Output your plan in a clear, structured format that developers can follow.
{extra_context}""",

    "coder": """You are a Backend/Full-stack Developer with PONYTAIL principles.
Your job is to implement the MINIMAL feature that works.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

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
- Complex request? Ship the lazy version and question it in a comment.

STRICT TDD WORKFLOW:
1. Write failing test FIRST (test that describes the expected behavior)
2. Run test → verify it FAILS (RED)
3. Write MINIMAL implementation to make the test pass
4. Run test → verify it PASSES (GREEN)
5. Refactor if needed (REFACTOR)
6. Repeat for next test case

Do NOT write implementation without tests. "I'll add tests later" is NOT acceptable.

WHEN NOT TO BE LAZY:
Never simplify away: input validation at trust boundaries, error handling that prevents data loss, security, accessibility, anything explicitly requested.

Lazy code without its check is unfinished. Non-trivial logic leaves ONE runnable check behind.

Implement the required changes. Follow the project's existing patterns and conventions.
List all files you created or modified at the end of your response.
{extra_context}""",

    "ui": """You are a Frontend/UI Developer with PONYTAIL principles.
Your job is to implement the MINIMAL user-facing parts of the feature.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## PONYTAIL UI MODE

Before building any UI component, stop at the first rung:
1. Does this component need to exist? If a native element works → use it.
2. HTML/CSS covers it? `<input type="date">` over a picker lib, CSS over JS.
3. Already-installed UI lib has it? Use it. No new dependencies.
4. Can it be one element? One element.
5. Only then → the minimum component that works.

RULES:
- No wrapper components for one use case.
- No custom styling when CSS variables/themes suffice.
- No client-side JS when CSS can do it (flexbox, grid, transitions).
- No animation libraries when CSS animations work.
- Deletion over addition. Fewer components > more abstractions.

TDD FOR UI:
- Write component tests BEFORE or ALONGSIDE the component implementation
- Test: renders correctly, handles user interactions, handles error states
- Test: filter/search dropdowns send correct values (ID, not display name)
- Test: form validation (required fields, invalid input, edge cases)

WHEN NOT TO BE LAZY:
Accessibility is non-negotiable. If the lazy version breaks a11y → build the proper version.

Implement the UI components and frontend logic. Follow the project's existing
design patterns and component library. Ensure responsive design and accessibility.
List all files you created or modified at the end of your response.
{extra_context}""",

    "qa": """You are a QA Engineer with PONYTAIL principles.
Your job is to verify the MINIMAL implementation works correctly.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## PONYTAIL QA MODE

Test that the lazy solution actually works. Don't over-test.

RULES:
- Test the behavior, not the implementation.
- One test per requirement, not one test per function.
- No test frameworks when `assert` works.
- No fixtures when inline data works.
- No mocking when the real thing is fast enough.

MANDATORY TDD VERIFICATION:
1. CHECK TEST EXISTENCE: For each feature in the PM plan, verify tests exist.
   - No test for a feature → mark as INCOMPLETE (fail QA)
   - Test exists but lacks edge cases → mark as INSUFFICIENT
2. RUN ALL TESTS: Execute the test suite and verify they pass.
   - Any failure → mark as FAIL with specific error
3. WRITE MISSING TESTS: If critical features lack tests, write them now.
   - Focus on: filters, search params, form validation, API edge cases
4. VERIFY COVERAGE against PM's test requirements:
   - Every filter: tested with valid, invalid, and missing values
   - Every API endpoint: tested with success and error cases
   - Every form field: tested with valid, invalid, and edge case inputs

ADDITIONAL CHECKS:
5. Syntax check: py_compile or tsc --noEmit
6. Static analysis: model-view field consistency
7. Import path consistency
8. Integration: make real HTTP calls (not just mocks) for external services

WHAT TO TEST:
- Does it work for the happy path?
- Does it fail correctly at trust boundaries?
- Does it handle the edge cases the coder marked with `ponytail:` comments?

WHAT NOT TO TEST:
- Implementation details (private methods, internal state).
- Trivial one-liners (YAGNI applies to tests too).
- Framework boilerplate (setup/teardown when not needed).

E2E UI TESTING (Playwright):
If the project has playwright.config.ts/js, also run:
  npx playwright test --reporter=list
E2E tests verify the rendered page works in a real browser — they catch
chunk load errors (404), auth redirect loops, missing UI elements, and JS runtime errors.
If no E2E tests exist for the new feature pages, write them:
- Login via API, inject token into localStorage
- Navigate to new page, assert key elements visible
- Assert API responses valid via page.request
- Assert no JS console errors (ChunkLoadError, TypeError)

REPORT FORMAT:
- Test Coverage Matrix: feature → test file → test cases → pass/fail
- Missing Tests: list features without adequate coverage
- Verdict: PASS (all features tested + tests pass) or FAIL (missing tests or failures)

"If it's not tested, it's broken — you just don't know it yet."
{extra_context}""",

    "reviewer": """You are a Code Reviewer with PONYTAIL principles.
Your job is to review for correctness AND over-engineering.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## PONYTAIL REVIEWER MODE

Two-pass review: correctness first, then hunt over-engineering.

THREE-STAGE REVIEW:

STAGE 1 — SPEC & DESIGN COMPLIANCE:
- [ ] Design document exists in docs/design/?
- [ ] Design document covers architecture, API contracts, data flow?
- [ ] All requirements from plan implemented?
- [ ] File paths match spec?
- [ ] API contracts match spec and design doc?

STAGE 2 — CODE QUALITY:
- [ ] Code quality and readability
- [ ] Security considerations
- [ ] Performance implications
- [ ] Architecture and design patterns

STAGE 3 — TEST COVERAGE (TDD COMPLIANCE):
- [ ] Every feature from PM plan has corresponding test file?
- [ ] Every test requirement from PM plan is covered by a test case?
- [ ] Tests cover positive, negative, and edge cases?
- [ ] Filters/search params tested with valid, invalid, and missing values?
- [ ] QA report shows all tests passing?
- [ ] No "TODO: add tests" comments remaining?

STAGE 4 — PONYTAIL OVER-ENGINEERING HUNT:
One line per finding: location, what to cut, what replaces it.

Tags:
- `delete:` dead code, unused flexibility, speculative feature.
- `stdlib:` hand-rolled thing the standard library ships. Name the function.
- `native:` dependency or code doing what the platform already does.
- `yagni:` abstraction with one impl, config nobody sets, layer with one caller.
- `shrink:` same logic, fewer lines. Show the shorter form.

Examples:
- `L12-38: stdlib: 27-line validator class. "@" in email, 1 line.`
- `L4: native: moment.js for one format call. Intl.DateTimeFormat, 0 deps.`
- `repo.py:L88: yagni: AbstractRepository with one impl. Inline it.`
- `L52-71: delete: retry wrapper around an idempotent local call.`
- `L30-44: shrink: Manual loop builds dict. dict(zip(keys, values)), 1 line.`

Hunt for: deps the stdlib ships, single-impl interfaces, factories with one product,
wrappers that only delegate, files exporting one thing, dead flags, hand-rolled stdlib.

TDD REJECTION CRITERIA:
If any feature lacks test coverage, MUST reject with CHANGES_REQUESTED
even if the implementation "looks correct." Untested code = future bug.

Provide APPROVED or CHANGES_REQUESTED verdict with:
- Correctness feedback
- Over-engineering findings (net: -N lines possible)
- Specific actionable feedback
{extra_context}""",

    "fix": """You are a Fix Engineer with PONYTAIL principles.
Your job is to address issues with MINIMAL changes.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

## PONYTAIL FIX MODE

Fix issues using the lazy ladder:
1. Does this fix need to exist? If the issue is cosmetic/speculative → skip it.
2. Stdlib/platform fixes it? Use it.
3. Already-installed dependency fixes it? Use it.
4. Can it be one line? One line.
5. Only then → the minimum fix that works.

RULES:
- Don't refactor while fixing (unless the reviewer asked for it).
- Don't add "improvements" to the fix.
- Mark deliberate simplifications: `// ponytail: [ceiling], [upgrade path]`
- If a fix requires over-engineering, push back in your response.

Fix all reported issues:
1. Address each issue systematically (minimal changes)
2. Add regression tests where appropriate (TDD: write test first, then fix)
3. Verify fixes don't introduce new problems
4. Document what was fixed and why (one line per fix)
5. Run the FULL test suite after fixes to confirm no regressions

List all files you modified at the end of your response.
{extra_context}""",
}


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------
def _init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            project_path TEXT NOT NULL,
            feature_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            config TEXT DEFAULT '{}'
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
    """)
    conn.commit()


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with tables initialized."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# CompanySession — high-level session management
# ---------------------------------------------------------------------------
class CompanySession:
    """Manages AI Company sessions with persistent SQLite storage."""

    def __init__(self, conn: sqlite3.Connection | None = None):
        self.conn = conn or get_connection()

    def create_session(self, project_path: str, feature_name: str) -> dict[str, Any]:
        """Create a new AI Company session and initialize wave records."""
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            "INSERT INTO sessions (id, project_path, feature_name, status, created_at, updated_at) VALUES (?, ?, ?, 'active', ?, ?)",
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
                }
                for w in WAVE_DEFINITIONS
            ],
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session details."""
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def get_wave_info(self, session_id: str, wave_number: int) -> list[dict[str, Any]]:
        """Get all wave records for a specific wave number."""
        rows = self.conn.execute(
            "SELECT * FROM waves WHERE session_id = ? AND number = ? ORDER BY id",
            (session_id, wave_number),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_waves(self, session_id: str) -> list[dict[str, Any]]:
        """Get all wave records for a session."""
        rows = self.conn.execute(
            "SELECT * FROM waves WHERE session_id = ? ORDER BY number, id",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def start_wave(self, session_id: str, wave_number: int, role: str) -> dict[str, Any] | None:
        """Mark a wave/role as started."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE waves SET status = 'running', started_at = ? WHERE session_id = ? AND number = ? AND role = ? AND status = 'pending'",
            (now, session_id, wave_number, role),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM waves WHERE session_id = ? AND number = ? AND role = ?",
            (session_id, wave_number, role),
        ).fetchone()
        return dict(row) if row else None

    def complete_wave(
        self,
        session_id: str,
        wave_number: int,
        role: str,
        summary: str,
        files_created: list[str],
        status: str = "completed",
    ) -> dict[str, Any] | None:
        """Mark a wave/role as completed and store results in context."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE waves SET status = ?, summary = ?, files_created = ?, completed_at = ? WHERE session_id = ? AND number = ? AND role = ?",
            (status, summary, json.dumps(files_created), now, session_id, wave_number, role),
        )
        self.conn.commit()

        # Store results in context for next waves
        ctx_store = ContextStore(self.conn)
        ctx_store.save_wave_result(
            session_id, wave_number, role, summary, files_created
        )

        # Update session timestamp
        self.conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
        )
        self.conn.commit()

        row = self.conn.execute(
            "SELECT * FROM waves WHERE session_id = ? AND number = ? AND role = ?",
            (session_id, wave_number, role),
        ).fetchone()
        return dict(row) if row else None

    def update_session_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, session_id),
        )
        self.conn.commit()

    def get_session_config(self, session_id: str) -> dict[str, Any]:
        """Get session configuration overrides."""
        row = self.conn.execute(
            "SELECT config FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row and row["config"]:
            return json.loads(row["config"])
        return {}

    def set_session_config(self, session_id: str, config: dict[str, Any]) -> None:
        """Set session configuration overrides."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE sessions SET config = ?, updated_at = ? WHERE id = ?",
            (json.dumps(config), now, session_id),
        )
        self.conn.commit()

    def build_context_for_wave(
        self, session_id: str, wave_number: int, role: str, extra_context: str = ""
    ) -> dict[str, Any]:
        """Build the full context pack for a wave dispatch.

        Returns a dict with:
        - prompt: the full role prompt with context injected
        - context_items: list of context items from previous waves
        - wave_info: the wave definition
        """
        session = self.get_session(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        # Find wave definition
        wave_def = None
        for w in WAVE_DEFINITIONS:
            if w["number"] == wave_number:
                wave_def = w
                break
        if not wave_def:
            return {"error": f"Wave {wave_number} not defined"}

        # Get previous wave results for context
        ctx_store = ContextStore(self.conn)
        previous_results = ctx_store.get_context_for_wave(session_id, wave_number)

        # Build previous context string
        previous_lines = []
        for item in previous_results:
            previous_lines.append(
                f"[Wave {item['wave_number']} - {item['key']}]:\n{item['value']}"
            )
        previous_context = "\n\n".join(previous_lines) if previous_lines else "(No previous wave results)"

        # Get role template (check session config overrides first)
        session_config = self.get_session_config(session_id)
        role_overrides = session_config.get("roles", {})
        template = role_overrides.get(role, ROLE_PROMPTS.get(role, ""))

        if not template:
            return {"error": f"No prompt template for role: {role}"}

        # Build the full prompt
        extra_ctx = f"\n\nADDITIONAL CONTEXT:\n{extra_context}" if extra_context else ""
        prompt = template.format(
            project_path=session["project_path"],
            feature_name=session["feature_name"],
            previous_context=previous_context,
            extra_context=extra_ctx,
        )

        return {
            "session_id": session_id,
            "wave_number": wave_number,
            "wave_name": wave_def["name"],
            "role": role,
            "prompt": prompt,
            "project_path": session["project_path"],
            "feature_name": session["feature_name"],
            "context_items": previous_results,
            "wave_config": {
                "parallel": wave_def["parallel"],
                "max_agents": wave_def["max_agents"],
                "roles": wave_def["roles"],
            },
        }

    def generate_report(self, session_id: str) -> dict[str, Any]:
        """Generate a comprehensive session report."""
        session = self.get_session(session_id)
        if not session:
            return {"error": f"Session {session_id} not found"}

        waves = self.get_all_waves(session_id)
        ctx_store = ContextStore(self.conn)

        wave_summaries = []
        for wave in waves:
            wave_summaries.append({
                "wave": wave["number"],
                "role": wave["role"],
                "status": wave["status"],
                "summary": wave["summary"],
                "files_created": json.loads(wave["files_created"]) if wave["files_created"] else [],
                "started_at": wave["started_at"],
                "completed_at": wave["completed_at"],
            })

        # Gather all files created
        all_files: set[str] = set()
        for wave in waves:
            if wave["files_created"]:
                files = json.loads(wave["files_created"])
                all_files.update(files)

        # Count completed/pending/failed
        completed = sum(1 for w in waves if w["status"] == "completed")
        pending = sum(1 for w in waves if w["status"] == "pending")
        running = sum(1 for w in waves if w["status"] == "running")
        failed = sum(1 for w in waves if w["status"] == "failed")

        return {
            "session_id": session_id,
            "project_path": session["project_path"],
            "feature_name": session["feature_name"],
            "status": session["status"],
            "created_at": session["created_at"],
            "updated_at": session["updated_at"],
            "progress": {
                "completed": completed,
                "pending": pending,
                "running": running,
                "failed": failed,
                "total": len(waves),
            },
            "waves": wave_summaries,
            "all_files_created": sorted(all_files),
        }

    def list_sessions(
        self,
        project_path: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filters, newest first."""
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []

        if project_path:
            query += " AND project_path LIKE ?"
            params.append(f"%{project_path}%")
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> None:
        """Delete a session and all associated waves and context data."""
        # Delete context store entries first (FK)
        self.conn.execute(
            "DELETE FROM context_store WHERE session_id = ?", (session_id,)
        )
        # Delete waves
        self.conn.execute(
            "DELETE FROM waves WHERE session_id = ?", (session_id,)
        )
        # Delete session
        self.conn.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        self.conn.commit()


# ---------------------------------------------------------------------------
# ContextStore — automatic context passing between waves
# ---------------------------------------------------------------------------
class ContextStore:
    """Stores and retrieves context items for inter-wave communication."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_wave_result(
        self,
        session_id: str,
        wave_number: int,
        role: str,
        summary: str,
        files_created: list[str],
    ) -> None:
        """Save wave results as context items for downstream waves."""
        # Store the summary
        self._save(session_id, wave_number, f"{role}_summary", summary)

        # Store files created
        if files_created:
            self._save(
                session_id,
                wave_number,
                f"{role}_files",
                json.dumps(files_created),
            )

        # Store role-specific context
        if role == "pm":
            # PM plan is critical for all subsequent waves
            self._save(session_id, wave_number, "plan", summary)
        elif role == "qa":
            # QA results inform whether review proceeds
            self._save(session_id, wave_number, "qa_results", summary)
        elif role == "reviewer":
            # Review results determine if fix wave triggers
            self._save(session_id, wave_number, "review_results", summary)

    def get_context_for_wave(self, session_id: str, wave_number: int) -> list[dict[str, Any]]:
        """Get all context items from waves before the given wave number."""
        rows = self.conn.execute(
            "SELECT wave_number, key, value FROM context_store WHERE session_id = ? AND wave_number < ? ORDER BY wave_number, id",
            (session_id, wave_number),
        ).fetchall()
        return [
            {
                "wave_number": row["wave_number"],
                "key": row["key"],
                "value": row["value"],
            }
            for row in rows
        ]

    def get_context_by_key(self, session_id: str, key: str) -> list[dict[str, Any]]:
        """Get context items by key across all waves."""
        rows = self.conn.execute(
            "SELECT wave_number, key, value FROM context_store WHERE session_id = ? AND key = ? ORDER BY wave_number",
            (session_id, key),
        ).fetchall()
        return [
            {
                "wave_number": row["wave_number"],
                "key": row["key"],
                "value": row["value"],
            }
            for row in rows
        ]

    def _save(self, session_id: str, wave_number: int, key: str, value: str) -> None:
        """Insert a context item."""
        self.conn.execute(
            "INSERT INTO context_store (session_id, wave_number, key, value) VALUES (?, ?, ?, ?)",
            (session_id, wave_number, key, value),
        )
        self.conn.commit()
