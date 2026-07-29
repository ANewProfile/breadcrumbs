# Breadcrumbs — Session Handoff

## Goal

Build an MVP of **Breadcrumbs**: a single-user student productivity app that reads Google Calendar to find free time blocks, then auto-schedules manually entered tasks using subject grouping (cognitive load) and time estimation (weighted average of user estimate + historical actuals). Rule-based for MVP; ML deferred.

**Stack:** Next.js 16 + Tailwind v4 + TypeScript (frontend), FastAPI + Python (backend), MongoDB (database — local for dev, Atlas for prod).

---

## Current State

### What's working end-to-end
The full MVP loop works:
1. User adds tasks via the web UI (title, subject, estimated minutes)
2. "Run Scheduler" button hits `POST /schedule/run` → reads Google Calendar → computes free blocks (future-only) → assigns tasks → writes `[Breadcrumbs] <title>` events to Google Calendar → updates MongoDB with `status: "scheduled"`, `scheduled_blocks`, and `gcal_event_id`
3. Tasks that don't fit any free block are marked `status: "unschedulable"` and surfaced in the UI with an amber warning banner
4. UI re-renders showing scheduled tasks with their assigned time slots
5. User clicks "Complete" on a task, enters actual minutes, task is marked done

MongoDB is unblocked (see history below). `backend/.env` has `MONGODB_URI=mongodb://localhost:27017`.

Google OAuth token (`backend/token.json`) exists and is scoped to `calendar.events` (read + write events, no calendar settings access). This was re-issued this session — should be fine.

### What's NOT working / known issues

- **No GCal event deletion** — when a task is deleted or completed, the corresponding GCal event (stored as `gcal_event_id` on the task document) is not removed from the calendar.
- **No events = no free blocks** — `compute_free_blocks` derives its date range from the events it finds. If GCal has zero events in the next 7 days, `busy` is empty and the function returns `[]` early (line 18–19 of `get_free_blocks.py`). This would cause the scheduler to mark every task unschedulable.
- **Unschedulable tasks can't be re-scheduled** — once a task is marked `unschedulable`, re-running the scheduler won't pick it up (the query in `schedule.py` filters for `status: "pending"` only). For now, users have to delete and re-add such tasks.
- **Dark mode UI** — `color-scheme: light` was added to `:root` in `globals.css` two sessions ago. This should fix the invisible title and input placeholder text when the OS is in dark mode, but it hasn't been confirmed visually this session. If it's still broken, try setting `color-scheme: light` on `body` instead, or add `style={{ colorScheme: 'light' }}` to the `<html>` element in `layout.tsx`.
- **`tests/test_calendar_service.py`** — broken stub that imports `pymock` (not a real package). Leave alone until writing real calendar service tests.

### How to run
```bash
# Terminal 1 — backend (from /breadcrumbs/backend)
venv/bin/uvicorn main:app --reload

# Terminal 2 — frontend (from /breadcrumbs/frontend)
npm run dev   # binds to :3001 because :3000 is taken
```
Open `http://localhost:3001`. The GCal OAuth token is already present at `backend/token.json` — no browser prompt needed on next scheduler run.

### MongoDB (local dev)
- `mongod` is managed via `sudo systemctl start/stop mongod`
- Config at `/etc/mongod.conf` — `#security:` is commented out (no auth), `bindIp: 127.0.0.1`
- If mongod is restarted with `--auth --bind_ip_all` flags (happens if started manually), the localhost exception is disabled and nothing can authenticate. Always start via systemctl.

---

## Files and their status

