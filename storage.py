import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import imagehash
from PIL import Image

MAPS_DIR = Path(__file__).parent / "maps"
MAPS_DIR.mkdir(exist_ok=True)


def compute_phash(screenshot_bytes: bytes) -> str:
    """Compute perceptual hash from screenshot bytes."""
    img = Image.open(io.BytesIO(screenshot_bytes))
    return str(imagehash.phash(img))


def save_map(map_data: dict) -> str:
    """Save map to disk, return map_id."""
    map_id = map_data["map_id"]
    path = MAPS_DIR / f"{map_id}.json"
    with open(path, "w") as f:
        json.dump(map_data, f, indent=2)
    return map_id


def load_map(map_id: str) -> dict | None:
    """Load map from disk by ID."""
    path = MAPS_DIR / f"{map_id}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def list_maps() -> list[dict]:
    """Return summaries of all stored maps."""
    summaries = []
    for path in MAPS_DIR.glob("*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            summaries.append({
                "map_id": data["map_id"],
                "source": data.get("source", ""),
                "timestamp": data.get("timestamp", ""),
                "element_count": len(data.get("elements", [])),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return summaries


def find_matching_map(phash: str, threshold: int = 8) -> dict | None:
    """Find stored map with perceptual hash within hamming distance threshold."""
    target = imagehash.hex_to_hash(phash)
    best_match = None
    best_distance = threshold + 1

    for path in MAPS_DIR.glob("*.json"):
        try:
            with open(path) as f:
                data = json.load(f)
            stored_phash = data.get("phash")
            if not stored_phash:
                continue
            distance = target - imagehash.hex_to_hash(stored_phash)
            if distance < best_distance:
                best_distance = distance
                best_match = data
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    if best_match is None:
        return None
    return {**best_match, "_distance": best_distance}
