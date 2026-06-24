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
