import secrets
from datetime import datetime, timedelta, timezone

SESSION_TTL_DAYS = 30


def upsert_user(users_collection, *, google_sub: str, email: str, name: str | None, picture: str | None) -> dict:
    """Finds or creates a user keyed by their stable Google account id (sub) —
    this is the only identity we have; there's no separate password to check."""
    now = datetime.now(timezone.utc)
    return users_collection.find_one_and_update(
        {"google_sub": google_sub},
        {
            "$set": {"email": email, "name": name, "picture": picture, "last_login_at": now},
            "$setOnInsert": {"google_sub": google_sub, "created_at": now},
        },
        upsert=True,
        return_document=True,
    )


def store_google_credentials(users_collection, user_id, credentials_dict: dict) -> None:
    users_collection.update_one({"_id": user_id}, {"$set": {"google_credentials": credentials_dict}})


def create_session(sessions_collection, user_id) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    sessions_collection.insert_one({
        "_id": token,
        "user_id": user_id,
        "created_at": now,
        "expires_at": now + timedelta(days=SESSION_TTL_DAYS),
    })
    return token


def get_user_for_session(sessions_collection, users_collection, token: str | None) -> dict | None:
    if not token:
        return None
    session = sessions_collection.find_one({"_id": token})
    if not session:
        return None

    # pymongo returns naive datetimes for UTC-stored values by default; reattach
    # the UTC tzinfo so this can be compared against an aware "now" safely.
    expires_at = session["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        sessions_collection.delete_one({"_id": token})
        return None

    return users_collection.find_one({"_id": session["user_id"]})


def delete_session(sessions_collection, token: str | None) -> None:
    if token:
        sessions_collection.delete_one({"_id": token})
