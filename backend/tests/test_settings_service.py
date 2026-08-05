from unittest.mock import MagicMock
from bson import ObjectId
from services.settings_service import get_settings, update_settings, DEFAULT_SETTINGS

USER_ID = ObjectId()


def test_get_settings_returns_defaults_when_no_doc_exists():
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None

    settings = get_settings(mock_collection, USER_ID)

    assert settings == DEFAULT_SETTINGS
    mock_collection.find_one.assert_called_once_with({"_id": USER_ID})


def test_get_settings_merges_stored_overrides_onto_defaults():
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"_id": USER_ID, "day_start": "09:00"}

    settings = get_settings(mock_collection, USER_ID)

    assert settings["day_start"] == "09:00"
    assert settings["day_end"] == DEFAULT_SETTINGS["day_end"]
    assert "_id" not in settings


def test_get_settings_scoped_per_user():
    other_user_id = ObjectId()
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None

    get_settings(mock_collection, other_user_id)

    mock_collection.find_one.assert_called_once_with({"_id": other_user_id})


def test_update_settings_upserts_and_returns_merged_settings():
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = {"_id": USER_ID, "day_start": "09:00"}

    result = update_settings(mock_collection, USER_ID, {"day_start": "09:00"})

    mock_collection.update_one.assert_called_once_with(
        {"_id": USER_ID}, {"$set": {"day_start": "09:00"}}, upsert=True
    )
    assert result["day_start"] == "09:00"


def test_update_settings_with_no_updates_skips_write():
    mock_collection = MagicMock()
    mock_collection.find_one.return_value = None

    update_settings(mock_collection, USER_ID, {})

    mock_collection.update_one.assert_not_called()
