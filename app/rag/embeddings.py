from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from app.core.config import get_settings


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> list[float]: ...


class LocalHashEmbeddingClient:
    """Deterministic local embedding for zero-key demos and tests.

    It is intentionally simple, but produces stable vectors and keeps the
    storage/retrieval architecture identical to a hosted embedding provider.
    """

    def __init__(self, dimension: int | None = None):
        self.dimension = dimension or get_settings().embedding_dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9_-]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


def get_embedding_client() -> EmbeddingClient:
    return LocalHashEmbeddingClient()
