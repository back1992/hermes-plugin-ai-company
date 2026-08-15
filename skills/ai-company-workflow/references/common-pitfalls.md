# AI Company Workflow: Common Pitfalls

## The "Obvious Bug Fix" Skip (2026-06-18 lesson — most common failure mode)

The agent's strongest instinct on "obvious" 3-file bug fixes is to skip the AI Company workflow and fix directly. **This is WRONG** — the user will catch it ("are you really fixed?"), the fix gets rejected, and must be redone through AI Company anyway (with TDD, QA, review).

### Canonical Example: SSE Connection Drops

**Scenario**: Long-running generation tasks (283MB PDF = 55 min) caused SSE connection drops. Frontend showed "network error" / "任务失败" even though the task completed successfully in the background.

**Root cause was obvious**:
1. Backend had no heartbeat → Nginx `proxy_read_timeout` (600s) killed idle connections
2. Frontend SSE client had no reconnect logic → immediately showed "failed"
3. Progress page UI showed error card immediately on disconnect

**What happened without workflow**: Agent fixed all 3 files directly in 5 minutes. No tests written. User asked "are you really fixed?" → exposed that there were no tests, no QA verification, no review.

**What happened WITH workflow** (after redo):
- PM produced 701-line plan with 31 TDD test requirements
- Coder: 9 backend heartbeat tests (RED → GREEN), 126/126 API tests pass
- UI: 18 frontend SSE tests + 3 smoke tests, vitest + build succeeds
- QA: verified all 4 requirements, found 2 non-blocking bugs
- Reviewer: APPROVED with spec compliance matrix
- Bug fixes: duplicate SSEClient in check-status handler, ConnectionStatus type in 3 places
- Total: 25 minutes, but the fix was verified and production-ready

**Rule**: If you're about to edit 3+ files and thinking "this is simple, I'll just fix it directly" — **STOP**. That's the exact case where the workflow catches problems you'd miss (test gaps, edge cases, code duplication, type inconsistencies). The "5-minute quick fix" always becomes a 30-minute cycle of fix → user catches gaps → redo → deploy → verify.

### Signs You're About to Skip
- "The fix is just adding a heartbeat / reconnect logic / UI state" — still 3+ files
- "I know exactly what to change" — you might, but tests will catch what you miss
- "It'll only take 5 minutes" — the workflow takes 20-30 min but produces verified results
- "The user just wants it fixed, not a whole workflow" — the user wants it fixed RIGHT, which means tested and reviewed
