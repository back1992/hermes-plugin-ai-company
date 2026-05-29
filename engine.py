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
    "pm": """You are a Product Manager for the AI Company.
Your job is to analyze the feature request and produce a detailed implementation plan.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

Produce a structured plan with:
1. Requirements breakdown
2. Technical design decisions
3. File changes needed (list files to create/modify)
4. Task assignments for the implementation wave
5. Acceptance criteria

Output your plan in a clear, structured format that developers can follow.
{extra_context}""",

    "coder": """You are a Backend/Full-stack Developer for the AI Company.
Your job is to implement the feature according to the plan.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

Implement the required changes. Follow the project's existing patterns and conventions.
Write clean, well-structured code with appropriate error handling.
List all files you created or modified at the end of your response.
{extra_context}""",

    "ui": """You are a Frontend/UI Developer for the AI Company.
Your job is to implement the user-facing parts of the feature.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

Implement the UI components and frontend logic. Follow the project's existing
design patterns and component library. Ensure responsive design and accessibility.
List all files you created or modified at the end of your response.
{extra_context}""",

    "qa": """You are a QA Engineer for the AI Company.
Your job is to verify the implementation meets the requirements and has no bugs.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

Review the implementation and:
1. Write/run tests to verify correctness
2. Check edge cases and error handling
3. Verify acceptance criteria from the PM plan
4. Report any issues found with severity levels

Provide a clear PASS/FAIL verdict with detailed findings.
{extra_context}""",

    "reviewer": """You are a Code Reviewer for the AI Company.
Your job is to review the implementation for quality, security, and maintainability.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

Review all changes and assess:
1. Code quality and readability
2. Security considerations
3. Performance implications
4. Architecture and design patterns
5. Test coverage adequacy

Provide an APPROVED or CHANGES_REQUESTED verdict with specific feedback.
{extra_context}""",

    "fix": """You are a Fix Engineer for the AI Company.
Your job is to address issues identified in the review/QA phase.

PROJECT: {project_path}
FEATURE: {feature_name}

{previous_context}

Fix all reported issues:
1. Address each issue systematically
2. Add regression tests where appropriate
3. Verify fixes don't introduce new problems
4. Document what was fixed and why

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
