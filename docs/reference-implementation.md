# Reference Implementation: ppt-bot-v2

How the [`ppt-bot-v2`](https://ppt-v2.izhixue.cc) project wires the AI Company
workflow for fully unattended operation on a prod server (since 2026-08-15).
Use this as a concrete example when writing your own `.ai-company.yaml`.

## Roles

| Role | Actor | Surface |
|------|-------|---------|
| CEO / orchestrator | Hermes (cron job `ppt-bot-v2-auto-company`, id `91e34abd137c`) | prod server |
| Coder surface | AI Company waves (this skill) or Codex CLI | git worktree `/mnt/projects/ppt-bot-v2-worktrees/auto-company` |
| Outer reviewer | claude CLI via `scripts/conductor-review.py --post` | prod server |

AI Company's Wave-3 Task Reviewer and Wave-5 Reviewer are internal quality
gates only. The final push approval is a `PUSH-APPROVAL digest=<sha256>
verdict=APPROVED` comment posted by the reviewer account (`claude-reviewer`)
on the tracker's approval log; the pre-push gate verifies both the digest and
the approver identity, so coding sessions cannot self-approve.

## Integration contract values

| Contract key | ppt-bot-v2 value |
|--------------|------------------|
| `tracker` | Built-in Django issue tracker at `https://ppt-v2.izhixue.cc`, team key `TRA`; filed via `scripts/file-tracker-issue.py` (exact-title dedup, safe number resolution) |
| `tracker.issue_ref_pattern` | `TRA-\d+` — the commit-msg hook (`scripts/check-tracker-refs.py`) validates every commit cites a real ticket against the prod tracker |
| `review_gate.command` | `python3 scripts/conductor-review.py --post` (posts the diff digest, waits for the claude reviewer verdict, notifies) |
| `deploy` | Deploy checkout `/mnt/projects/ppt-bot-v2`; service restart + health check after push |
| `notify` | `scripts/notify-workflow-event.sh` → Feishu webhook (structured verdict format) |

## Auto-fix loop

`~/.hermes/scripts/auto-fix-loop.sh` drives the queue to zero:

1. Wait for the current hermes run to finish.
2. Count open `TRA-*` issues via tracker API.
3. If open > 0 and budget remains: trigger the next `hermes cron run 91e34abd137c` (detached).
4. Repeat until the queue is empty or the run/poll budget is exhausted.

A nightly scheduled run backstops anything the loop did not finish.

## Unattended auto-approval in practice

The Wave-1 pause is skipped only when the session is tied to an existing
`TRA-N`, the spec adds no dependencies / public endpoints / schema changes /
auth surface, and scope is ≤ 8 files. Otherwise the session stops, comments
the open questions on the ticket, notifies via Feishu, and waits for a human.

## Companion repo skills

- `skills/coding-cycle/` — outer cycle: issue → implement (AI Company) → commit → review → push → close.
- `skills/issue-creator/` — issue Markdown template.
- `skills/duplication-prevention/` — shared-utility lookup table + commit-time duplication gate.
- `skills/session-kickoff/` — session-start status report (unpushed commits, bypass warnings).
