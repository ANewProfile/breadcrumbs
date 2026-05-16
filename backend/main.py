# backend/main.py
from fastapi import FastAPI
from database import tasks_collection

app = FastAPI()

@app.get("/test")
def test():
    tasks_collection.insert_one({"test": True})
    document_count = tasks_collection.count_documents({})
    return {"document_count": document_count}
