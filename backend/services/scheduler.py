from datetime import timedelta


def assign_tasks(tasks: list, free_blocks: list) -> tuple[dict, list]:
    tasks_sorted = sorted(tasks, key=lambda t: t["subject"])
    blocks = [dict(b) for b in free_blocks]
    assignments = {}
    unfit_ids = []

    for task in tasks_sorted:
        needed = task["estimated_minutes"]
        for block in blocks:
            if block["duration_min"] >= needed:
                end_dt = block["start"] + timedelta(minutes=needed)
                assignments[task["id"]] = {
                    "start": block["start"].isoformat(),
                    "end": end_dt.isoformat(),
                }
                block["start"] = end_dt
                block["duration_min"] -= needed
                break
        else:
            unfit_ids.append(task["id"])

    return assignments, unfit_ids
