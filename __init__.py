"""AI Company orchestration plugin — bundled, auto-loaded.

Registers 7 tools into the ``ai_company`` toolset for managing multi-wave
AI development sessions. Each session tracks waves (PM, Coder, QA, Reviewer,
Fix) with persistent SQLite storage and automatic context passing between waves.

The plugin handles STATE MANAGEMENT and CONTEXT BUILDING only — it does NOT
call delegate_task itself. The orchestrator agent uses company_dispatch to get
the context pack, then calls delegate_task with that context.
"""

from __future__ import annotations

try:
    from .tools import (
        COMPANY_CONFIG_SCHEMA,
        COMPANY_CREATE_ISSUE_SCHEMA,
        COMPANY_DELETE_SCHEMA,
        COMPANY_DISPATCH_SCHEMA,
        COMPANY_LIST_SCHEMA,
        COMPANY_REPORT_SCHEMA,
        COMPANY_START_SCHEMA,
        COMPANY_STATUS_SCHEMA,
        _check_available,
        _handle_company_config,
        _handle_company_create_issue,
        _handle_company_delete,
        _handle_company_dispatch,
        _handle_company_list,
        _handle_company_report,
        _handle_company_start,
        _handle_company_status,
    )
except ImportError:
    from tools import (
        COMPANY_CONFIG_SCHEMA,
        COMPANY_CREATE_ISSUE_SCHEMA,
        COMPANY_DELETE_SCHEMA,
        COMPANY_DISPATCH_SCHEMA,
        COMPANY_LIST_SCHEMA,
        COMPANY_REPORT_SCHEMA,
        COMPANY_START_SCHEMA,
        COMPANY_STATUS_SCHEMA,
        _check_available,
        _handle_company_config,
        _handle_company_create_issue,
        _handle_company_delete,
        _handle_company_dispatch,
        _handle_company_list,
        _handle_company_report,
        _handle_company_start,
        _handle_company_status,
    )

_TOOLS = (
    ("company_start",    COMPANY_START_SCHEMA,    _handle_company_start,    "🏢"),
    ("company_dispatch", COMPANY_DISPATCH_SCHEMA, _handle_company_dispatch, "📋"),
    ("company_status",   COMPANY_STATUS_SCHEMA,   _handle_company_status,   "📊"),
    ("company_config",   COMPANY_CONFIG_SCHEMA,    _handle_company_config,   "⚙️"),
    ("company_report",   COMPANY_REPORT_SCHEMA,   _handle_company_report,   "📑"),
    ("company_list",     COMPANY_LIST_SCHEMA,     _handle_company_list,     "📂"),
    ("company_delete",   COMPANY_DELETE_SCHEMA,   _handle_company_delete,   "🗑️"),
    ("company_create_issue", COMPANY_CREATE_ISSUE_SCHEMA, _handle_company_create_issue, "🐛"),
)


def register(ctx) -> None:
    """Register all AI Company tools. Called once by the plugin loader."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="ai_company",
            schema=schema,
            handler=handler,
            check_fn=_check_available,
            emoji=emoji,
        )
