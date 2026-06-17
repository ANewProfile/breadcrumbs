# Breadcrumbs — Session Handoff

## Goal

Build an MVP of **Breadcrumbs**: a single-user student productivity app that reads Google Calendar to find free time blocks, then auto-schedules manually entered tasks using subject grouping (cognitive load) and time estimation (weighted average of user estimate + historical actuals). Rule-based for MVP; ML deferred.

**Stack:** Next.js 16 + Tailwind v4 + TypeScript (frontend), FastAPI + Python (backend), MongoDB (database — local for dev, Atlas for prod).

---

## Current State

### What's working end-to-end
The full MVP loop works:
1. User adds tasks via the web UI (title, subject, estimated minutes)
2. "Run Scheduler" button hits `POST /schedule/run` → reads Google Calendar → computes free blocks → assigns tasks → writes scheduled times back to MongoDB
3. UI re-renders showing scheduled tasks with their assigned time slots
4. User clicks "Complete" on a task, enters actual minutes, task is marked done

MongoDB is unblocked: the rogue manually-started `mongod --auth --bind_ip_all` was killed, `mongod` restarted via `sudo systemctl start mongod` (uses `/etc/mongod.conf` which has `#security:` commented out — no auth, binds to `127.0.0.1` only). `backend/.env` now exists with `MONGODB_URI=mongodb://localhost:27017`.

### What's NOT working right now (blocking)
- **UI contrast / dark mode** — Tailwind v4's preflight injects `color-scheme: dark light` when the OS is in dark mode. This causes:
  - The page background to go dark while `text-zinc-900` (hardcoded in `page.tsx`) stays near-black → invisible title
  - Native form elements (inputs) to render placeholder text in a light color even when `bg-white` is set → invisible placeholder text
- **Attempted fixes this session:**
  1. Removed the `@media (prefers-color-scheme: dark)` block from `globals.css` — didn't help because Tailwind's own preflight still respects OS dark mode
  2. Added `color-scheme: light` to `:root` in `globals.css` — applied at end of session, **not yet confirmed to work**

### Other known issues
- **No Google Calendar write-back** — the scheduler reads GCal to find free blocks but never creates events on the calendar for the scheduled tasks.
- **Unschedulable tasks are silently dropped** — if a task is too long to fit any free block, `assign_tasks` just skips it with no feedback.
- **`tests/test_calendar_service.py`** — broken stub that imports `pymock` (not a real package). Leave alone until writing real calendar service tests.

### Files and their status
```
backend/
├── auth/google_auth.py              ✅ done — get_credentials(), OAuth flow, token.json persistence
├── services/calendar_service.py     ✅ done — get_events() fetches 7 days of primary calendar events
├── services/get_free_blocks.py      ✅ done — compute_free_blocks(): clips to day window, merges busy, finds gaps ≥15 min
├── services/scheduler.py            ✅ done — assign_tasks(): sorts by subject, greedy fit, returns {task_id: {start, end}}
├── services/calendar_write.py       ❌ does not exist yet — needs to be built for GCal write-back
├── routers/tasks.py                 ✅ done — POST/GET/PATCH/DELETE + status filter on GET
├── routers/schedule.py              ✅ done — POST /schedule/run wired end-to-end
├── routers/__init__.py              ✅ done
├── utils.py                         ✅ done — serialize() converts ObjectId + datetime to JSON-safe types
├── database.py                      ✅ done — TLS-conditional connection, falls back to localhost:27017
├── main.py                          ✅ done — both routers, CORS for localhost:3000 and :3001
├── .env                             ✅ created — MONGODB_URI=mongodb://localhost:27017
├── requirements.txt                 ✅ done (missing pytest — add it)
├── API_TESTING.md                   ✅ done — curl test guide for all endpoints
├── tests/test_scheduler.py          ✅ 7 passing tests
└── tests/test_calendar_service.py   ⚠️  broken stub, ignore

frontend/
├── lib/api.ts                       ✅ done — typed fetch wrappers for all FastAPI endpoints
├── app/actions.ts                   ✅ done — Server Actions: createTask, completeTask, deleteTask, runScheduler
├── app/page.tsx                     ✅ done — async Server Component, fetches tasks, renders Pending + Scheduled sections
├── app/layout.tsx                   ✅ done — title "Breadcrumbs", Geist font
├── app/globals.css                  ⚠️  dark mode contrast fix applied but unconfirmed (see above)
├── app/components/AddTaskForm.tsx   ✅ styling fixed — inputs have explicit bg-white
├── app/components/TaskCard.tsx      ✅ done — shows task, subject badge, scheduled time, inline complete form, delete
└── app/components/RunSchedulerBtn.tsx ✅ done — Client Component with loading state + error display
```

---

## Architecture Notes (important for next session)

### Next.js 16 / React 19 patterns in use
This is **not** the Next.js you know from training data. Key things that differ:

- **`fetch` is NOT cached by default** in Next.js 16 (opposite of 13/14). No need for `cache: 'no-store'` on reads, but it's included for clarity.
- **Server Components fetch directly** — `page.tsx` is `async` and calls `fetchTasks()` from `lib/api.ts` server-side. No SWR, no React Query, no `useEffect`.
- **Server Actions** (in `app/actions.ts` with `"use server"` at top) call the FastAPI backend, then `revalidatePath("/")` to invalidate and re-render the page. This is how mutations trigger UI updates.
- **`AddTaskForm.tsx` is a Server Component** — no `"use client"`, just a `<form action={createTaskAction}>`. Works with progressive enhancement.
- **`TaskCard.tsx` and `RunSchedulerBtn.tsx` are Client Components** (`"use client"`) because they need local state (show/hide complete form, loading spinner).
- **`@/` path alias** resolves to `frontend/` (configured in `tsconfig.json`).

