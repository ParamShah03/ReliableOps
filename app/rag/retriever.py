from __future__ import annotations

import math
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.entities import KnowledgeChunk, KnowledgeDocument
from app.rag.embeddings import get_embedding_client


def _cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a)) or 1.0
    db = math.sqrt(sum(y * y for y in b)) or 1.0
    return numerator / (da * db)


def search_runbook_chunks(db: Session, query: str, top_k: int = 4) -> list[dict]:
    query_vector = get_embedding_client().embed(query)

    if db.bind and db.bind.dialect.name == "postgresql":
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
        rows = db.execute(
            select(KnowledgeChunk, KnowledgeDocument, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .order_by(distance)
            .limit(top_k)
        ).all()
        return [
            {
                "document_name": doc.name,
                "chunk_text": chunk.text,
                "similarity_score": round(max(0.0, 1.0 - float(dist)), 4),
                "metadata": chunk.chunk_metadata,
            }
            for chunk, doc, dist in rows
        ]

    rows = db.execute(select(KnowledgeChunk, KnowledgeDocument).join(KnowledgeDocument)).all()
    scored = []
    for chunk, doc in rows:
        score = _cosine(query_vector, list(chunk.embedding))
        scored.append((score, chunk, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "document_name": doc.name,
            "chunk_text": chunk.text,
            "similarity_score": round(score, 4),
            "metadata": chunk.chunk_metadata,
        }
        for score, chunk, doc in scored[:top_k]
    ]
