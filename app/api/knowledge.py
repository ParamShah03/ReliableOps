from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.rag.ingest import ingest_document
from app.rag.retriever import search_runbook_chunks
from app.schemas.knowledge import KnowledgeIngestRequest, KnowledgeSearchResult

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/ingest")
def ingest(payload: KnowledgeIngestRequest, db: Session = Depends(get_db)):
    document = ingest_document(db, payload.name, payload.content, payload.metadata)
    return {"id": document.id, "name": document.name, "content_hash": document.content_hash}


@router.get("/search", response_model=list[KnowledgeSearchResult])
def search(q: str = Query(min_length=2), top_k: int = Query(default=4, ge=1, le=10), db: Session = Depends(get_db)):
    return search_runbook_chunks(db, q, top_k)
