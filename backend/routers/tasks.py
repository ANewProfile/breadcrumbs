from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from bson import ObjectId
from database import tasks_collection, settings_collection, users_collection
from utils import serialize
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from auth.session import get_current_user
from auth.google_auth import get_credentials_for_user
from services.calendar_write import delete_gcal_event, create_gcal_event, update_gcal_event
from services.calendar_service import get_events
from services.reschedule import find_conflicting_task, find_conflicting_gcal_event
from services.settings_service import get_settings

router = APIRouter()

Priority = Literal["low", "medium", "high"]


class TaskIn(BaseModel):
    title: str
    subject: str
    estimated_minutes: int
    due_date: date | None = None
    priority: Priority = "medium"


class TaskUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    estimated_minutes: int | None = None
    status: str | None = None
    due_date: date | None = None
    priority: Priority | None = None


class CompleteIn(BaseModel):
    actual_minutes: int | None = None


class RescheduleIn(BaseModel):
    start: datetime

    @field_validator("start")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("start must include timezone/UTC offset info")
        return v


@router.post("", status_code=201)
def create_task(body: TaskIn, user: dict = Depends(get_current_user)):
    doc = {
        **body.model_dump(exclude={"due_date"}),
        "due_date": body.due_date.isoformat() if body.due_date else None,
        "user_id": user["_id"],
        "actual_minutes": [],
        "status": "pending",
        "scheduled_blocks": [],
        "created_at": datetime.now(timezone.utc),
    }
    result = tasks_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
def list_tasks(status: str | None = None, user: dict = Depends(get_current_user)):
    query = {"user_id": user["_id"]}
    query.update({"status": status} if status else {"status": {"$ne": "done"}})
    return [serialize(t) for t in tasks_collection.find(query)]


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "due_date" in updates:
        updates["due_date"] = updates["due_date"].isoformat()
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = tasks_collection.find_one_and_update(
        {"_id": ObjectId(task_id), "user_id": user["_id"]},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize(result)


@router.patch("/{task_id}/complete")
def complete_task(task_id: str, body: CompleteIn, user: dict = Depends(get_current_user)):
    update: dict = {"$set": {"status": "done", "completed_at": datetime.now(timezone.utc)}}
    if body.actual_minutes is not None:
        update["$push"] = {"actual_minutes": body.actual_minutes}

    result = tasks_collection.find_one_and_update(
        {"_id": ObjectId(task_id), "user_id": user["_id"]},
        update,
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize(result)


@router.patch("/{task_id}/reschedule")
def reschedule_task(task_id: str, body: RescheduleIn, user: dict = Depends(get_current_user)):
    """
    Manually moves a task to a specific time — for a free slot the user knows
    about but hasn't put on their calendar. Refuses to double-book: rejects if
    the new slot overlaps another scheduled task of this user or any real Google
    Calendar event (other than the task's own event, which is what's being moved).
    """
    task = tasks_collection.find_one({"_id": ObjectId(task_id), "user_id": user["_id"]})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing_blocks = task.get("scheduled_blocks") or []
    if existing_blocks:
        old_start = datetime.fromisoformat(existing_blocks[-1]["start"])
        old_end = datetime.fromisoformat(existing_blocks[-1]["end"])
        duration_minutes = (old_end - old_start).total_seconds() / 60
    else:
        duration_minutes = task.get("estimated_minutes_used", task["estimated_minutes"])

    new_start = body.start
    new_end = new_start + timedelta(minutes=duration_minutes)

    task_conflict = find_conflicting_task(tasks_collection, user["_id"], task_id, new_start, new_end)
    if task_conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Conflicts with '{task_conflict['title']}', already scheduled at that time",
        )

    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Please reconnect your Google Calendar in Settings before moving a task.",
        )
    settings = get_settings(settings_collection, user["_id"])
    days_out = max(settings["lookahead_days"], (new_end.date() - datetime.now(timezone.utc).date()).days + 1)
    events = get_events(creds, lookahead_days=days_out)
    gcal_event_id = task.get("gcal_event_id")
    gcal_conflict = find_conflicting_gcal_event(events, gcal_event_id, new_start, new_end)
    if gcal_conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Conflicts with '{gcal_conflict.get('summary', 'a calendar event')}' on your calendar",
        )

    if gcal_event_id:
        update_gcal_event(creds, gcal_event_id, new_start.isoformat(), new_end.isoformat())
    else:
        gcal_event_id = create_gcal_event(
            creds, title=task["title"], start_iso=new_start.isoformat(), end_iso=new_end.isoformat()
        )

    result = tasks_collection.find_one_and_update(
        {"_id": ObjectId(task_id), "user_id": user["_id"]},
        {"$set": {
            "status": "scheduled",
            "scheduled_blocks": [{"start": new_start.isoformat(), "end": new_end.isoformat()}],
            "gcal_event_id": gcal_event_id,
        }},
        return_document=True,
    )
    return serialize(result)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    task = tasks_collection.find_one({"_id": ObjectId(task_id), "user_id": user["_id"]})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    gcal_event_id = task.get("gcal_event_id")
    scheduled_blocks = task.get("scheduled_blocks") or []
    if gcal_event_id and scheduled_blocks:
        block_end = datetime.fromisoformat(scheduled_blocks[-1]["end"])
        if block_end > datetime.now(timezone.utc):
            try:
                creds = get_credentials_for_user(user, users_collection)
                delete_gcal_event(creds, gcal_event_id)
            except ValueError:
                pass  # Google disconnected — nothing to clean up, don't block the local delete

    tasks_collection.delete_one({"_id": ObjectId(task_id), "user_id": user["_id"]})
