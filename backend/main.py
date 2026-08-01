# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import tasks, schedule, settings

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:3001", "https://breadcrumbs.kugelboshisthe.world"], allow_methods=["*"], allow_headers=["*"])
app.include_router(tasks.router, prefix="/tasks")
app.include_router(schedule.router, prefix="/schedule")
app.include_router(settings.router, prefix="/settings")

