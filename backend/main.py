# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import tasks, schedule

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])
app.include_router(tasks.router, prefix="/tasks")
app.include_router(schedule.router, prefix="/schedule")

# Two collections for MVP:
# tasks: { _id, title, subject, estimated_minutes, actual_minutes[], status, scheduled_blocks[], created_at }
# settings: { _id: "user", day_start, day_end, subjects[] }

# CRUD endpoints:
# POST /tasks
# GET /tasks
# PATCH /tasks/{id}
# DELETE /tasks/{id}
