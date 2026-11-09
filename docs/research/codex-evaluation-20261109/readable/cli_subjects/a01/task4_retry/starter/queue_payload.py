"""Defective starter. Repair into output/queue_payload.py."""
import base64
import hashlib

def prepare(image_bytes, description):
    text = (description or "").strip()
    if len(text.encode("utf-8")) > 2000:
        raise ValueError("description too long")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return {"schema": 1,
            "image": {"base64": base64.b64encode(image_bytes).decode("ascii"),
                      "sha256": hashlib.sha256(image_bytes).hexdigest()},
            "description": {"text": text, "sha256": digest}}

def retry(snapshot, live_description):
    image_bytes = base64.b64decode(snapshot["image"]["base64"])
    snapshot.update(prepare(image_bytes, live_description))
    return snapshot
