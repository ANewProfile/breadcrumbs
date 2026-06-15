from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from database import tasks_collection
from utils import serialize
from datetime import datetime, timezone

router = APIRouter()


class TaskIn(BaseModel):
    title: str
    subject: str
    estimated_minutes: int


class TaskUpdate(BaseModel):
    title: str | None = None
    subject: str | None = None
    estimated_minutes: int | None = None
    status: str | None = None


class CompleteIn(BaseModel):
    actual_minutes: int


@router.post("", status_code=201)
def create_task(body: TaskIn):
    doc = {
        **body.model_dump(),
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
    result = tasks_collection.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
