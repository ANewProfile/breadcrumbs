import re
import datetime as datetime_module
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator, model_validator
from bson import ObjectId
from database import no_go_zones_collection
from auth.session import get_current_user
from utils import serialize

router = APIRouter()

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class NoGoZoneIn(BaseModel):
    label: str
    start_time: str
    end_time: str
    date: datetime_module.date | None = None
    days_of_week: list[int] | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v):
        if not TIME_RE.match(v):
            raise ValueError("must be in 24-hour HH:MM format")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v):
        if v is not None and any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week entries must be between 0 (Mon) and 6 (Sun)")
        return v

    @model_validator(mode="after")
    def validate_shape(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.date is not None and self.days_of_week:
            raise ValueError("date and days_of_week are mutually exclusive")
        return self


@router.post("", status_code=201)
def create_no_go_zone(body: NoGoZoneIn, user: dict = Depends(get_current_user)):
    doc = {
        **body.model_dump(exclude={"date"}),
        "date": body.date.isoformat() if body.date else None,
        "user_id": user["_id"],
    }
    result = no_go_zones_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
def list_no_go_zones(user: dict = Depends(get_current_user)):
    return [serialize(z) for z in no_go_zones_collection.find({"user_id": user["_id"]})]


@router.delete("/{zone_id}", status_code=204)
def delete_no_go_zone(zone_id: str, user: dict = Depends(get_current_user)):
    result = no_go_zones_collection.delete_one({"_id": ObjectId(zone_id), "user_id": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No-go zone not found")
