from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from database import tasks_collection
from utils import serialize
from datetime import date, datetime, timezone
from typing import Literal
from auth.google_auth import get_credentials
from services.calendar_write import delete_gcal_event

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
    actual_minutes: int


@router.post("", status_code=201)
def create_task(body: TaskIn):
    doc = {
        **body.model_dump(exclude={"due_date"}),
        "due_date": body.due_date.isoformat() if body.due_date else None,
        "actual_minutes": [],
        "status": "pending",
        "scheduled_blocks": [],
        "created_at": datetime.now(timezone.utc),
    }
    result = tasks_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
def list_tasks(status: str | None = None):
    query = {"status": status} if status else {"status": {"$ne": "done"}}
    return [serialize(t) for t in tasks_collection.find(query)]


@router.patch("/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "due_date" in updates:
        updates["due_date"] = updates["due_date"].isoformat()
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = tasks_collection.find_one_and_update(
        {"_id": ObjectId(task_id)},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize(result)


@router.patch("/{task_id}/complete")
def complete_task(task_id: str, body: CompleteIn):
    result = tasks_collection.find_one_and_update(
        {"_id": ObjectId(task_id)},
        {"$set": {"status": "done"}, "$push": {"actual_minutes": body.actual_minutes}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return serialize(result)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str):
    task = tasks_collection.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    gcal_event_id = task.get("gcal_event_id")
    scheduled_blocks = task.get("scheduled_blocks") or []
    if gcal_event_id and scheduled_blocks:
        block_end = datetime.fromisoformat(scheduled_blocks[-1]["end"])
        if block_end > datetime.now(timezone.utc):
            creds = get_credentials()
            delete_gcal_event(creds, gcal_event_id)

    tasks_collection.delete_one({"_id": ObjectId(task_id)})
