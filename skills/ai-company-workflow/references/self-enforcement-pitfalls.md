# Self-Enforcement Pitfalls

## The "Simple Fix" Trap

### Incident (2026-06-18, the production service SSE Resilience)

**Scenario:** User sent a screenshot showing a long-running generation task stuck at 30% with "network error" / "任务失败". Investigation revealed:
- Root cause: SSE connection drops during long-running tasks (30-60 min) due to Nginx `proxy_read_timeout=600s` killing idle connections
- Fix required 3 files: `backend/app/api/status.py` (heartbeat), `frontend/lib/sse.ts` (reconnect), `frontend/app/progress/[task_id]/page.tsx` (UI)

**What went wrong:** Agent identified the 3 files, then immediately started editing them directly — skipping the AI Company workflow entirely. No PM plan, no TDD tests, no QA, no review.

**User caught it:** *"are you realy use ai company workflow to these task? this feature is realy tested?"*

**Consequence:** Had to `git checkout` all 3 files to revert, then run the full workflow:
1. PM produced a 701-line plan with 31 specific TDD test requirements
2. Coder + UI implemented in parallel with strict RED→GREEN TDD
3. QA found 2 bugs the direct approach missed:
   - `handleCheckStatus` created duplicate SSEClient without disconnecting previous
   - `ConnectionStatus` type defined in 3 different files
4. Reviewer APPROVED with architectural feedback
5. Final result: 147 tests (126 backend + 21 frontend), all passing

**Lesson:** The "quick fix" would have shipped with 2 latent bugs and zero test coverage. The workflow overhead (~30 min) was less than the cost of the bugs it prevented.

### Pre-Flight Checklist (Run Before Every Fix)

```
□ How many files will this change?
  → If ≥3: AI Company workflow mandatory
  → If <3: Direct fix OK, but still write tests

□ Do I need tests for this?
  → If yes: AI Company workflow (TDD is mandatory in the workflow)
  → Even for 1-2 file changes, write tests

□ Will this affect production behavior?
  → If yes: QA + Review needed → use workflow
  → If no (dev-only, docs, etc.): Direct OK

□ Am I tempted to skip the workflow because it "seems simple"?
  → If yes: STOP. That's the trap. Count files again. Use workflow.
```

### Common "Seems Simple, Isn't" Patterns

| Symptom | Files Typically Touched | Workflow? |
|---------|------------------------|-----------|
| SSE/WebSocket timeout | backend handler + frontend client + UI indicator + tests | ✅ Yes |
| Nginx config change | nginx conf + app code + tests | ✅ Yes |
| Auth flow change | backend auth + frontend auth + middleware + tests | ✅ Yes |
| CSS/style fix | 1-2 component files | ❌ Direct OK |
| Typo in docs | 1 file | ❌ Direct OK |
| Config value change | 1 config file | ❌ Direct OK |
