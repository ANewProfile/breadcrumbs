from fastapi import APIRouter, HTTPException
from auth.google_auth import get_credentials
from services.calendar_service import get_events
from services.get_free_blocks import compute_free_blocks
from services.scheduler import assign_tasks
from database import tasks_collection
from utils import serialize

router = APIRouter()


@router.post("/run")
def run_schedule():
    creds = get_credentials()
    events = get_events(creds)
    free_blocks = compute_free_blocks(events)

    pending_tasks = [serialize(t) for t in tasks_collection.find({"status": "pending"})]
    if not pending_tasks:
        raise HTTPException(status_code=400, detail="No pending tasks to schedule")

    assignments = assign_tasks(pending_tasks, free_blocks)
    return {"free_blocks": [
        {**b, "start": b["start"].isoformat(), "end": b["end"].isoformat()}
        for b in free_blocks
    ], "assignments": assignments}
