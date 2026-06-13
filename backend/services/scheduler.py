from datetime import timedelta


def assign_tasks(tasks: list, free_blocks: list) -> dict:
    tasks_sorted = sorted(tasks, key=lambda t: t["subject"])
    blocks = [dict(b) for b in free_blocks]
    assignments = {}

    for task in tasks_sorted:
        needed = task["estimated_minutes"]
        for block in blocks:
            if block["duration_min"] >= needed:
                end_dt = block["start"] + timedelta(minutes=needed)
                assignments[task["_id"]] = {
                    "start": block["start"].isoformat(),
                    "end": end_dt.isoformat(),
                }
                block["start"] = end_dt
                block["duration_min"] -= needed
                break

    return assignments
