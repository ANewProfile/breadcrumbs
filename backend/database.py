# backend/database.py
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import os

load_dotenv()

client = MongoClient(
    os.getenv("MONGODB_URI"),
    tls=True,
    tlsCAFile=certifi.where(),
)
db = client["breadcrumbs"]

# create collections
tasks_collection = db["tasks"]
settings_collection = db["settings"]
