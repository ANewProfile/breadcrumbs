def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc
