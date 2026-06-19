from fastapi import APIRouter, HTTPException
from bson import ObjectId
from auth.google_auth import get_credentials
from services.calendar_service import get_events
from services.get_free_blocks import compute_free_blocks
from services.scheduler import assign_tasks
from services.calendar_write import create_gcal_event
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

    assignments, unfit_ids = assign_tasks(pending_tasks, free_blocks)

    task_title_map = {t["id"]: t["title"] for t in pending_tasks}

    for task_id, block in assignments.items():
        gcal_id = create_gcal_event(
            creds,
            title=task_title_map.get(task_id, "Task"),
            start_iso=block["start"],
            end_iso=block["end"],
        )
        tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "scheduled",
                "scheduled_blocks": [block],
                "gcal_event_id": gcal_id,
            }},
        )

    for task_id in unfit_ids:
        tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"status": "unschedulable"}},
        )

    return {
        "free_blocks": [
            {**b, "start": b["start"].isoformat(), "end": b["end"].isoformat()}
            for b in free_blocks
        ],
        "assignments": assignments,
        "unfit_ids": unfit_ids,
    }
