# Breadcrumbs — Session Handoff

## Goal
Build an MVP of **Breadcrumbs**: a single-user student productivity app that reads Google Calendar to find free time blocks, then auto-schedules manually entered tasks using subject grouping (cognitive load) and time estimation (weighted average of user estimate + historical actuals). Rule-based for MVP; ML deferred.

**Stack:** Next.js + Tailwind + TypeScript (frontend), FastAPI + Python (backend), MongoDB Atlas (database).

---

## Current State

### What's done
- Repo initialized (`/breadcrumbs`, with `/frontend` and `/backend` subdirectories)
- `.gitignore` includes `.env`, `token.json`, `credentials.json`, `__pycache__/`, `venv/`
- Next.js app scaffolded via `create-next-app` with TypeScript + Tailwind + App Router
- Python venv created, all dependencies installed (`fastapi`, `uvicorn`, `pymongo`, `python-dotenv`, `google-api-python-client`, `google-auth-oauthlib`)
- MongoDB Atlas cluster connected — URI in `backend/.env`
- Google Calendar OAuth working — Desktop App credentials, `credentials.json` in `/backend`, token persisted to `token.json` via `run_local_server()`
- `backend/auth/google_auth.py` — `get_credentials()` written and working
- `backend/services/calendar_service.py` — `get_free_blocks()` fetches raw events from primary calendar
- `backend/services/scheduler.py` — `compute_free_blocks()` fully written: parses events, clips to day window, merges overlapping busy blocks, detects gaps with 15-minute minimum, handles timezones via `zoneinfo`

### What's NOT done yet
- `backend/utils.py` — `serialize()` helper not extracted yet (discussed but not written)
- `backend/routers/tasks.py` — CRUD endpoints discussed, not written
- `backend/routers/schedule.py` — `/schedule/run` endpoint discussed, not written
- `backend/services/scheduler.py` — `assign_tasks()` not written yet
- `backend/main.py` — routers not wired in yet
- Frontend — untouched
- Actual scheduling algorithm (`assign_tasks`) — not started

### Files actively being built
```
backend/
├── auth/google_auth.py         ✅ done
├── services/calendar_service.py ✅ done
├── services/scheduler.py        ⚠️  compute_free_blocks done, assign_tasks missing
├── routers/tasks.py             ❌ not started
├── routers/schedule.py          ❌ not started
├── utils.py                     ❌ not started
├── database.py                  ✅ done
├── main.py                      ⚠️  exists but routers not wired in
└── .env                         ✅ done
```

---

## What We Tried That Didn't Work

Nothing failed outright this session, but notable decisions made and why:

- **Next.js API routes as backend** — rejected. Scheduling logic and future ML are naturally Python; Google Calendar SDK has better Python support; FastAPI is Theo's primary language comfort zone. Next.js API routes would mean either rewriting scheduling logic in TS or running two servers anyway.
- **Local MongoDB** — started with `brew install mongodb-community` but switched to Atlas. No data loss (nothing had been written yet). Atlas is accessible anywhere and requires no local service management. Local install was uninstalled cleanly.
- **Putting `compute_free_blocks` in `calendar_service.py`** — rejected in favor of keeping it in `scheduler.py`. `calendar_service.py` should only handle IO (fetching); computation belongs in the scheduler. Keeps both functions independently testable.
- **`cursor = e` instead of `cursor = max(cursor, e)`** in `compute_free_blocks` — the `max` version is defensive against a bug in the merge step causing a backwards cursor. Strictly unnecessary given correct merging, but costs nothing.

---

## Next Immediate Step

**Write `utils.py`, then complete the routers, then wire into `main.py`.**

Exact order:

1. **`backend/utils.py`**
   ```python
   def serialize(doc: dict) -> dict:
       doc["_id"] = str(doc["_id"])
       return doc
   ```

2. **`backend/routers/tasks.py`** — implement all 5 endpoints:
   - `POST /tasks` — create with title, subject, estimated_minutes
   - `GET /tasks` — return all non-done tasks
   - `PATCH /tasks/{id}` — generic field update
   - `PATCH /tasks/{id}/complete` — set status=done, push actual_minutes
   - `DELETE /tasks/{id}`

3. **`backend/services/scheduler.py`** — add stub `assign_tasks`:
   ```python
   def assign_tasks(tasks: list, free_blocks: list) -> dict:
       return {}  # stub — implement next session
   ```

4. **`backend/routers/schedule.py`** — implement `POST /schedule/run` using the stub

5. **`backend/main.py`** — wire both routers with prefixes `/tasks` and `/schedule`, add CORS middleware for `localhost:3000`

6. **Verify** every endpoint at `http://localhost:8000/docs` before touching frontend

---

## Roadmap

### Immediate (next 1–2 sessions) — most specific

Complete the backend API as described above. Verify all endpoints manually via FastAPI's `/docs`. At this point the backend should be fully functional as a standalone API:
- Tasks can be created, listed, updated, completed, deleted
- `POST /schedule/run` calls the calendar, computes free blocks, and returns a result (even if `assign_tasks` is still a stub)

### Short term — write `assign_tasks`

Implement the actual scheduling algorithm in `scheduler.py`. Logic:
1. Sort tasks by subject (group same-subject tasks together)
2. For each task, find the first free block with enough duration (`free_block.duration_minutes >= task.estimated_minutes`)
3. Assign the task to that block, shrink the block, move to next task
4. Return a dict of `{task_id: [{"start": dt, "end": dt}]}`

Time estimation at this stage: use `estimated_minutes` directly. Weighted average (`0.6 * historical_avg + 0.4 * user_estimate`) can be swapped in once `actual_minutes` arrays have enough data.

Test this with hardcoded dummy tasks and free blocks before wiring to MongoDB/Calendar.

### Medium term — build the frontend

Minimum viable UI, in order of priority:
1. Task list — shows all pending/scheduled tasks with subject tag and scheduled time if assigned
2. Add task form — title, subject dropdown, estimated minutes input
3. "Run scheduler" button — calls `POST /schedule/run`, refreshes list
4. Mark complete — prompts for actual minutes, calls `PATCH /{id}/complete`

Use **SWR or React Query** for data fetching — don't manage loading/error state manually with `useState`. Keep API calls in a `frontend/lib/api.ts` file.

No calendar view needed. A plain list showing "Math: Finish pset 3 — scheduled Tuesday 3:00–4:30pm" is sufficient for MVP.

### Late MVP — polish and close the loop

- Surface the weighted time estimate: once a task subject has ≥5 completions with logged `actual_minutes`, switch from raw `estimated_minutes` to `0.6 * mean(actual_minutes) + 0.4 * user_estimate` in the scheduler
- Add basic settings: configurable `day_start`, `day_end`, timezone stored in the `settings` collection
- Handle edge cases in the scheduler: tasks that don't fit in any available block (surface these to the user rather than silently dropping them), tasks longer than any single free block (split or flag)
- End-to-end test: add tasks, run scheduler, verify the output looks reasonable against your actual Google Calendar

### Post-MVP (out of scope for now)
- Real auth / multi-user support
- Write scheduled tasks back to Google Calendar as events
- ML-based time prediction (needs substantial per-user historical data first)
- Canvas / Google Classroom integration
- Mobile UI
