# Enforcement Pitfalls — Real Session Failures

## 2026-06-18: Skipping Workflow on "Obvious" 3-File Fix

**Context:** User reported SSE connection drops during long-running generation tasks (30-60 min). Root cause: Nginx `proxy_read_timeout=600s` killing idle SSE connections + no frontend reconnect logic. Fix required 3 files: backend `status.py`, frontend `sse.ts`, frontend `page.tsx`.

**What went wrong:** Agent diagnosed the root cause, then immediately edited all 3 files without:
- Writing any tests
- Using the AI Company workflow
- Even considering that it was a multi-file change

User asked: "are you really use ai company workflow to these task? this feature is really tested?"

**Resolution:** Had to:
1. `git checkout --` all 3 files to revert
2. Start `company_start` properly
3. Run full Wave 1 (PM) → Wave 2 (Coder+UI parallel) → Wave 3 (QA) → Wave 4 (Reviewer)
4. Result: 126 backend + 21 frontend tests, proper docs, APPROVED review

**Time wasted:** ~20 minutes of rework + trust erosion

**Lesson:** Even when the fix seems trivial and obvious, if it touches 3+ files → START THE WORKFLOW. Do not write a single line of code until `company_start` is called. The user values process discipline over speed.

**Red flags that should trigger immediate workflow start:**
- Change spans backend + frontend
- Change needs new test files
- Change affects a data flow (SSE, webhooks, message queues)
- Change involves nginx/systemd/infra configs + application code
