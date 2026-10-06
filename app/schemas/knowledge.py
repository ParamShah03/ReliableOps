from typing import Any
from pydantic import BaseModel, Field


class KnowledgeIngestRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeSearchResult(BaseModel):
    document_name: str
    chunk_text: str
    similarity_score: float
    metadata: dict[str, Any]
