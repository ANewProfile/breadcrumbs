from fastapi import APIRouter, HTTPException
from bson import ObjectId
from auth.google_auth import get_credentials
from services.calendar_service import get_events
from services.get_free_blocks import compute_free_blocks
from services.scheduler import assign_tasks
from services.calendar_write import create_gcal_event
from services.estimation import compute_subject_actuals, weighted_estimate
from services.settings_service import get_settings
from database import tasks_collection, settings_collection
from utils import serialize

router = APIRouter()


@router.post("/run")
def run_schedule():
    settings = get_settings(settings_collection)
    creds = get_credentials()
    events = get_events(creds, lookahead_days=settings["lookahead_days"])
    free_blocks = compute_free_blocks(
        events,
        day_start=settings["day_start"],
        day_end=settings["day_end"],
        tz_str=settings["timezone"],
        lookahead_days=settings["lookahead_days"],
    )

    schedulable_tasks = [
        serialize(t)
        for t in tasks_collection.find({"status": {"$in": ["pending", "unschedulable"]}})
    ]
    if not schedulable_tasks:
        raise HTTPException(status_code=400, detail="No pending tasks to schedule")

    subject_actuals_cache: dict[str, list[int]] = {}
    for t in schedulable_tasks:
        subject = t["subject"]
        if subject not in subject_actuals_cache:
            subject_actuals_cache[subject] = compute_subject_actuals(tasks_collection, subject)
        estimate, learned = weighted_estimate(t["estimated_minutes"], subject_actuals_cache[subject])
        t["adjusted_minutes"] = round(estimate)
        t["estimate_learned"] = learned
        t["estimate_sample_size"] = len(subject_actuals_cache[subject])

    assignments, unfit_ids = assign_tasks(
        schedulable_tasks,
        free_blocks,
        max_continuous_minutes=settings["max_continuous_minutes"],
        max_subjects_per_day=settings["max_subjects_per_day"],
    )

    task_lookup = {t["id"]: t for t in schedulable_tasks}

    for task_id, block in assignments.items():
        task = task_lookup[task_id]
        gcal_id = create_gcal_event(
            creds,
            title=task["title"],
            start_iso=block["start"],
            end_iso=block["end"],
        )
        tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "status": "scheduled",
                "scheduled_blocks": [block],
                "gcal_event_id": gcal_id,
                "estimated_minutes_used": task["adjusted_minutes"],
                "estimate_basis": "historical" if task["estimate_learned"] else "user",
                "estimate_sample_size": task["estimate_sample_size"],
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
