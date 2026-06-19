# backend/services/scheduler.py
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def compute_free_blocks(events: list, day_start: str = "08:00", day_end: str = "22:00", tz_str: str = "America/New_York") -> list:
    tz = ZoneInfo(tz_str)

    busy = []
    for e in events:
        start_raw = e.get("start", {})
        end_raw = e.get("end", {})
        if "dateTime" not in start_raw:
            continue
        start = datetime.fromisoformat(start_raw["dateTime"]).astimezone(tz)
        end = datetime.fromisoformat(end_raw["dateTime"]).astimezone(tz)
        busy.append((start, end))

    if not busy:
        return []

    all_dates = [s.date() for s, _ in busy] + [e.date() for _, e in busy]
    date_min = min(all_dates)
    date_max = max(all_dates)

    now = datetime.now(tz)
    free_blocks = []
    current_date = date_min

    while current_date <= date_max:
        window_start = max(
            datetime(current_date.year, current_date.month, current_date.day,
                     int(day_start.split(":")[0]), int(day_start.split(":")[1]),
                     tzinfo=tz),
            now,
        )
        window_end = datetime(current_date.year, current_date.month, current_date.day,
                              int(day_end.split(":")[0]), int(day_end.split(":")[1]),
                              tzinfo=tz)

        day_busy = []
        for s, e in busy:
            if s < window_end and e > window_start:
                clipped_start = max(s, window_start)
                clipped_end = min(e, window_end)
                day_busy.append((clipped_start, clipped_end))

        day_busy.sort(key=lambda x: x[0])
        merged = []
        for s, e in day_busy:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))

        cursor = window_start
        for s, e in merged:
            if cursor < s:
                duration = int((s - cursor).total_seconds() / 60)
                free_blocks.append({"start": cursor, "end": s, "duration_min": duration})
            cursor = max(cursor, e)

        if cursor < window_end:
            duration = int((window_end - cursor).total_seconds() / 60)
            free_blocks.append({"start": cursor, "end": window_end, "duration_min": duration})

        current_date += timedelta(days=1)

    return free_blocks
