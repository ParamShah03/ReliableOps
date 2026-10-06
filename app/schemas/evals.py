from pydantic import BaseModel


class EvalRunRequest(BaseModel):
    case_ids: list[str] | None = None
    agent_version: str = "v1"
