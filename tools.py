"""AI Company tools — schemas and handlers (registered via plugins/ai-company)."""

from __future__ import annotations

import json
from typing import Any

from .engine import (
    CompanySession,
    ContextStore,
    WAVE_DEFINITIONS,
    get_connection,
)
from tools.registry import tool_error, tool_result


def _check_available() -> bool:
    """Plugin is always available."""
    return True


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

COMPANY_START_SCHEMA: dict[str, Any] = {
    "name": "company_start",
    "description": (
        "Initialize a new AI Company session for developing a feature. "
        "Creates a session with 5 waves: PM planning, Implementation (coder+ui in parallel), "
        "QA testing, Code Review, and Fix (auto-triggered on review failure). "
        "Returns the session_id and wave plan."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Path to the project repository (e.g., /mnt/projects/myapp)",
            },
            "feature_name": {
                "type": "string",
                "description": "Name/description of the feature to build",
            },
        },
        "required": ["project_path", "feature_name"],
    },
}

COMPANY_DISPATCH_SCHEMA: dict[str, Any] = {
    "name": "company_dispatch",
    "description": (
        "Build the context pack for a specific wave and role. "
        "Call this to get the full prompt and context before calling delegate_task. "
        "Optionally pass a 'result' to record a wave's completion with summary and files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID returned by company_start",
            },
            "wave_number": {
                "type": "integer",
                "description": "Wave number (1-5) to dispatch",
            },
            "role": {
                "type": "string",
                "description": "Specific role to dispatch within the wave (e.g., 'coder', 'qa'). Optional — if omitted, dispatches for all roles in the wave.",
            },
            "extra_context": {
                "type": "string",
                "description": "Additional context to append to the prompt",
            },
            "result": {
                "type": "object",
                "description": (
                    "Record a wave result instead of dispatching. "
                    "Contains: {role, summary, files_created (list of file paths), status (completed|failed)}"
                ),
            },
        },
        "required": ["session_id", "wave_number"],
    },
}

COMPANY_STATUS_SCHEMA: dict[str, Any] = {
    "name": "company_status",
    "description": (
        "Show the current state of an AI Company session including completed waves, "
        "files created, and progress."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID to check",
            },
        },
        "required": ["session_id"],
    },
}

COMPANY_CONFIG_SCHEMA: dict[str, Any] = {
    "name": "company_config",
    "description": (
        "Override default role prompt configurations for a session. "
        "Pass a YAML/JSON object mapping role names to custom prompt templates."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID to configure",
            },
            "roles_yaml": {
                "type": "string",
                "description": (
                    "YAML or JSON string with role overrides. "
                    "Example: {\"roles\": {\"pm\": \"Custom PM prompt...\", \"coder\": \"Custom coder prompt...\"}}"
                ),
            },
        },
        "required": ["session_id", "roles_yaml"],
    },
}

COMPANY_REPORT_SCHEMA: dict[str, Any] = {
    "name": "company_report",
    "description": (
        "Generate a comprehensive final report for an AI Company session. "
        "Includes all wave summaries, files created, and overall progress."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID to report on",
            },
        },
        "required": ["session_id"],
    },
}


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _handle_company_start(args: dict, **kw) -> str:
    """Initialize a new AI Company session."""
    project_path = str(args.get("project_path") or "").strip()
    feature_name = str(args.get("feature_name") or "").strip()

    if not project_path:
        return tool_error("project_path is required")
    if not feature_name:
        return tool_error("feature_name is required")

    try:
        session_mgr = CompanySession()
        result = session_mgr.create_session(project_path, feature_name)
        return tool_result(result)
    except Exception as exc:
        return tool_error(f"Failed to create session: {type(exc).__name__}: {exc}")


