from app.rag.ingest import ingest_document
from app.rag.retriever import search_runbook_chunks


def test_rag_returns_relevant_document(db):
    ingest_document(
        db,
        "special_pool_test.md",
        "Database pool exhaustion causes timeout waiting for database connection when utilization reaches 100 percent.",
        {"test": True},
    )
    results = search_runbook_chunks(db, "database connection pool timeout", top_k=5)
    assert any(item["document_name"] == "special_pool_test.md" for item in results)
    assert all("similarity_score" in item for item in results)
