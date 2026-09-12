import pytest
from pydantic import ValidationError
from routers.settings import SettingsUpdate


def test_valid_settings_pass_validation():
    body = SettingsUpdate(
        day_start="09:00",
        day_end="21:30",
        timezone="America/Los_Angeles",
        max_continuous_minutes=60,
        max_subjects_per_day=2,
        max_daily_minutes=180,
        lookahead_days=14,
    )
    assert body.day_start == "09:00"
    assert body.timezone == "America/Los_Angeles"


def test_partial_update_leaves_other_fields_none():
    body = SettingsUpdate(day_start="09:00")
    assert body.day_start == "09:00"
    assert body.day_end is None


@pytest.mark.parametrize("bad_time", ["9:00", "25:00", "09:60", "morning", ""])
def test_invalid_time_format_rejected(bad_time):
    with pytest.raises(ValidationError):
        SettingsUpdate(day_start=bad_time)


def test_invalid_timezone_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(timezone="Not/A_Real_Zone")


@pytest.mark.parametrize("field", ["max_continuous_minutes", "max_subjects_per_day", "max_daily_minutes", "lookahead_days"])
def test_non_positive_numbers_rejected(field):
    with pytest.raises(ValidationError):
        SettingsUpdate(**{field: 0})
    with pytest.raises(ValidationError):
        SettingsUpdate(**{field: -5})


@pytest.mark.parametrize("mode", ["manual", "automatic"])
def test_valid_time_tracking_mode_accepted(mode):
    body = SettingsUpdate(time_tracking_mode=mode)
    assert body.time_tracking_mode == mode


def test_invalid_time_tracking_mode_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(time_tracking_mode="stopwatch")


@pytest.mark.parametrize("preference", ["no_preference", "morning", "afternoon", "evening"])
def test_valid_preferred_time_of_day_accepted(preference):
    body = SettingsUpdate(preferred_time_of_day=preference)
    assert body.preferred_time_of_day == preference


def test_invalid_preferred_time_of_day_rejected():
    with pytest.raises(ValidationError):
        SettingsUpdate(preferred_time_of_day="whenever")
