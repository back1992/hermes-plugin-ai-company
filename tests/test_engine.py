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
    assert task_mgr.all_tasks_complete(session_id) is True  # All tasks done
