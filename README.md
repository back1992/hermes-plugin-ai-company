# Hermes Plugin: AI Company Workflow

An orchestration plugin for [Hermes Agent](https://hermes-agent.nousresearch.com/) that simulates a software company structure — spawning sub-agents as PM, Coder, UI Designer, QA, and Reviewer to develop features in parallel waves.

## Install

```bash
hermes plugins install back1992/hermes-plugin-ai-company --enable
```

## Tools (7)

| Tool | Description |
|------|-------------|
| `company_start` | Initialize a new AI Company session for a project/feature |
| `company_dispatch` | Build role-specific context for a wave (auto-injects previous results) |
| `company_status` | Check session progress (completed waves, files, time) |
| `company_config` | Override role prompts and wave definitions |
| `company_report` | Generate final session report |
| `company_list` | List all sessions (filterable by project, status) |
| `company_delete` | Delete a session and its associated data |

## How It Works

```
Wave 1: 🧠 PM Agent     → writes implementation plan
Wave 2: 💻 Coder + 🎨 UI → implement in parallel (max 2 agents)
Wave 3: 🧪 QA Agent     → test + find bugs
Wave 4: 📋 Reviewer     → spec compliance + code quality
Wave 5: 🔧 Fix Agent    → resolve issues (auto-triggered if review fails)
```

Each wave **automatically receives** all previous wave results in its context — no manual copying needed.

## Fix Wave Auto-Trigger

When a Reviewer wave completes with `CHANGES_REQUESTED` or `FAIL` in its summary, the dispatch result includes a `fix_wave_hint` field that tells the orchestrator to dispatch Wave 5:

```json
{
  "action": "record_result",
  "fix_wave_hint": {
    "wave": 5,
    "reason": "Reviewer requested changes",
    "dispatch_args": { "session_id": "...", "wave_number": 5 }
  }
}
```

The orchestrator should check for `fix_wave_hint` and automatically call `company_dispatch` for Wave 5.

## Session History

All sessions are persisted in SQLite at `~/.hermes/ai-company-sessions.db`, searchable across projects and sessions. Use `company_list` to browse and `company_delete` to clean up old sessions.

## License

MIT
