# Hermes Plugin: AI Company Workflow

An orchestration plugin for [Hermes Agent](https://hermes-agent.nousresearch.com/) that simulates a software company structure — spawning sub-agents as PM, Coder, UI Designer, QA, and Reviewer to develop features in parallel waves.

## Install

```bash
hermes plugins install <your-github>/hermes-plugin-ai-company --enable
```

## Tools (5)

| Tool | Description |
|------|-------------|
| `company_start` | Initialize a new AI Company session for a project/feature |
| `company_dispatch` | Build role-specific context for a wave (auto-injects previous results) |
| `company_status` | Check session progress (completed waves, files, time) |
| `company_config` | Override role prompts and wave definitions |
| `company_report` | Generate final session report |

## How It Works

```
Wave 1: 🧠 PM Agent     → writes implementation plan
Wave 2: 💻 Coder + 🎨 UI → implement in parallel (max 3 agents)
Wave 3: 🧪 QA Agent     → test + find bugs
Wave 4: 📋 Reviewer     → spec compliance + code quality
Wave 5: 🔧 Fix Agent    → resolve issues (auto-triggered if review fails)
```

Each wave **automatically receives** all previous wave results in its context — no manual copying needed.

## Session History

All sessions are persisted in SQLite at `~/.hermes/ai-company-sessions.db`, searchable across projects and sessions.

## License

MIT
