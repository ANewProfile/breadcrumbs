from datetime import datetime, timezone
from auth.google_auth import get_credentials_for_user, revoke_credentials
from services.calendar_write import delete_gcal_event


def cleanup_future_gcal_events(tasks_collection, users_collection, user: dict) -> None:
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
    try:
        creds = get_credentials_for_user(user, users_collection)
        revoke_credentials(creds)
    except ValueError:
        pass  # already disconnected / nothing to revoke


def disconnect_google(users_collection, user: dict) -> None:
    revoke_google_grant(users_collection, user)
    users_collection.update_one({"_id": user["_id"]}, {"$unset": {"google_credentials": ""}})


def delete_all_task_data(tasks_collection, settings_collection, user_id) -> None:
    tasks_collection.delete_many({"user_id": user_id})
    settings_collection.delete_one({"_id": user_id})


def delete_account(users_collection, tasks_collection, settings_collection, sessions_collection, user_id) -> None:
    tasks_collection.delete_many({"user_id": user_id})
    settings_collection.delete_one({"_id": user_id})
    sessions_collection.delete_many({"user_id": user_id})
    users_collection.delete_one({"_id": user_id})
