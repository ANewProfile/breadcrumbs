# Breadcrumbs — Session Handoff

## Goal

Build an MVP of **Breadcrumbs**: a single-user student productivity app that reads Google Calendar to find free time blocks, then auto-schedules manually entered tasks using subject grouping (cognitive load) and time estimation (weighted average of user estimate + historical actuals). Rule-based for MVP; ML deferred.

**Stack:** Next.js 16 + Tailwind v4 + TypeScript (frontend), FastAPI + Python (backend), MongoDB Atlas (database).

---

## Current State

### What's working end-to-end
The full MVP loop works:
1. User adds tasks via the web UI (title, subject, estimated minutes)
2. "Run Scheduler" button hits `POST /schedule/run` → reads Google Calendar → computes free blocks → assigns tasks → writes scheduled times back to MongoDB
3. UI re-renders showing scheduled tasks with their assigned time slots
4. User clicks "Complete" on a task, enters actual minutes, task is marked done

### What's NOT done yet (known issues)
- **Form styling is off** — the Add Task form inputs don't look right. The colors are the problem: in Tailwind v4, `<input>` elements render with a transparent background by default so `bg-zinc-50` on the form container shows through the inputs awkwardly. Fix: add `bg-white` explicitly to each `<input>` className in `AddTaskForm.tsx`.
- **No Google Calendar write-back** — the scheduler reads GCal to find free blocks but never creates events on the calendar for the scheduled tasks. Users have no visibility in GCal of what Breadcrumbs scheduled. This is the next real feature to build (see Next Immediate Steps).
- **`tests/test_calendar_service.py`** — broken stub that imports `pymock` (not a real package). Leave alone until writing real calendar service tests.
- **pytest not in `requirements.txt`** — had to install it manually this session. Add `pytest` to `requirements.txt` so the venv is complete from a fresh install.
- **Unschedulable tasks are silently dropped** — if a task is too long to fit any free block, `assign_tasks` just skips it with no feedback. The UI shows nothing; the task stays "pending" forever with no explanation.

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
├── database.py                      ✅ done — MongoDB Atlas connection, tasks_collection
├── main.py                          ✅ done — both routers, CORS for localhost:3000
├── requirements.txt                 ✅ done (but missing pytest — add it)
├── API_TESTING.md                   ✅ done — curl test guide for all endpoints
├── tests/test_scheduler.py          ✅ 7 passing tests
└── tests/test_calendar_service.py   ⚠️  broken stub, ignore

frontend/
├── lib/api.ts                       ✅ done — typed fetch wrappers for all FastAPI endpoints
├── app/actions.ts                   ✅ done — Server Actions: createTask, completeTask, deleteTask, runScheduler
├── app/page.tsx                     ✅ done — async Server Component, fetches tasks, renders Pending + Scheduled sections
├── app/layout.tsx                   ✅ done — title "Breadcrumbs", Geist font
├── app/globals.css                  ✅ done — Tailwind v4 import, base tokens
├── app/components/AddTaskForm.tsx   ⚠️  works but has styling issue (input colors — see above)
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
npm run dev
```
Open `http://localhost:3000`. First `POST /schedule/run` opens a browser for Google OAuth if `token.json` is missing — complete it once and it persists.

---

## What We Tried That Didn't Work

### From earlier sessions
- **Next.js API routes as backend** — rejected. Scheduling logic and future ML are naturally Python; Google Calendar SDK has better Python support; FastAPI is Theo's comfort zone.
- **Local MongoDB** — started with `brew install mongodb-community`, switched to Atlas. No data loss. Atlas needs no local service management.
- **Putting `compute_free_blocks` in `calendar_service.py`** — rejected. `calendar_service.py` is IO only; computation in its own file keeps both independently testable.
- **`cursor = e` instead of `cursor = max(cursor, e)`** in `compute_free_blocks` — the `max` version guards against a bug in the merge step causing a backwards cursor.
- **Five bugs in `get_free_blocks.py`** — all fixed:
  1. `from zoneinfor import ZoneInfo` → `from zoneinfo import ZoneInfo` (typo)
  2. `clipped_start = max(s, window_end)` → `max(s, window_start)` (swapped)
  3. `clipped_end = min(e, window_start)` → `min(e, window_end)` (swapped)
  4. `cusor` → `cursor` (typo)
  5. `"duration_min"; duration` → `"duration_min": duration` (semicolon not colon)
- **Conflicting pymongo entries in `requirements.txt`** — had both `pymongo[srv]==3.12` and `pymongo==4.17.0`. Consolidated to `pymongo[srv]==4.17.0`. Also removed `annotated-doc==0.0.4` (spurious; real package `annotated-types` was already listed).
- **`test_calendar_service.py` imports `pymock`** — not a real package. Tests were never finished. Left alone.
- **venv was missing despite being listed as done** — recreated with `python3 -m venv venv && venv/bin/pip install -r requirements.txt`. Always use `venv/bin/python` / `venv/bin/uvicorn`, not system Python.
- **SWR/React Query for data fetching** — considered, but unnecessary in Next.js 16. Server Components fetch directly; Server Actions + `revalidatePath` handle post-mutation refresh. Zero client-side data fetching libraries needed.

---

## Next Immediate Steps

### 1. Fix form input colors (quick)
In `frontend/app/components/AddTaskForm.tsx`, each `<input>` needs `bg-white` added to its `className`. Currently inputs inherit the `bg-zinc-50` of their container through transparency, making the borders look faint and the fields blend together. The fix is a one-liner per input:

```tsx
className="bg-white border border-zinc-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
```

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
    return result["id"]  # store this so we can delete/update the event later
```

Then in `backend/routers/schedule.py`, after the MongoDB write-back loop, call `create_gcal_event` for each assigned task and store the returned `gcal_event_id` on the task document. You'll need to fetch the task title from MongoDB (you already have the task objects in `pending_tasks`).

The `gcal_event_id` should be stored on the task in MongoDB so that if a task is deleted or re-scheduled, the event can be removed from GCal too (future work, but set up the field now).

### 3. Surface unschedulable tasks (after GCal write-back)
`assign_tasks` currently silently skips tasks that don't fit any free block. The fix: return a second value — a list of task IDs that couldn't be scheduled. In `schedule.py`, after the assignment loop, update those tasks with `status: "unschedulable"` and surface them in the UI with a warning.

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
