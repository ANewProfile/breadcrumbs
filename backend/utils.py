def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc
