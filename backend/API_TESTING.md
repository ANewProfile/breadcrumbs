# API Endpoint Testing Guide

Start the server first:

```bash
cd backend && uvicorn main:app --reload
```

Run these in order — each builds on the previous.

---

## 1. Create a task
```bash
curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Finish pset 3", "subject": "Math", "estimated_minutes": 90}' | python3 -m json.tool
```
Expect: `201` with the full task doc including `_id`, `status: "pending"`, `actual_minutes: []`.
Copy the `_id` value — you'll need it for the next steps. Call it `TASK_ID`.

---

## 2. Create a second task
```bash
curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Read chapter 4", "subject": "Biology", "estimated_minutes": 45}' | python3 -m json.tool
```

---

## 3. List tasks
```bash
curl -s http://localhost:8000/tasks | python3 -m json.tool
```
Expect: array with both tasks, neither with `status: "done"`.

---

## 4. Update a task field
```bash
curl -s -X PATCH http://localhost:8000/tasks/TASK_ID \
  -H "Content-Type: application/json" \
  -d '{"estimated_minutes": 120}' | python3 -m json.tool
```
Expect: task returned with `estimated_minutes: 120`.

---

## 5. Complete a task
```bash
curl -s -X PATCH http://localhost:8000/tasks/TASK_ID/complete \
  -H "Content-Type: application/json" \
  -d '{"actual_minutes": 105}' | python3 -m json.tool
```
Expect: `status: "done"`, `actual_minutes: [105]`.

---

## 6. Confirm completed task is excluded from list
```bash
curl -s http://localhost:8000/tasks | python3 -m json.tool
```
Expect: only the Biology task remains (the completed Math one is filtered out).

---

## 7. Delete a task
```bash
curl -s -X DELETE http://localhost:8000/tasks/BIOLOGY_TASK_ID -o /dev/null -w "%{http_code}\n"
```
Expect: `204`.

---

## 8. Confirm deletion
```bash
curl -s http://localhost:8000/tasks | python3 -m json.tool
```
Expect: empty array `[]`.

---

## 9. Run the scheduler
Requires Google Calendar credentials in `backend/token.json`.

```bash
# First add a pending task so it has something to schedule
curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Study for exam", "subject": "Chemistry", "estimated_minutes": 60}' | python3 -m json.tool

# Then run the scheduler
curl -s -X POST http://localhost:8000/schedule/run | python3 -m json.tool
```
Expect: `{"free_blocks": [...], "assignments": {}}` — `free_blocks` populated from your real calendar, `assignments` empty because it's still a stub.

---

## Error cases

```bash
# Bad ID → 404
curl -s -X PATCH http://localhost:8000/tasks/000000000000000000000000 \
  -H "Content-Type: application/json" \
  -d '{"estimated_minutes": 10}' | python3 -m json.tool

# Empty update body → 400
curl -s -X PATCH http://localhost:8000/tasks/TASK_ID \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool

# No pending tasks → 400 from /schedule/run
curl -s -X POST http://localhost:8000/schedule/run | python3 -m json.tool
```
