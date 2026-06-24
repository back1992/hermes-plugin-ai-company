"""Tests for AI Company engine — sessions, waves, tasks, context."""
import sys
import os
import sqlite3
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