### How to run
```bash
# Terminal 1 — backend (from /breadcrumbs/backend)
venv/bin/uvicorn main:app --reload

# Terminal 2 — frontend (from /breadcrumbs/frontend)
npm run dev   # binds to :3001 because :3000 is taken
```
Open `http://localhost:3001`. First `POST /schedule/run` opens a browser for Google OAuth if `token.json` is missing — complete it once and it persists.

### MongoDB (local dev)
- `mongod` is managed via `sudo systemctl start/stop mongod`
- Config at `/etc/mongod.conf` — `#security:` is commented out (no auth), `bindIp: 127.0.0.1`
- If mongod is restarted with `--auth --bind_ip_all` flags (happens if started manually), the localhost exception is disabled and nothing can authenticate. Always start via systemctl.

---

## Everything We Tried That Didn't Work

### This session — UI contrast (dark mode)

**Problem:** System is in dark mode. Title (`text-zinc-900`) was invisible on dark background; input placeholder text was invisible on light input background.

**Attempt 1:** Removed `@media (prefers-color-scheme: dark)` block from `globals.css`.
- Did not fix it. The CSS variable block only controlled our `--background`/`--foreground` custom properties. Tailwind v4's own preflight still honors OS dark mode independently, causing the body background and form elements to render dark.

**Attempt 2:** Added `color-scheme: light` to `:root` in `globals.css`.
- This is the correct fix — it tells the browser to always use the light color scheme for all elements, including native form controls and their placeholder text.
- **Not yet confirmed** — applied at end of session. If it didn't work, investigate whether Tailwind v4's `@import "tailwindcss"` preflight overrides `color-scheme` on `:root` and try setting it on `html` or `body` instead, or add `color-scheme: light` to the `body` rule directly.

### From previous sessions — MongoDB
- `mongod` was running with `--auth --bind_ip_all` (started manually, not via systemctl)
- `--bind_ip_all` disables the MongoDB localhost exception, so `createUser` without credentials fails
- TLS mismatch: `database.py` had `tls=True` hardcoded; local mongod doesn't speak TLS → fixed by making TLS conditional on `mongodb+srv://` URI prefix
- Fixed by killing the process and restarting via `sudo systemctl start mongod`

### From earlier sessions
- **Next.js API routes as backend** — rejected. Scheduling logic and future ML are naturally Python; Google Calendar SDK has better Python support; FastAPI is Theo's comfort zone.
- **Local MongoDB → Atlas** — started with local, switched to Atlas. No data loss. Atlas needs no local service management. (Moved back to local for dev; Atlas still usable for prod with the same `database.py`.)
- **Putting `compute_free_blocks` in `calendar_service.py`** — rejected. `calendar_service.py` is IO only; computation in its own file keeps both independently testable.
- **`cursor = e` instead of `cursor = max(cursor, e)`** in `compute_free_blocks` — the `max` version guards against a bug in the merge step causing a backwards cursor.
- **Five bugs in `get_free_blocks.py`** — all fixed (typos, swapped window_start/window_end, semicolon vs colon in dict literal).
- **Conflicting pymongo entries in `requirements.txt`** — consolidated to `pymongo[srv]==4.17.0`.
- **SWR/React Query for data fetching** — considered, unnecessary. Server Components + Server Actions + `revalidatePath` handle everything.

---

## Next Immediate Steps

### 1. Confirm the dark mode fix
Refresh `http://localhost:3001`. If the title and placeholder text are still invisible:
- Try moving `color-scheme: light` from `:root` to `body` in `globals.css`
- Or add it to the `html` element via `layout.tsx`: `<html ... style={{ colorScheme: 'light' }}>`
- Last resort: add explicit `text-zinc-900` color to the `body` rule and `placeholder-zinc-500` to every input

### 2. Write scheduled tasks back to Google Calendar
Create `backend/services/calendar_write.py`:
```python
from googleapiclient.discovery import build

def create_gcal_event(creds, title: str, start_iso: str, end_iso: str) -> str:
    service = build("calendar", "v3", credentials=creds)
    event = {
        "summary": f"[Breadcrumbs] {title}",
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return result["id"]
```
Then in `backend/routers/schedule.py`, after the MongoDB write-back loop, call `create_gcal_event` for each assigned task and store `gcal_event_id` on the task document.

### 3. Surface unschedulable tasks
`assign_tasks` currently silently skips tasks that don't fit any free block. Fix: return a second value — a list of unfit task IDs. In `schedule.py`, update those tasks with `status: "unschedulable"` and surface them in the UI with a warning banner.

---

## Roadmap

### Short term
- Weighted time estimate: once a subject has ≥5 completions, switch to `0.6 * mean(actual_minutes) + 0.4 * user_estimate`
- Configurable `day_start`, `day_end`, timezone in a `settings` MongoDB collection
- Delete GCal event when a task is deleted or marked done

### Post-MVP (out of scope for now)
- Real auth / multi-user support
- ML-based time prediction
- Canvas / Google Classroom integration
- Mobile UI
