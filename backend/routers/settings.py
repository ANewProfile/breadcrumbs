import re
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from database import settings_collection
from auth.session import get_current_user
from services.settings_service import get_settings, update_settings

router = APIRouter()

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class SettingsUpdate(BaseModel):
    day_start: str | None = None
    day_end: str | None = None
    timezone: str | None = None
    max_continuous_minutes: int | None = None
    max_subjects_per_day: int | None = None
    lookahead_days: int | None = None
    time_tracking_mode: Literal["manual", "automatic"] | None = None

    @field_validator("day_start", "day_end")
    @classmethod
    def validate_time(cls, v):
        if v is not None and not TIME_RE.match(v):
            raise ValueError("must be in 24-hour HH:MM format")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v):
        if v is not None:
            try:
                ZoneInfo(v)
            except ZoneInfoNotFoundError:
                raise ValueError(f"unknown IANA timezone: {v}")
        return v

    @field_validator("max_continuous_minutes", "max_subjects_per_day", "lookahead_days")
    @classmethod
    def validate_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("must be a positive number")
        return v


@router.get("")
def read_settings(user: dict = Depends(get_current_user)):
    return get_settings(settings_collection, user["_id"])


@router.patch("")
def patch_settings(body: SettingsUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    return update_settings(settings_collection, user["_id"], updates)
