from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.rag.retriever import search_runbook_chunks
from app.tools.base import BaseTool, ToolContext


class SearchRunbooksInput(BaseModel):
    query: str
    top_k: int = Field(default=4, ge=1, le=10)


class RunbookChunk(BaseModel):
    document_name: str
    chunk_text: str
    similarity_score: float
    metadata: dict


class SearchRunbooksOutput(BaseModel):
    results: list[RunbookChunk]


class SearchRunbooksTool(BaseTool[SearchRunbooksInput, SearchRunbooksOutput]):
    name = "search_runbooks"
    description = "Retrieve the most relevant operational runbook chunks using vector similarity."
    input_model = SearchRunbooksInput
    output_model = SearchRunbooksOutput

    def execute(self, db: Session, args: SearchRunbooksInput, context: ToolContext) -> SearchRunbooksOutput:
        results = [RunbookChunk.model_validate(x) for x in search_runbook_chunks(db, args.query, args.top_k)]
        return SearchRunbooksOutput(results=results)
