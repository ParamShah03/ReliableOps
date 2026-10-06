from __future__ import annotations

import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.entities import Memory
from app.tools.mock_loader import load_json


def upsert_memory(db: Session, run_id: str, memory_type: str, key: str, value: dict) -> Memory:
    memory = db.scalar(
        select(Memory).where(Memory.run_id == run_id, Memory.memory_type == memory_type, Memory.key == key)
    )
    if memory:
        memory.value = value
        return memory
    memory = Memory(run_id=run_id, memory_type=memory_type, key=key, value=value)
    db.add(memory)
    return memory


def retrieve_similar_incidents(text: str, limit: int = 2) -> list[dict]:
    tokens = set(re.findall(r"[a-z0-9_-]+", text.lower()))
    scored: list[tuple[int, dict]] = []
    for incident in load_json("incidents/known_incidents.json"):
        haystack = f"{incident['title']} {incident['summary']} {incident['root_cause']}".lower()
        score = sum(1 for token in tokens if token in haystack)
        scored.append((score, incident))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item for score, item in scored[:limit] if score > 0]