```
backend/
├── auth/google_auth.py              ✅ done — SCOPES now ["calendar.events"] (was readonly)
├── services/calendar_service.py     ✅ done — get_events() fetches 7 days of primary calendar events
├── services/get_free_blocks.py      ✅ done — clips window_start to max(day_start, now) so past times are excluded
├── services/scheduler.py            ✅ done — returns (assignments, unfit_ids) tuple; reads task["id"] (not "_id")
├── services/calendar_write.py       ✅ done — create_gcal_event() creates "[Breadcrumbs] <title>" event
├── routers/tasks.py                 ✅ done — POST/GET/PATCH/DELETE + status filter on GET
├── routers/schedule.py              ✅ done — calls create_gcal_event per assigned task; marks unfit tasks "unschedulable"
├── routers/__init__.py              ✅ done
├── utils.py                         ✅ FIXED — serialize() now renames _id → id (was keeping it as _id)
├── database.py                      ✅ done — TLS-conditional connection, falls back to localhost:27017
├── main.py                          ✅ done — both routers, CORS for localhost:3000 and :3001
├── .env                             ✅ done — MONGODB_URI=mongodb://localhost:27017
├── token.json                       ✅ exists — scoped to calendar.events
├── requirements.txt                 ✅ done (missing pytest — add it)
├── API_TESTING.md                   ✅ done — curl test guide for all endpoints
├── tests/test_scheduler.py          ✅ 7 passing tests — updated for tuple return + "id" key
├── tests/test_get_free_blocks.py    ✅ 2 passing tests — past blocks excluded, future blocks included
└── tests/test_calendar_service.py   ⚠️  broken stub (pymock), ignore

frontend/
├── lib/api.ts                       ✅ done — Task.status now includes "unschedulable"
├── app/actions.ts                   ✅ done — Server Actions: createTask, completeTask, deleteTask, runScheduler
├── app/page.tsx                     ✅ done — renders Scheduled, Pending, and Unschedulable sections
├── app/layout.tsx                   ✅ done — title "Breadcrumbs", Geist font
├── app/globals.css                  ⚠️  color-scheme: light applied but unconfirmed visually
├── app/components/AddTaskForm.tsx   ✅ done — inputs have explicit bg-white
├── app/components/TaskCard.tsx      ✅ done — hides Complete button for unschedulable tasks
└── app/components/RunSchedulerBtn.tsx ✅ done — Client Component with loading state + error display
```

---

## Architecture Notes (important for next session)

### Next.js 16 / React 19 patterns in use
This is **not** the Next.js you know from training data. Key things that differ:

- **`fetch` is NOT cached by default** in Next.js 16 (opposite of 13/14).
- **Server Components fetch directly** — `page.tsx` is `async` and calls `fetchTasks()` from `lib/api.ts` server-side. No SWR, no React Query, no `useEffect`.
- **Server Actions** (in `app/actions.ts` with `"use server"` at top) call the FastAPI backend, then `revalidatePath("/")` to invalidate and re-render the page. This is how mutations trigger UI updates.
- **`AddTaskForm.tsx` is a Server Component** — no `"use client"`, just a `<form action={createTaskAction}>`.
- **`TaskCard.tsx` and `RunSchedulerBtn.tsx` are Client Components** (`"use client"`) because they need local state.
- **`@/` path alias** resolves to `frontend/` (configured in `tsconfig.json`).

### Critical `_id` → `id` fix (this session)
`utils.serialize()` used to convert `_id` from ObjectId to string but keep the field name `_id`. The frontend `Task` type has `id: string`. This meant `task.id` was `undefined` at runtime on every task, causing:
- React key warning ("Each child in a list should have a unique key prop") — `key={undefined}` on every list item
- Delete and Complete silently broken — hidden `<input value={task.id}>` submitted empty string

Fix: `serialize()` now does `doc["id"] = str(doc.pop("_id"))`. All downstream callers updated: `assign_tasks` reads `task["id"]`, `schedule.py` builds `task_title_map` with `t["id"]`, tests use `{"id": ...}`.

---

## Everything We Tried That Didn't Work

### This session — OAuth scope
`google_auth.py` was using `calendar.readonly` scope. Writing events requires at least `calendar.events`. The fix was to change SCOPES and delete `token.json` to force a fresh OAuth flow. The new token has been issued.

### Previous session — UI contrast (dark mode)
**Problem:** OS in dark mode. Title (`text-zinc-900`) was invisible on dark background; input placeholder text was invisible on light input background.

