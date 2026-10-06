from datetime import datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tools.base import BaseTool, ToolContext
from app.tools.mock_loader import load_json


class SearchLogsInput(BaseModel):
    service: str
    query: str
    start_time: datetime
    end_time: datetime


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str


class SearchLogsOutput(BaseModel):
    service: str
    matches: list[LogEntry]
    count: int


class SearchLogsTool(BaseTool[SearchLogsInput, SearchLogsOutput]):
    name = "search_logs"
    description = "Search simulated service logs by service, text query, and time range."
    input_model = SearchLogsInput
    output_model = SearchLogsOutput

    def execute(self, db: Session, args: SearchLogsInput, context: ToolContext) -> SearchLogsOutput:
        entries = [LogEntry.model_validate(x) for x in load_json("logs/logs.json").get(args.service, [])]
        query = args.query.lower().strip()
        matches = [e for e in entries if args.start_time <= e.timestamp <= args.end_time and query in e.message.lower()]
        return SearchLogsOutput(service=args.service, matches=matches, count=len(matches))
