from datetime import datetime
from bson import ObjectId


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start


def find_conflicting_task(tasks_collection, user_id, exclude_task_id: str, new_start: datetime, new_end: datetime):
    """Returns the first other scheduled task *of this same user* whose block overlaps [new_start, new_end), or None."""
    query = {"status": "scheduled", "user_id": user_id, "_id": {"$ne": ObjectId(exclude_task_id)}}
    for t in tasks_collection.find(query):
        for block in t.get("scheduled_blocks", []):
            b_start = datetime.fromisoformat(block["start"])
            b_end = datetime.fromisoformat(block["end"])
            if overlaps(new_start, new_end, b_start, b_end):
                return t
    return None


def find_conflicting_gcal_event(events: list, exclude_event_id: str | None, new_start: datetime, new_end: datetime):
    """
    Returns the first real Google Calendar event that overlaps [new_start, new_end),
    excluding the task's own existing event (which is the one being moved).
    All-day events (no "dateTime") are skipped, consistent with compute_free_blocks.
    """
    for e in events:
        if exclude_event_id and e.get("id") == exclude_event_id:
            continue
        start_raw = e.get("start", {})
        end_raw = e.get("end", {})
        if "dateTime" not in start_raw:
            continue
        e_start = datetime.fromisoformat(start_raw["dateTime"])
        e_end = datetime.fromisoformat(end_raw["dateTime"])
        if overlaps(new_start, new_end, e_start, e_end):
            return e
    return None
