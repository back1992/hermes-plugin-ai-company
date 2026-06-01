"""Tests for AI Company plugin — engine and tool handlers."""
import json
import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

# Patch DB path before importing engine so tests use a temp database
_TMP_DB = None


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path):
    """Use a temporary SQLite database for each test."""
    global _TMP_DB
    _TMP_DB = tmp_path / "test-sessions.db"
    with patch("engine.DB_PATH", _TMP_DB):
        yield _TMP_DB
    _TMP_DB = None


@pytest.fixture
def session_mgr():
    """Create a fresh CompanySession for each test."""
    from engine import CompanySession
    return CompanySession()


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------

class TestCompanySession:
    def test_create_session(self, session_mgr):
        result = session_mgr.create_session("/tmp/test-project", "Add login feature")
        assert "session_id" in result
        assert result["project_path"] == "/tmp/test-project"
        assert result["feature_name"] == "Add login feature"
        assert result["status"] == "active"
        assert len(result["wave_plan"]) == 5

    def test_create_session_has_all_waves(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature X")
        sid = result["session_id"]

        waves = session_mgr.get_all_waves(sid)
        # 5 wave definitions: pm(1) + coder+ui(2) + qa(1) + reviewer(1) + fix(1) = 6 rows
        assert len(waves) == 6

        roles = [w["role"] for w in waves]
        assert "pm" in roles
        assert "coder" in roles
        assert "ui" in roles
        assert "qa" in roles
        assert "reviewer" in roles
        assert "fix" in roles

    def test_get_session(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature A")
        sid = result["session_id"]

        session = session_mgr.get_session(sid)
        assert session is not None
        assert session["id"] == sid

    def test_get_nonexistent_session(self, session_mgr):
        session = session_mgr.get_session("does-not-exist")
        assert session is None

    def test_start_wave(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature B")
        sid = result["session_id"]

        wave = session_mgr.start_wave(sid, 1, "pm")
        assert wave is not None
        assert wave["status"] == "running"
        assert wave["started_at"] is not None

    def test_complete_wave(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature C")
        sid = result["session_id"]

        session_mgr.start_wave(sid, 1, "pm")
        wave = session_mgr.complete_wave(
            sid, 1, "pm",
            "PM plan: build login page",
            ["app/login.py", "app/templates/login.html"],
            "completed",
        )
        assert wave["status"] == "completed"
        assert wave["completed_at"] is not None
        files = json.loads(wave["files_created"])
        assert "app/login.py" in files

    def test_list_sessions(self, session_mgr):
        session_mgr.create_session("/tmp/proj-a", "Feature 1")
        session_mgr.create_session("/tmp/proj-b", "Feature 2")
        session_mgr.create_session("/tmp/proj-a", "Feature 3")

        all_sessions = session_mgr.list_sessions()
        assert len(all_sessions) == 3

        # Filter by project path
        proj_a = session_mgr.list_sessions(project_path="proj-a")
        assert len(proj_a) == 2

        # Filter by status
        active = session_mgr.list_sessions(status="active")
        assert len(active) == 3

    def test_list_sessions_limit(self, session_mgr):
        for i in range(5):
            session_mgr.create_session("/tmp/proj", f"Feature {i}")

        limited = session_mgr.list_sessions(limit=3)
        assert len(limited) == 3

    def test_delete_session(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "To Delete")
        sid = result["session_id"]

        # Add some wave data
        session_mgr.start_wave(sid, 1, "pm")
        session_mgr.complete_wave(sid, 1, "pm", "Done", ["file.py"], "completed")

        # Delete
        session_mgr.delete_session(sid)

        # Verify gone
        assert session_mgr.get_session(sid) is None
        assert session_mgr.get_all_waves(sid) == []

    def test_delete_nonexistent_session(self, session_mgr):
        # Should not raise — just no rows affected
        session_mgr.delete_session("no-such-id")

    def test_update_session_status(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature D")
        sid = result["session_id"]

        session_mgr.update_session_status(sid, "completed")
        session = session_mgr.get_session(sid)
        assert session["status"] == "completed"

    def test_session_config(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature E")
        sid = result["session_id"]

        config = {"roles": {"pm": "Custom PM prompt"}}
        session_mgr.set_session_config(sid, config)
        loaded = session_mgr.get_session_config(sid)
        assert loaded["roles"]["pm"] == "Custom PM prompt"

    def test_generate_report(self, session_mgr):
        result = session_mgr.create_session("/tmp/proj", "Feature F")
        sid = result["session_id"]

        session_mgr.start_wave(sid, 1, "pm")
        session_mgr.complete_wave(sid, 1, "pm", "Plan done", ["plan.md"], "completed")

        report = session_mgr.generate_report(sid)
        assert report["session_id"] == sid
        assert report["progress"]["completed"] == 1
        assert "plan.md" in report["all_files_created"]

    def test_context_passing_between_waves(self, session_mgr):
        """Verify Wave 2 gets Wave 1 (PM) results in context."""
        result = session_mgr.create_session("/tmp/proj", "Feature G")
        sid = result["session_id"]

        # Complete Wave 1
        session_mgr.start_wave(sid, 1, "pm")
        session_mgr.complete_wave(
            sid, 1, "pm",
            "Build a REST API with endpoints: GET /users, POST /users",
            [],
            "completed",
        )

        # Build context for Wave 2
        ctx = session_mgr.build_context_for_wave(sid, 2, "coder")
        assert "REST API" in ctx["prompt"]
        assert len(ctx["context_items"]) > 0


# ---------------------------------------------------------------------------
# Tool handler tests
# ---------------------------------------------------------------------------

class TestToolHandlers:
    def test_company_start(self, session_mgr):
        from tools import _handle_company_start
        result_str = _handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Test Feature",
        })
        result = json.loads(result_str)
        assert "session_id" in result

    def test_company_start_missing_args(self):
        from tools import _handle_company_start
        result = json.loads(_handle_company_start({"project_path": ""}))
        assert "error" in result

    def test_company_dispatch_build_context(self, session_mgr):
        from tools import _handle_company_start, _handle_company_dispatch

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        # Dispatch wave 1 for pm
        result = json.loads(_handle_company_dispatch({
            "session_id": sid,
            "wave_number": 1,
            "role": "pm",
        }))
        assert "prompt" in result
        assert result["role"] == "pm"

    def test_company_dispatch_record_result(self, session_mgr):
        from tools import _handle_company_start, _handle_company_dispatch

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        # Record wave 1 result
        result = json.loads(_handle_company_dispatch({
            "session_id": sid,
            "wave_number": 1,
            "result": {
                "role": "pm",
                "summary": "Plan complete",
                "files_created": ["plan.md"],
                "status": "completed",
            },
        }))
        assert result["action"] == "record_result"
        assert result["status"] == "completed"

    def test_fix_wave_hint_on_review_failure(self, session_mgr):
        """When reviewer reports CHANGES_REQUESTED, fix_wave_hint should appear."""
        from tools import _handle_company_start, _handle_company_dispatch

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        # Record reviewer result with CHANGES_REQUESTED
        result = json.loads(_handle_company_dispatch({
            "session_id": sid,
            "wave_number": 4,
            "result": {
                "role": "reviewer",
                "summary": "CHANGES_REQUESTED: Missing error handling in API endpoints",
                "files_created": [],
                "status": "completed",
            },
        }))
        assert "fix_wave_hint" in result
        assert result["fix_wave_hint"]["wave"] == 5
        assert result["fix_wave_hint"]["dispatch_args"]["session_id"] == sid

    def test_fix_wave_hint_not_triggered_on_approval(self, session_mgr):
        """When reviewer approves, fix_wave_hint should NOT appear."""
        from tools import _handle_company_start, _handle_company_dispatch

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        result = json.loads(_handle_company_dispatch({
            "session_id": sid,
            "wave_number": 4,
            "result": {
                "role": "reviewer",
                "summary": "APPROVED: Clean implementation, good test coverage",
                "files_created": [],
                "status": "completed",
            },
        }))
        assert "fix_wave_hint" not in result

    def test_company_status(self, session_mgr):
        from tools import _handle_company_start, _handle_company_status

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        result = json.loads(_handle_company_status({"session_id": sid}))
        assert result["session_id"] == sid
        assert result["progress"]["pending"] == 6

    def test_company_list(self, session_mgr):
        from tools import _handle_company_start, _handle_company_list

        _handle_company_start({"project_path": "/tmp/a", "feature_name": "F1"})
        _handle_company_start({"project_path": "/tmp/b", "feature_name": "F2"})

        result = json.loads(_handle_company_list({}))
        assert result["total"] == 2

    def test_company_list_filter(self, session_mgr):
        from tools import _handle_company_start, _handle_company_list

        _handle_company_start({"project_path": "/tmp/alpha", "feature_name": "F1"})
        _handle_company_start({"project_path": "/tmp/beta", "feature_name": "F2"})

        result = json.loads(_handle_company_list({"project_path": "alpha"}))
        assert result["total"] == 1

    def test_company_delete(self, session_mgr):
        from tools import _handle_company_start, _handle_company_delete, _handle_company_status

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "To Delete",
        }))["session_id"]

        # Delete
        result = json.loads(_handle_company_delete({"session_id": sid}))
        assert result["action"] == "deleted"

        # Verify gone
        status_result = json.loads(_handle_company_status({"session_id": sid}))
        assert "error" in status_result

    def test_company_delete_nonexistent(self):
        from tools import _handle_company_delete
        result = json.loads(_handle_company_delete({"session_id": "no-such-id"}))
        assert "error" in result

    def test_company_config(self, session_mgr):
        from tools import _handle_company_start, _handle_company_config

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        result = json.loads(_handle_company_config({
            "session_id": sid,
            "roles_yaml": json.dumps({"roles": {"pm": "Custom prompt"}}),
        }))
        assert result["config_updated"] is True
        assert "pm" in result["overridden_roles"]

    def test_company_report(self, session_mgr):
        from tools import _handle_company_start, _handle_company_report

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        result = json.loads(_handle_company_report({"session_id": sid}))
        assert result["session_id"] == sid
        assert "waves" in result

    def test_dispatch_invalid_wave(self, session_mgr):
        from tools import _handle_company_start, _handle_company_dispatch

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        result = json.loads(_handle_company_dispatch({
            "session_id": sid,
            "wave_number": 99,
        }))
        assert "error" in result

    def test_dispatch_invalid_role(self, session_mgr):
        from tools import _handle_company_start, _handle_company_dispatch

        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/test",
            "feature_name": "Feature",
        }))["session_id"]

        result = json.loads(_handle_company_dispatch({
            "session_id": sid,
            "wave_number": 1,
            "role": "astronaut",
        }))
        assert "error" in result


# ---------------------------------------------------------------------------
# Import fallback test
# ---------------------------------------------------------------------------

class TestImportFallback:
    def test_fallback_tool_result(self):
        """Verify fallback tool_result works when tools.registry is unavailable."""
        from tools import tool_result
        result = tool_result({"key": "value"})
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_fallback_tool_error(self):
        """Verify fallback tool_error works when tools.registry is unavailable."""
        from tools import tool_error
        result = tool_error("something went wrong")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "something went wrong" in parsed["error"]


# ---------------------------------------------------------------------------
# Full lifecycle test
# ---------------------------------------------------------------------------

class TestFullLifecycle:
    """End-to-end: create session → dispatch all waves → generate report."""

    def test_full_happy_path(self, session_mgr):
        from tools import (
            _handle_company_start,
            _handle_company_dispatch,
            _handle_company_status,
            _handle_company_report,
        )

        # 1. Create session
        sid = json.loads(_handle_company_start({
            "project_path": "/tmp/myapp",
            "feature_name": "User authentication",
        }))["session_id"]

        # 2. Wave 1: PM
        pm_ctx = json.loads(_handle_company_dispatch({
            "session_id": sid, "wave_number": 1, "role": "pm",
        }))
        assert "prompt" in pm_ctx

        _handle_company_dispatch({
            "session_id": sid, "wave_number": 1,
            "result": {"role": "pm", "summary": "Build JWT auth", "files_created": ["auth.py"], "status": "completed"},
        })

        # 3. Wave 2: Coder + UI
        for role in ["coder", "ui"]:
            _handle_company_dispatch({"session_id": sid, "wave_number": 2, "role": role})
            _handle_company_dispatch({
                "session_id": sid, "wave_number": 2,
                "result": {"role": role, "summary": f"{role} done", "files_created": [f"{role}_file.py"], "status": "completed"},
            })

        # 4. Wave 3: QA
        _handle_company_dispatch({"session_id": sid, "wave_number": 3, "role": "qa"})
        _handle_company_dispatch({
            "session_id": sid, "wave_number": 3,
            "result": {"role": "qa", "summary": "PASS: All tests pass", "files_created": [], "status": "completed"},
        })

        # 5. Wave 4: Reviewer (APPROVED)
        _handle_company_dispatch({"session_id": sid, "wave_number": 4, "role": "reviewer"})
        review_result = json.loads(_handle_company_dispatch({
            "session_id": sid, "wave_number": 4,
            "result": {"role": "reviewer", "summary": "APPROVED: Clean code", "files_created": [], "status": "completed"},
        }))
        assert "fix_wave_hint" not in review_result

        # 6. Wave 5: Fix (complete without issues)
        _handle_company_dispatch({"session_id": sid, "wave_number": 5, "role": "fix"})
        _handle_company_dispatch({
            "session_id": sid, "wave_number": 5,
            "result": {"role": "fix", "summary": "No fixes needed", "files_created": [], "status": "completed"},
        })

        # 7. Check final status
        status = json.loads(_handle_company_status({"session_id": sid}))
        assert status["status"] == "completed"
        assert status["progress"]["completed"] == 6
        assert status["progress"]["pending"] == 0

        # 8. Generate report
        report = json.loads(_handle_company_report({"session_id": sid}))
        assert len(report["waves"]) == 6
        assert "auth.py" in report["all_files_created"]

    def test_company_create_issue_missing_title(self):
        from tools import _handle_company_create_issue
        result = json.loads(_handle_company_create_issue({"title": "", "description": "test"}))
        assert "error" in result

    def test_company_create_issue_missing_description(self):
        from tools import _handle_company_create_issue
        result = json.loads(_handle_company_create_issue({"title": "test", "description": ""}))
        assert "error" in result
