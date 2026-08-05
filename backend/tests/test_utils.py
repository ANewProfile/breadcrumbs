from bson import ObjectId
from utils import serialize


def test_serialize_converts_id_and_strips_user_id():
    doc = {"_id": ObjectId(), "user_id": ObjectId(), "title": "Some task"}

    result = serialize(doc)

    assert isinstance(result["id"], str)
    assert "user_id" not in result
    assert "_id" not in result
    assert result["title"] == "Some task"


def test_serialize_handles_missing_user_id():
    doc = {"_id": ObjectId(), "title": "Some task"}

    result = serialize(doc)

    assert isinstance(result["id"], str)
    assert "user_id" not in result