def _handle_company_dispatch(args: dict, **kw) -> str:
    """Build context for a wave or record a wave result."""
    session_id = str(args.get("session_id") or "").strip()
    wave_number = args.get("wave_number")

    if not session_id:
        return tool_error("session_id is required")
    if wave_number is None:
        return tool_error("wave_number is required")

    try:
        wave_number = int(wave_number)
    except (TypeError, ValueError):
        return tool_error("wave_number must be an integer")

    if wave_number < 1 or wave_number > 5:
        return tool_error("wave_number must be between 1 and 5")

    try:
        session_mgr = CompanySession()

        # Check session exists
        session = session_mgr.get_session(session_id)
        if not session:
            return tool_error(f"Session '{session_id}' not found")

        # If result is provided, record the wave completion
        result_data = args.get("result")
        if result_data:
            role = str(result_data.get("role") or "").strip()
            summary = str(result_data.get("summary") or "").strip()
            files_created = result_data.get("files_created", [])
            status = str(result_data.get("status") or "completed").strip()

            if not role:
                return tool_error("result.role is required")
            if status not in ("completed", "failed"):
                return tool_error("result.status must be 'completed' or 'failed'")

            if not isinstance(files_created, list):
                files_created = [str(files_created)] if files_created else []

            wave_result = session_mgr.complete_wave(
                session_id, wave_number, role, summary, files_created, status
            )

            # Check if wave 5 (fix) should be auto-triggered
            if role == "reviewer" and status == "completed":
                if "CHANGES_REQUESTED" in summary.upper() or "FAIL" in summary.upper():
                    # Mark fix wave as ready
                    pass  # Fix wave is already pending, orchestrator can check

            # If all waves done, update session status
            all_waves = session_mgr.get_all_waves(session_id)
            all_done = all(
                w["status"] in ("completed", "failed") for w in all_waves
            )
            if all_done:
                has_failures = any(w["status"] == "failed" for w in all_waves)
                session_mgr.update_session_status(
                    session_id, "completed_with_failures" if has_failures else "completed"
                )

            return tool_result({
                "action": "record_result",
                "session_id": session_id,
                "wave_number": wave_number,
                "role": role,
                "status": status,
                "wave": wave_result,
            })

        # Otherwise, build context pack for dispatch
        role = args.get("role")
        extra_context = str(args.get("extra_context") or "").strip()

        # Find the wave definition
        wave_def = None
        for w in WAVE_DEFINITIONS:
            if w["number"] == wave_number:
                wave_def = w
                break

        if not wave_def:
            return tool_error(f"Wave {wave_number} is not defined")

        if role:
            # Dispatch for a specific role
            role = str(role).strip()
            if role not in wave_def["roles"]:
                return tool_error(
                    f"Role '{role}' not in wave {wave_number}. Available: {wave_def['roles']}"
                )

            # Mark wave as started
            session_mgr.start_wave(session_id, wave_number, role)

            context_pack = session_mgr.build_context_for_wave(
                session_id, wave_number, role, extra_context
            )
            return tool_result(context_pack)
        else:
            # Dispatch for all roles in the wave
            packs = []
            for r in wave_def["roles"]:
                session_mgr.start_wave(session_id, wave_number, r)
                pack = session_mgr.build_context_for_wave(
                    session_id, wave_number, r, extra_context
                )
                packs.append(pack)

            return tool_result({
                "session_id": session_id,
                "wave_number": wave_number,
                "wave_name": wave_def["name"],
                "parallel": wave_def["parallel"],
                "max_agents": wave_def["max_agents"],
                "dispatches": packs,
            })

    except Exception as exc:
        return tool_error(f"Dispatch failed: {type(exc).__name__}: {exc}")


def _handle_company_status(args: dict, **kw) -> str:
    """Show current session state."""
    session_id = str(args.get("session_id") or "").strip()
    if not session_id:
        return tool_error("session_id is required")

    try:
        session_mgr = CompanySession()
        session = session_mgr.get_session(session_id)
        if not session:
            return tool_error(f"Session '{session_id}' not found")

        waves = session_mgr.get_all_waves(session_id)
        wave_summaries = []
        for wave in waves:
            wave_summaries.append({
                "wave": wave["number"],
                "role": wave["role"],
                "status": wave["status"],
                "summary": wave["summary"][:200] if wave["summary"] else "",
                "files_created": json.loads(wave["files_created"]) if wave["files_created"] else [],
                "started_at": wave["started_at"],
                "completed_at": wave["completed_at"],
            })

        completed = sum(1 for w in waves if w["status"] == "completed")
        pending = sum(1 for w in waves if w["status"] == "pending")
        running = sum(1 for w in waves if w["status"] == "running")
        failed = sum(1 for w in waves if w["status"] == "failed")

        return tool_result({
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
        })
    except Exception as exc:
        return tool_error(f"Status check failed: {type(exc).__name__}: {exc}")


def _handle_company_config(args: dict, **kw) -> str:
    """Override role configurations for a session."""
    session_id = str(args.get("session_id") or "").strip()
    roles_yaml = str(args.get("roles_yaml") or "").strip()

    if not session_id:
        return tool_error("session_id is required")
    if not roles_yaml:
        return tool_error("roles_yaml is required")

    try:
        session_mgr = CompanySession()
        session = session_mgr.get_session(session_id)
        if not session:
            return tool_error(f"Session '{session_id}' not found")

        # Parse the config (try JSON first, then YAML)
        config = None
        try:
            config = json.loads(roles_yaml)
        except json.JSONDecodeError:
            try:
                import yaml
                config = yaml.safe_load(roles_yaml)
            except ImportError:
                return tool_error(
                    "Failed to parse roles_yaml as JSON. YAML support requires PyYAML. "
                    "Please pass valid JSON."
                )
            except Exception as yaml_exc:
                return tool_error(f"Failed to parse roles_yaml: {yaml_exc}")

        if not isinstance(config, dict):
            return tool_error("roles_yaml must parse to a dict/object")

        # Merge with existing config
        existing = session_mgr.get_session_config(session_id)
        existing.update(config)
        session_mgr.set_session_config(session_id, existing)

        return tool_result({
            "session_id": session_id,
            "config_updated": True,
            "current_config": existing,
            "overridden_roles": list(config.get("roles", {}).keys()),
        })
    except Exception as exc:
        return tool_error(f"Config update failed: {type(exc).__name__}: {exc}")


def _handle_company_report(args: dict, **kw) -> str:
    """Generate final session report."""
    session_id = str(args.get("session_id") or "").strip()
    if not session_id:
        return tool_error("session_id is required")

    try:
        session_mgr = CompanySession()
        report = session_mgr.generate_report(session_id)

        if "error" in report:
            return tool_error(report["error"])

        return tool_result(report)
    except Exception as exc:
        return tool_error(f"Report generation failed: {type(exc).__name__}: {exc}")
