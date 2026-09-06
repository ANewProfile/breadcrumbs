from unittest.mock import patch, MagicMock
import pytest
from bson import ObjectId
from pydantic import ValidationError
from fastapi import HTTPException
from routers.no_go_zones import NoGoZoneIn, create_no_go_zone, list_no_go_zones, delete_no_go_zone

USER = {"_id": ObjectId()}
ZONE_ID = "507f1f77bcf86cd799439011"


@patch("routers.no_go_zones.no_go_zones_collection")
def test_create_recurring_zone_stores_and_serializes(mock_collection):
    mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId())
    captured = {}
    mock_collection.insert_one.side_effect = lambda doc: captured.update(doc) or MagicMock(inserted_id=ObjectId())
    body = NoGoZoneIn(label="Lunch", start_time="12:00", end_time="13:00")

    result = create_no_go_zone(body, USER)

    assert captured["user_id"] == USER["_id"]
    assert captured["date"] is None
    assert result["label"] == "Lunch"
    assert "user_id" not in result
    assert result["id"]


@patch("routers.no_go_zones.no_go_zones_collection")
def test_create_one_off_zone_stores_iso_date(mock_collection):
    captured = {}
    mock_collection.insert_one.side_effect = lambda doc: captured.update(doc) or MagicMock(inserted_id=ObjectId())
    body = NoGoZoneIn(label="Dentist", start_time="14:00", end_time="15:00", date="2026-09-10")

    create_no_go_zone(body, USER)

    assert captured["date"] == "2026-09-10"
    assert captured["days_of_week"] is None


@patch("routers.no_go_zones.no_go_zones_collection")
def test_list_no_go_zones_scoped_to_user(mock_collection):
    mock_collection.find.return_value = []

    list_no_go_zones(USER)

    mock_collection.find.assert_called_once_with({"user_id": USER["_id"]})


@patch("routers.no_go_zones.no_go_zones_collection")
def test_delete_no_go_zone_removes(mock_collection):
    mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

    delete_no_go_zone(ZONE_ID, USER)

    mock_collection.delete_one.assert_called_once_with(
        {"_id": ObjectId(ZONE_ID), "user_id": USER["_id"]}
    )


@patch("routers.no_go_zones.no_go_zones_collection")
def test_delete_nonexistent_zone_raises_404(mock_collection):
    mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

    with pytest.raises(HTTPException) as exc_info:
        delete_no_go_zone(ZONE_ID, USER)

    assert exc_info.value.status_code == 404


@pytest.mark.parametrize("bad_time", ["9:00", "25:00", "09:60", "noon"])
def test_invalid_time_format_rejected(bad_time):
    with pytest.raises(ValidationError):
        NoGoZoneIn(label="X", start_time=bad_time, end_time="13:00")


def test_end_before_start_rejected():
    with pytest.raises(ValidationError):
        NoGoZoneIn(label="X", start_time="13:00", end_time="12:00")


def test_date_and_days_of_week_mutually_exclusive():
    with pytest.raises(ValidationError):
        NoGoZoneIn(label="X", start_time="12:00", end_time="13:00", date="2026-09-10", days_of_week=[0, 1])


def test_days_of_week_out_of_range_rejected():
    with pytest.raises(ValidationError):
        NoGoZoneIn(label="X", start_time="12:00", end_time="13:00", days_of_week=[0, 7])


def test_empty_days_of_week_alongside_date_is_allowed():
    # An empty list is falsy, so it shouldn't trip the mutual-exclusivity check.
    body = NoGoZoneIn(label="X", start_time="12:00", end_time="13:00", date="2026-09-10", days_of_week=[])
    assert body.date is not None
