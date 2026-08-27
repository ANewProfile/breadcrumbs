# backend/database.py
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import os

load_dotenv()

_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
_use_tls = _uri.startswith("mongodb+srv://")

client = MongoClient(
    _uri,
    tls=_use_tls,
    tlsCAFile=certifi.where() if _use_tls else None,
)
db = client["breadcrumbs"]

# create collections
tasks_collection = db["tasks"]
settings_collection = db["settings"]
users_collection = db["users"]
sessions_collection = db["sessions"]
school_schedule_collection = db["school_schedules"]
