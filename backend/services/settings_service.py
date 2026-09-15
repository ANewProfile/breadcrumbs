DEFAULT_SETTINGS = {
    "day_start": "08:00",
    "day_end": "22:00",
    "timezone": "America/New_York",
    "max_continuous_minutes": 90,
    "max_subjects_per_day": 3,
    "max_daily_minutes": 240,
    "lookahead_days": 7,
    "time_tracking_mode": "manual",
    "break_between_tasks_minutes": 0,
    "break_between_subjects_minutes": 0,
    "preferred_time_of_day": "no_preference",
    "selected_calendar_ids": ["primary"],
}


def get_settings(settings_collection, user_id) -> dict:
    """Each user has their own settings document, keyed by their own _id."""
    doc = settings_collection.find_one({"_id": user_id})
    merged = dict(DEFAULT_SETTINGS)
    if doc:
        merged.update({k: v for k, v in doc.items() if k != "_id"})
    return merged


def update_settings(settings_collection, user_id, updates: dict) -> dict:
    if updates:
        settings_collection.update_one(
            {"_id": user_id}, {"$set": updates}, upsert=True
        )
    return get_settings(settings_collection, user_id)