**Attempt 1:** Removed `@media (prefers-color-scheme: dark)` block from `globals.css`.
- Did not fix it. That block only controlled our custom `--background`/`--foreground` properties. Tailwind v4's own preflight still honors OS dark mode independently.

**Attempt 2:** Added `color-scheme: light` to `:root` in `globals.css`.
- Correct approach — tells the browser to always use the light color scheme, including native form controls. Applied but not visually confirmed. If still broken, try on `body` or on `<html>` via `layout.tsx`.

### Earlier sessions — MongoDB
- `mongod` was running with `--auth --bind_ip_all` (started manually, not via systemctl)
- `--bind_ip_all` disables the MongoDB localhost exception
- TLS mismatch: `database.py` had `tls=True` hardcoded; local mongod doesn't speak TLS → fixed by making TLS conditional on `mongodb+srv://` URI prefix
- Fixed by killing the process and restarting via `sudo systemctl start mongod`

### Earlier sessions — architecture decisions
- **Next.js API routes as backend** — rejected. Python better for scheduling logic and future ML.
- **Putting `compute_free_blocks` in `calendar_service.py`** — rejected. IO and computation in separate files keeps both independently testable.
- **`cursor = e` instead of `cursor = max(cursor, e)`** in `compute_free_blocks` — the `max` version guards against a backwards cursor from overlapping events.
- **SWR/React Query** — unnecessary. Server Components + Server Actions + `revalidatePath` handle everything.

---

## Next Immediate Steps

### 1. Update MongoDB credentials for new computer
This session is running on a new machine — `backend/.env` and/or local `mongod` setup likely need to be reconfigured to match this computer's MongoDB install (local dev credentials, URI, or Atlas connection string may differ from the previous machine). Verify `MONGODB_URI` in `backend/.env` and confirm `mongod` is running and reachable before testing anything else.

### 2. Confirm dark mode fix
Open `http://localhost:3001`. Check that the "Breadcrumbs" title is readable and input placeholder text is visible. If not, change `globals.css` to put `color-scheme: light` on `body` instead of `:root`.

### 3. Delete GCal event on task deletion / completion
The `gcal_event_id` field is now stored on each scheduled task in MongoDB. When a task is deleted or completed:
- In `routers/tasks.py`, before `delete_one`, call a new `delete_gcal_event(creds, gcal_event_id)` from `services/calendar_write.py`
- Same for `complete_task` — on completion, the GCal event should be removed (task is done)
- Need to call `get_credentials()` in those routes (currently only used in `schedule.py`)

```python
# add to services/calendar_write.py
def delete_gcal_event(creds, event_id: str) -> None:
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(calendarId="primary", eventId=event_id).execute()
```

### 4. Fix "no events = no free blocks"
`compute_free_blocks` returns `[]` immediately if GCal has no events. Instead, fall back to scheduling across a fixed window (e.g., today + 7 days) using `day_start`/`day_end`. The simplest fix:

```python
if not busy:
    # no events → treat the next 7 days as fully free
    from datetime import date, timedelta
    today = datetime.now(tz).date()
    all_dates = [today + timedelta(days=i) for i in range(7)]
    # then run the normal per-day loop with no busy intervals
```

### 5. Allow re-scheduling unschedulable tasks
Currently the scheduler only queries `status: "pending"`. Change the query to include `"unschedulable"` so those tasks get another shot when the user re-runs the scheduler (e.g. after a day passes and new free blocks open up). Change in `schedule.py`:
```python
tasks_collection.find({"status": {"$in": ["pending", "unschedulable"]}})
```

---

## Roadmap

### Short term
- Weighted time estimate: once a subject has ≥5 completions, switch to `0.6 * mean(actual_minutes) + 0.4 * user_estimate`
- Configurable `day_start`, `day_end`, timezone in a `settings` MongoDB collection
- Delete GCal event when task is deleted or marked done (step 2 above)

### Post-MVP (out of scope for now)
- Real auth / multi-user support
- ML-based time prediction
- Canvas / Google Classroom integration
- Mobile UI
