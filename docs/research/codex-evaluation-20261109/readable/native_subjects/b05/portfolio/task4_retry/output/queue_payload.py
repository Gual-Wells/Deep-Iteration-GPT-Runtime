"""Create immutable submission material and copy it for unknown-result retries."""

import base64
import copy
import hashlib


def prepare(image_bytes, description):
    if not isinstance(image_bytes, bytes):
        raise ValueError("image_bytes must be bytes")
    if description is not None and not isinstance(description, str):
        raise ValueError("description must be str or None")

    text = "" if description is None else description
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if len(text) > 2000:
        raise ValueError("description exceeds 2000 Unicode code points")

    return {
        "schema": 1,
        "image": {
            "base64": base64.b64encode(image_bytes).decode("ascii"),
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
        },
        "description": {
            "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
    }


def retry(snapshot, live_description):
    return copy.deepcopy(snapshot)
