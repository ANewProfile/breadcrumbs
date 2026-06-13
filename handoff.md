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
- Python venv at `backend/venv/` — all dependencies installed; run with `venv/bin/python`
- MongoDB Atlas cluster connected — URI in `backend/.env`
- Google Calendar OAuth working — Desktop App credentials, `credentials.json` in `/backend`, token persisted to `token.json` via `run_local_server()`
- `backend/auth/google_auth.py` — `get_credentials()` written and working
- `backend/services/calendar_service.py` — `get_events()` fetches raw events from primary calendar
- `backend/services/get_free_blocks.py` — `compute_free_blocks()` fully written and bug-fixed: parses events, clips to day window, merges overlapping busy blocks, detects gaps ≥15 min, handles timezones via `zoneinfo`
- `backend/utils.py` — `serialize()` helper written
- `backend/routers/tasks.py` — all 5 CRUD endpoints written: `POST /tasks`, `GET /tasks`, `PATCH /tasks/{id}`, `PATCH /tasks/{id}/complete`, `DELETE /tasks/{id}`
- `backend/routers/schedule.py` — `POST /schedule/run` fully wired: fetches calendar, computes free blocks, calls `assign_tasks`, writes results back to MongoDB, returns both
- `backend/services/scheduler.py` — `assign_tasks` implemented: sorts tasks by subject (cognitive grouping), greedily fits each into the first block large enough, shrinks block after each assignment, returns `{task_id: {start, end}}` with ISO strings
- `backend/tests/test_scheduler.py` — 7 passing tests covering: single fit, task too large, block shrinking, subject sort order, empty inputs, multi-block spill
- `backend/main.py` — both routers wired in with correct prefixes, CORS middleware for `localhost:3000`
- `backend/requirements.txt` — cleaned up
- `backend/API_TESTING.md` — full curl-based test guide for all endpoints

### What's NOT done yet
- **Endpoints have NOT been verified against a running server** — do this before anything else
- `token.json` is missing — `POST /schedule/run` will trigger a browser OAuth flow on first run; let it complete once and the token persists
- `GET /tasks` has no `?status=` filter param yet — needed for frontend to separate pending from scheduled
- `tests/test_calendar_service.py` — stub only, imports `pymock` which doesn't exist; leave alone until writing real tests
- Frontend — untouched

### Files actively being built
```
backend/
├── auth/google_auth.py              ✅ done
├── services/calendar_service.py     ✅ done
├── services/get_free_blocks.py      ✅ done
├── services/scheduler.py            ✅ done (assign_tasks implemented + tested)
├── routers/tasks.py                 ✅ done
├── routers/schedule.py              ✅ done (MongoDB write-back wired)
├── routers/__init__.py              ✅ done
├── utils.py                         ✅ done
├── database.py                      ✅ done
├── main.py                          ✅ done
├── requirements.txt                 ✅ cleaned up
├── API_TESTING.md                   ✅ done
├── tests/test_scheduler.py          ✅ 7 passing tests
└── tests/test_calendar_service.py   ⚠️  broken stub, ignore for now
```

---

## What We Tried That Didn't Work

### From earlier sessions
- **Next.js API routes as backend** — rejected. Scheduling logic and future ML are naturally Python; Google Calendar SDK has better Python support; FastAPI is Theo's primary language comfort zone.
- **Local MongoDB** — started with `brew install mongodb-community` but switched to Atlas. No data loss. Atlas is accessible anywhere and requires no local service management.
- **Putting `compute_free_blocks` in `calendar_service.py`** — rejected. `calendar_service.py` handles only IO (fetching); computation belongs in its own file. Keeps both independently testable.
- **`cursor = e` instead of `cursor = max(cursor, e)`** in `compute_free_blocks` — the `max` version is defensive against a bug in the merge step causing a backwards cursor.
- **`get_free_blocks.py` had five bugs** — all fixed:
  1. `from zoneinfor import ZoneInfo` → `from zoneinfo import ZoneInfo` (typo)
  2. `clipped_start = max(s, window_end)` → `max(s, window_start)` (start/end swapped)
  3. `clipped_end = min(e, window_start)` → `min(e, window_end)` (start/end swapped)
  4. `cusor` → `cursor` (typo in variable name)
  5. `"duration_min"; duration` → `"duration_min": duration` (semicolon instead of colon)
- **`requirements.txt` had conflicting pymongo entries** — `pymongo[srv]==3.12` and `pymongo==4.17.0` both listed. Consolidated to `pymongo[srv]==4.17.0`. Also removed `annotated-doc==0.0.4` (spurious artifact; real package `annotated-types` was already listed).
- **`test_calendar_service.py` imports `pymock`** — not a real package. Tests were never finished. Left alone.

### This session
- **venv was missing** — `backend/venv/` did not exist despite being listed as done in the previous handoff. Recreated with `python3 -m venv venv && venv/bin/pip install -r requirements.txt`. Always activate with `venv/bin/python` or `venv/bin/uvicorn`, not the system Python.

---

## Next Immediate Steps

**1. Verify all endpoints** using `backend/API_TESTING.md`.

```bash
cd backend && venv/bin/uvicorn main:app --reload
```

Work through the guide top to bottom. The scheduler endpoint (`POST /schedule/run`) requires `token.json` — if it's missing, `get_credentials()` opens a browser for OAuth. Complete that flow once and the token persists.

**2. Add a `status` filter to `GET /tasks`** so the frontend can query pending and scheduled tasks separately:

```python
@router.get("")
def list_tasks(status: str | None = None):
    query = {"status": {"$ne": "done"}}
    if status:
        query = {"status": status}
    return [serialize(t) for t in tasks_collection.find(query)]
```

**3. Start the frontend.** Minimum viable UI in order:
1. Task list — shows all pending/scheduled tasks with subject tag and scheduled time if assigned
2. Add task form — title, subject dropdown, estimated minutes input
3. "Run scheduler" button — calls `POST /schedule/run`, refreshes list
4. Mark complete — prompts for actual minutes, calls `PATCH /{id}/complete`

Use **SWR or React Query** for data fetching. Keep API calls in `frontend/lib/api.ts`. No calendar view needed for MVP.

---

## Roadmap

### Short term — after frontend MVP
- Weighted time estimate: once a subject has ≥5 completions with logged `actual_minutes`, switch to `0.6 * mean(actual_minutes) + 0.4 * user_estimate`
- Surface unschedulable tasks (no block large enough) to user instead of silently dropping them
- Split tasks longer than any single free block, or flag them
- Configurable `day_start`, `day_end`, timezone stored in the `settings` collection

### Post-MVP (out of scope for now)
- Real auth / multi-user support
- Write scheduled tasks back to Google Calendar as events
- ML-based time prediction
- Canvas / Google Classroom integration
- Mobile UI
