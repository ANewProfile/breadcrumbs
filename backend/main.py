# backend/main.py
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from rate_limit import default_rate_limit
from routers import tasks, schedule, settings, auth, account, no_go_zones, calendars

# rate limiting to protect against my friends
app = FastAPI(dependencies=[Depends(default_rate_limit)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://usebreadcrumbs.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# compressed json packages
app.add_middleware(GZipMiddleware, minimum_size=500)
app.include_router(tasks.router, prefix="/tasks")
app.include_router(schedule.router, prefix="/schedule")
app.include_router(settings.router, prefix="/settings")
app.include_router(auth.router, prefix="/auth")
app.include_router(account.router, prefix="/account")
app.include_router(no_go_zones.router, prefix="/no-go-zones")
app.include_router(calendars.router, prefix="/calendars")

