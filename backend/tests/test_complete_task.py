from unittest.mock import patch
from bson import ObjectId
from routers.tasks import complete_task, CompleteIn

TASK_ID = "507f1f77bcf86cd799439011"
USER = {"_id": ObjectId()}


@patch("routers.tasks.tasks_collection")
def test_complete_with_actual_minutes_pushes_value(mock_collection):
    mock_collection.find_one_and_update.return_value = {"_id": TASK_ID, "status": "done"}

    complete_task(TASK_ID, CompleteIn(actual_minutes=45), USER)

    args, _ = mock_collection.find_one_and_update.call_args
    update = args[1]
    assert update["$push"] == {"actual_minutes": 45}
    assert update["$set"]["status"] == "done"
    assert "completed_at" in update["$set"]


@patch("routers.tasks.tasks_collection")
def test_complete_without_actual_minutes_skips_push(mock_collection):
    mock_collection.find_one_and_update.return_value = {"_id": TASK_ID, "status": "done"}

    complete_task(TASK_ID, CompleteIn(actual_minutes=None), USER)

    args, _ = mock_collection.find_one_and_update.call_args
    update = args[1]
    assert "$push" not in update
    assert update["$set"]["status"] == "done"
    assert "completed_at" in update["$set"]
