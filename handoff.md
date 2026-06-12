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
- Python venv created, all dependencies installed
- MongoDB Atlas cluster connected — URI in `backend/.env`
- Google Calendar OAuth working — Desktop App credentials, `credentials.json` in `/backend`, token persisted to `token.json` via `run_local_server()`
- `backend/auth/google_auth.py` — `get_credentials()` written and working
- `backend/services/calendar_service.py` — `get_events()` fetches raw events from primary calendar
- `backend/services/get_free_blocks.py` — `compute_free_blocks()` fully written and bug-fixed: parses events, clips to day window, merges overlapping busy blocks, detects gaps ≥15 min, handles timezones via `zoneinfo`
- `backend/utils.py` — `serialize()` helper written
- `backend/routers/tasks.py` — all 5 CRUD endpoints written: `POST /tasks`, `GET /tasks`, `PATCH /tasks/{id}`, `PATCH /tasks/{id}/complete`, `DELETE /tasks/{id}`
- `backend/routers/schedule.py` — `POST /schedule/run` written: fetches calendar, computes free blocks, calls `assign_tasks` stub, returns both
- `backend/services/scheduler.py` — `assign_tasks` stub written (returns `{}`)
- `backend/main.py` — both routers wired in with correct prefixes, CORS middleware for `localhost:3000`
- `backend/requirements.txt` — cleaned up (removed duplicate `pymongo` entries and spurious `annotated-doc`)
- `backend/API_TESTING.md` — full curl-based test guide for all endpoints

### What's NOT done yet
- Endpoints have NOT been verified against a running server yet — do this before anything else
- `assign_tasks` is a stub — no real scheduling logic
- `tests/test_calendar_service.py` — stub only (imports `pymock` which doesn't exist, body is empty)
- `tests/test_scheduler.py` — empty file
- Frontend — untouched

### Files actively being built
```
backend/
├── auth/google_auth.py              ✅ done
├── services/calendar_service.py     ✅ done
├── services/get_free_blocks.py      ✅ done (bugs fixed this session)
├── services/scheduler.py            ⚠️  assign_tasks is a stub
├── routers/tasks.py                 ✅ done
├── routers/schedule.py              ✅ done
├── routers/__init__.py              ✅ done
├── utils.py                         ✅ done
├── database.py                      ✅ done
├── main.py                          ✅ done
├── requirements.txt                 ✅ cleaned up
├── API_TESTING.md                   ✅ done
└── .env                             ✅ done
```

---

## What We Tried That Didn't Work

### From the previous session
- **Next.js API routes as backend** — rejected. Scheduling logic and future ML are naturally Python; Google Calendar SDK has better Python support; FastAPI is Theo's primary language comfort zone.
- **Local MongoDB** — started with `brew install mongodb-community` but switched to Atlas. No data loss. Atlas is accessible anywhere and requires no local service management.
- **Putting `compute_free_blocks` in `calendar_service.py`** — rejected. `calendar_service.py` handles only IO (fetching); computation belongs in the scheduler. Keeps both independently testable.
- **`cursor = e` instead of `cursor = max(cursor, e)`** in `compute_free_blocks` — the `max` version is defensive against a bug in the merge step causing a backwards cursor.

### This session
- **`get_free_blocks.py` had five bugs from last session** — all fixed:
  1. `from zoneinfor import ZoneInfo` → `from zoneinfo import ZoneInfo` (typo)
  2. `clipped_start = max(s, window_end)` → `max(s, window_start)` (start/end swapped)
  3. `clipped_end = min(e, window_start)` → `min(e, window_end)` (start/end swapped)
  4. `cusor` → `cursor` (typo in variable name)
  5. `"duration_min"; duration` → `"duration_min": duration` (semicolon instead of colon)
- **`requirements.txt` had conflicting pymongo entries** — `pymongo[srv]==3.12` and `pymongo==4.17.0` both listed. Consolidated to `pymongo[srv]==4.17.0`. Also removed `annotated-doc==0.0.4` (spurious artifact; real package `annotated-types` was already listed).
- **`test_calendar_service.py` imports `pymock`** — not a real package. Tests were never finished. Leave alone for now; fix when writing real tests.

---

## Next Immediate Steps

**1. Verify all endpoints** using `backend/API_TESTING.md`.

```bash
cd backend && uvicorn main:app --reload
```

Work through the guide top to bottom. The scheduler endpoint (`POST /schedule/run`) requires `token.json` to exist — if it doesn't, `get_credentials()` will open a browser for OAuth.

**2. Implement `assign_tasks`** in `backend/services/scheduler.py`. Logic:

```python
def assign_tasks(tasks: list, free_blocks: list) -> dict:
    # 1. Sort tasks by subject to group cognitive load
    tasks_sorted = sorted(tasks, key=lambda t: t["subject"])

    # 2. Work through free blocks greedily
    blocks = [dict(b) for b in free_blocks]  # shallow copy so we can shrink
    assignments = {}

    for task in tasks_sorted:
        needed = task["estimated_minutes"]
        for block in blocks:
            if block["duration_min"] >= needed:
                end_dt = block["start"] + timedelta(minutes=needed)
                assignments[task["_id"]] = {"start": block["start"], "end": end_dt}
                # shrink block
                block["start"] = end_dt
                block["duration_min"] -= needed
                break

    return assignments
```

Test with hardcoded dummy tasks and free blocks before wiring to the real DB/calendar call. Put the test in `tests/test_scheduler.py`.

---

## Roadmap

### Short term — after assign_tasks works
- Wire actual `scheduled_blocks` back into MongoDB: after `assign_tasks` returns, write `{"$set": {"scheduled_blocks": [...], "status": "scheduled"}}` on each assigned task in `POST /schedule/run`
- Add a `GET /tasks` filter param so frontend can show scheduled vs. pending separately

### Medium term — build the frontend
Minimum viable UI, in order of priority:
1. Task list — shows all pending/scheduled tasks with subject tag and scheduled time if assigned
2. Add task form — title, subject dropdown, estimated minutes input
3. "Run scheduler" button — calls `POST /schedule/run`, refreshes list
4. Mark complete — prompts for actual minutes, calls `PATCH /{id}/complete`

Use **SWR or React Query** for data fetching. Keep API calls in `frontend/lib/api.ts`. No calendar view needed for MVP.

### Late MVP — close the loop
- Weighted time estimate: once a subject has ≥5 completions with logged `actual_minutes`, switch to `0.6 * mean(actual_minutes) + 0.4 * user_estimate`
- Configurable `day_start`, `day_end`, timezone stored in the `settings` collection
- Surface unschedulable tasks (no block large enough) to user instead of silently dropping them
- Split tasks longer than any single free block, or flag them

### Post-MVP (out of scope for now)
- Real auth / multi-user support
- Write scheduled tasks back to Google Calendar as events
- ML-based time prediction
- Canvas / Google Classroom integration
- Mobile UI
