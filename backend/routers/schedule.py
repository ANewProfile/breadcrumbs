from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from auth.session import get_current_user
from auth.google_auth import get_credentials_for_user
from services.calendar_service import get_events
from services.get_free_blocks import compute_free_blocks
from services.scheduler import assign_tasks
from services.calendar_write import create_gcal_event, update_gcal_event, delete_gcal_event
from services.estimation import compute_subject_history, weighted_estimate
from services.settings_service import get_settings
from database import tasks_collection, settings_collection, users_collection, no_go_zones_collection
from utils import serialize
from rate_limit import rate_limit

router = APIRouter()


def _dev_fake_busy_events(user_id) -> list[dict]:
    """
    Dev users have no real Google Calendar for get_events() to read, but their
    already-scheduled tasks still need to show up as busy time — otherwise a
    run that only touches a subset of tasks (e.g. reschedule-missed) has no
    way to know another dev task already occupies a slot, and happily
    double-books it. Synthesizes the same shape get_events() returns, from
    this dev user's own scheduled tasks.
    """
    events = []
    for t in tasks_collection.find({"user_id": user_id, "status": "scheduled"}):
        blocks = t.get("scheduled_blocks") or []
        gcal_id = t.get("gcal_event_id")
        if not blocks or not gcal_id:
            continue
        events.append({
            "id": gcal_id,
            "start": {"dateTime": blocks[0]["start"]},
            "end": {"dateTime": blocks[0]["end"]},
        })
    return events


def _google_state(user: dict, is_dev_user: bool, settings: dict):
    """Returns (creds, events). Dev users have no real Google account, so
    their busy time is faked from their own already-scheduled tasks instead."""
    if is_dev_user:
        return None, _dev_fake_busy_events(user["_id"])
    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Please reconnect your Google Calendar in Settings before running the scheduler.",
        )
    events = get_events(creds, lookahead_days=settings["lookahead_days"])
    return creds, events


def _with_estimates(tasks: list[dict], user_id) -> list[dict]:
    subject_history_cache: dict[str, list[dict]] = {}
    for t in tasks:
        subject = t["subject"]
        if subject not in subject_history_cache:
            subject_history_cache[subject] = compute_subject_history(tasks_collection, user_id, subject)
        estimate, learned = weighted_estimate(t["estimated_minutes"], subject_history_cache[subject])
        t["adjusted_minutes"] = round(estimate)
        t["estimate_learned"] = learned
        t["estimate_sample_size"] = len(subject_history_cache[subject])
        t["estimate_ratio"] = round(estimate / t["estimated_minutes"], 2) if t["estimated_minutes"] else 1.0
    return tasks


def _is_missed(task: dict) -> bool:
    """A "scheduled" task whose block already ended without the task being
    marked done — the user missed it."""
    blocks = task.get("scheduled_blocks") or []
    if not blocks:
        return False
    return datetime.fromisoformat(blocks[0]["end"]) < datetime.now(timezone.utc)


def _apply_assignments(
    user_id,
    task_lookup: dict[str, dict],
    assignments: dict[str, dict],
    unfit_ids: list[str],
    creds,
    is_dev_user: bool,
) -> None:
    for task_id, block in assignments.items():
        task = task_lookup[task_id]
        existing_event_id = task.get("gcal_event_id")
        # Dev fake user has no real Google credentials to write with, and the
        # whole point of dev-login is to preview scheduling without touching
        # a real calendar — so skip the actual Google Calendar API call. Each
        # task gets its own fake id (not a shared literal) so _dev_fake_busy_events
        # and the own-event exclusion below can tell tasks apart.
        if is_dev_user:
            gcal_id = existing_event_id or f"dev-fake-{task_id}"
        elif existing_event_id:
            # Already on the calendar from a previous run — move it rather
            # than creating a second, duplicate event.
            update_gcal_event(creds, existing_event_id, start_iso=block["start"], end_iso=block["end"])
            gcal_id = existing_event_id
        else:
            gcal_id = create_gcal_event(
                creds,
                title=task["title"],
                start_iso=block["start"],
                end_iso=block["end"],
            )
        tasks_collection.update_one(
            {"_id": ObjectId(task_id), "user_id": user_id},
            {"$set": {
                "status": "scheduled",
                "scheduled_blocks": [block],
                "gcal_event_id": gcal_id,
                "estimated_minutes_used": task["adjusted_minutes"],
                "estimate_basis": "historical" if task["estimate_learned"] else "user",
                "estimate_sample_size": task["estimate_sample_size"],
                "estimate_ratio": task["estimate_ratio"],
            }},
        )

    for task_id in unfit_ids:
        task = task_lookup[task_id]
        existing_event_id = task.get("gcal_event_id")
        # A task that was scheduled before but got bumped out this run no
        # longer has a slot, so its old calendar event is stale — remove it
        # rather than leaving a phantom event behind.
        if existing_event_id and not is_dev_user:
            delete_gcal_event(creds, existing_event_id)
        tasks_collection.update_one(
            {"_id": ObjectId(task_id), "user_id": user_id},
            {
                "$set": {"status": "unschedulable", "scheduled_blocks": []},
                "$unset": {"gcal_event_id": ""},
            },
        )


@router.post("/run", dependencies=[Depends(rate_limit("15/minute"))])
def run_schedule(user: dict = Depends(get_current_user)):
    settings = get_settings(settings_collection, user["_id"])
    is_dev_user = bool(user.get("is_dev_user"))
    creds, events = _google_state(user, is_dev_user, settings)
    no_go_zones = list(no_go_zones_collection.find({"user_id": user["_id"]}))

    # Every run re-optimizes the full set of not-yet-done tasks, not just ones
    # added since the last run — otherwise adding a new urgent task could
    # never bump an already-scheduled one out of its slot.
    schedulable_tasks = [
        serialize(t)
        for t in tasks_collection.find(
            {"user_id": user["_id"], "status": {"$in": ["pending", "unschedulable", "scheduled"]}}
        )
    ]
    if not schedulable_tasks:
        raise HTTPException(status_code=400, detail="No pending tasks to schedule")

    # A task already scheduled from a previous run holds its own real Google
    # Calendar event, which would otherwise show up as busy time and block the
    # task from ever being moved (it would collide with itself). These tasks
    # are ours to move, so exclude their own events from the free/busy read.
    own_event_ids = {t["gcal_event_id"] for t in schedulable_tasks if t.get("gcal_event_id")}
    if own_event_ids:
        events = [e for e in events if e.get("id") not in own_event_ids]

    free_blocks = compute_free_blocks(
        events,
        day_start=settings["day_start"],
        day_end=settings["day_end"],
        tz_str=settings["timezone"],
        lookahead_days=settings["lookahead_days"],
        no_go_zones=no_go_zones,
    )

    schedulable_tasks = _with_estimates(schedulable_tasks, user["_id"])

    assignments, unfit_ids = assign_tasks(
        schedulable_tasks,
        free_blocks,
        max_continuous_minutes=settings["max_continuous_minutes"],
        max_subjects_per_day=settings["max_subjects_per_day"],
        break_between_tasks_minutes=settings["break_between_tasks_minutes"],
        break_between_subjects_minutes=settings["break_between_subjects_minutes"],
    )

    task_lookup = {t["id"]: t for t in schedulable_tasks}
    _apply_assignments(user["_id"], task_lookup, assignments, unfit_ids, creds, is_dev_user)

    return {
        "free_blocks": [
            {**b, "start": b["start"].isoformat(), "end": b["end"].isoformat()}
            for b in free_blocks
        ],
        "assignments": assignments,
        "unfit_ids": unfit_ids,
    }


@router.post("/reschedule-missed", dependencies=[Depends(rate_limit("15/minute"))])
def reschedule_missed(user: dict = Depends(get_current_user)):
    """
    Finds tasks that were scheduled into a block that has already passed
    without being marked done — e.g. the user missed a task — and finds each
    one a fresh, future slot. Scoped to just those tasks, so it doesn't
    reshuffle everything else already correctly scheduled the way a full
    /run does.
    """
    settings = get_settings(settings_collection, user["_id"])
    is_dev_user = bool(user.get("is_dev_user"))
    creds, events = _google_state(user, is_dev_user, settings)
    no_go_zones = list(no_go_zones_collection.find({"user_id": user["_id"]}))

    scheduled_tasks = [
        serialize(t)
        for t in tasks_collection.find({"user_id": user["_id"], "status": "scheduled"})
    ]
    missed_tasks = [t for t in scheduled_tasks if _is_missed(t)]
    if not missed_tasks:
        raise HTTPException(status_code=400, detail="No missed tasks to reschedule")

    # Each missed task's own event already ended in the past, before the
    # free/busy window even starts, so it never shows up as busy — no need to
    # exclude it the way a full /run does for still-future scheduled tasks.
    free_blocks = compute_free_blocks(
        events,
        day_start=settings["day_start"],
        day_end=settings["day_end"],
        tz_str=settings["timezone"],
        lookahead_days=settings["lookahead_days"],
        no_go_zones=no_go_zones,
    )

    missed_tasks = _with_estimates(missed_tasks, user["_id"])

    assignments, unfit_ids = assign_tasks(
        missed_tasks,
        free_blocks,
        max_continuous_minutes=settings["max_continuous_minutes"],
        max_subjects_per_day=settings["max_subjects_per_day"],
        break_between_tasks_minutes=settings["break_between_tasks_minutes"],
        break_between_subjects_minutes=settings["break_between_subjects_minutes"],
    )

    task_lookup = {t["id"]: t for t in missed_tasks}
    _apply_assignments(user["_id"], task_lookup, assignments, unfit_ids, creds, is_dev_user)

    return {
        "free_blocks": [
            {**b, "start": b["start"].isoformat(), "end": b["end"].isoformat()}
            for b in free_blocks
        ],
        "assignments": assignments,
        "unfit_ids": unfit_ids,
    }
