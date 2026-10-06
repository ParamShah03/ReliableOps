from __future__ import annotations

import hashlib
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.entities import KnowledgeChunk, KnowledgeDocument
from app.rag.chunker import chunk_markdown
from app.rag.embeddings import get_embedding_client


def ingest_document(db: Session, name: str, content: str, metadata: dict | None = None) -> KnowledgeDocument:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.name == name))
    if existing and existing.content_hash == content_hash:
        return existing
    if existing:
        db.delete(existing)
        db.flush()

    document = KnowledgeDocument(name=name, content_hash=content_hash, source_metadata=metadata or {})
    db.add(document)
    db.flush()
    embedder = get_embedding_client()
    for index, text in enumerate(chunk_markdown(content)):
        db.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=index,
                text=text,
                embedding=embedder.embed(text),
                chunk_metadata={"document": name, "chunk_index": index, **(metadata or {})},
            )
        )
    db.commit()
    db.refresh(document)
    return document


def ingest_default_runbooks(db: Session) -> int:
    root = Path(__file__).resolve().parents[1] / "mock_data" / "runbooks"
    count = 0
    for path in sorted(root.glob("*.md")):
        ingest_document(db, path.name, path.read_text(encoding="utf-8"), {"source": "builtin_runbook"})
        count += 1
    return count
