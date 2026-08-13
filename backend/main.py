# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from routers import tasks, schedule, settings, auth, account

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://breadcrumbs.kugelboshisthe.world"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Compresses JSON responses over 500 bytes (e.g. the task list) when the
# client sends Accept-Encoding: gzip — every browser and Next.js's fetch do.
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(tasks.router, prefix="/tasks")
app.include_router(schedule.router, prefix="/schedule")
app.include_router(settings.router, prefix="/settings")
app.include_router(auth.router, prefix="/auth")
app.include_router(account.router, prefix="/account")

