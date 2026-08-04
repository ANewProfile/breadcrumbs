def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc.pop("user_id", None)  # internal ownership field, not part of the API response
    return doc
