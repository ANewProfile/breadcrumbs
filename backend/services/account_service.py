from datetime import datetime, timezone
from auth.google_auth import get_credentials_for_user, revoke_credentials
from services.calendar_write import delete_gcal_event


def cleanup_future_gcal_events(tasks_collection, users_collection, user: dict) -> None:
    """
    Before wiping a user's tasks, remove the real calendar events for any that
    are still upcoming — mirrors the single-task delete policy (past events are
    left alone as history). Best-effort: if credentials are missing/invalid,
    there's nothing we can clean up, so proceed without one.
    """
    tasks = list(
        tasks_collection.find(
            {"user_id": user["_id"], "gcal_event_id": {"$exists": True, "$ne": None}}
        )
    )
    if not tasks:
        return

    try:
        creds = get_credentials_for_user(user, users_collection)
    except ValueError:
        return

    now = datetime.now(timezone.utc)
    for task in tasks:
        blocks = task.get("scheduled_blocks") or []
        if not blocks:
            continue
        block_end = datetime.fromisoformat(blocks[-1]["end"])
        if block_end > now:
            delete_gcal_event(creds, task["gcal_event_id"])


def revoke_google_grant(users_collection, user: dict) -> None:
    """
    Tells Google to forget this grant. Does not touch the local user doc —
    use this (instead of disconnect_google) when the user doc is about to be
    deleted anyway, so we don't write a field we're seconds away from erasing.
    """
    try:
        creds = get_credentials_for_user(user, users_collection)
        revoke_credentials(creds)
    except ValueError:
        pass  # already disconnected / nothing to revoke


def disconnect_google(users_collection, user: dict) -> None:
    """Revokes the grant with Google and forgets the stored credentials locally."""
    revoke_google_grant(users_collection, user)
    users_collection.update_one({"_id": user["_id"]}, {"$unset": {"google_credentials": ""}})


def delete_all_task_data(tasks_collection, settings_collection, user_id) -> None:
    """Wipes tasks and settings for a user, but keeps their account/login intact."""
    tasks_collection.delete_many({"user_id": user_id})
    settings_collection.delete_one({"_id": user_id})


def delete_account(users_collection, tasks_collection, settings_collection, sessions_collection, user_id) -> None:
    """Full account deletion: tasks, settings, all sessions, and the user record itself."""
    tasks_collection.delete_many({"user_id": user_id})
    settings_collection.delete_one({"_id": user_id})
    sessions_collection.delete_many({"user_id": user_id})
    users_collection.delete_one({"_id": user_id})
